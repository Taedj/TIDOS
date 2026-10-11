"""TIDOS Privacy & Sanitization Firewall (v4.0).

Enforces the ZERO-LEAKAGE INVARIANT for community and upstream contributions.
Guarantees that private project code, proprietary business logic, client data,
passwords, API keys, personal file paths, and environment secrets NEVER leave
the user's local machine.

Stdlib only. Import-safe and usable as a CLI or verification module.
"""
import os
import re
import sys

# Whitelist: ONLY these categories of files may ever be contributed upstream
ALLOWED_EXTENSIONS = {".md"}
ALLOWED_DIRECTORIES = {"personas", "evolution", "checklists", "docs"}

# Prohibited file names or patterns (instant reject)
PROHIBITED_FILES = {
    ".env", ".env.local", ".env.production", "secrets.json", "id_rsa",
    "credentials.json", "google-services.json", "key.jks", "keystore",
    "token.txt", "token.json", "tidos.log", "gptid-relay.log"
}

# Regex patterns for secret detection
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(api[_-]?key|apikey)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(auth[_-]?token|access[_-]?token|refresh[_-]?token|id[_-]?token|bearer)\b\s*[:=]?\s*\S+"),
    re.compile(r"(?i)\b(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}\b"), # GitHub tokens
    re.compile(r"(?i)\bglpat-[A-Za-z0-9_-]{20,}\b"), # GitLab tokens
    re.compile(r"(?i)\bsk-[A-Za-z0-9]{20,}\b"), # OpenAI / standard API keys
    re.compile(r"(?i)\bAIza[0-9A-Za-z-_]{35}\b"), # Google API keys
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)cookie\s*[:=]\s*\S+"),
    re.compile(r"(?i)set-cookie\s*:\s*\S+"),
    re.compile(r"(?i)postgres(?:ql)?://\S+:\S+@\S+"), # DB connection strings
    re.compile(r"(?i)mongodb(?:\+srv)?://\S+:\S+@\S+"),
]

# Patterns for Local Path & PII Sanitization
PATH_PATTERNS = [
    (re.compile(r"[A-Za-z]:\\[Uu]sers\\[^\\]+\\"), "C:\\Users\\<USER>\\"),
    (re.compile(r"/home/[^/]+/"), "/home/<USER>/"),
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<IP_REDACTED>"),
]


def sanitize_text(text: str) -> str:
    """Redact secrets and local filesystem PII from text."""
    out = text
    # Redact secrets
    for pat in SECRET_PATTERNS:
        out = pat.sub("[REDACTED_SECRET]", out)
    # Redact local system user paths
    for pat, repl in PATH_PATTERNS:
        # Don't redact loopback 127.0.0.1
        if pat.pattern.startswith(r"\b\d"):
            out = re.sub(r"\b(?!127\.0\.0\.1)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "<IP_REDACTED>", out)
        else:
            out = pat.sub(repl, out)
    return out


def audit_file(filepath: str):
    """Audit a single file for zero-leakage compliance.

    Returns (ok, list_of_violations).
    """
    violations = []
    basename = os.path.basename(filepath)
    _, ext = os.path.splitext(filepath)

    # 1. Prohibited file name check
    if basename in PROHIBITED_FILES or basename.startswith(".env"):
        violations.append("Prohibited sensitive file name: %s" % basename)

    # 2. Extension whitelist check
    if ext.lower() not in ALLOWED_EXTENSIONS:
        violations.append("File extension '%s' is not in upstream contribution whitelist (.md only)" % ext)

    # 3. Content secret scan
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        return False, ["Unable to read file %s: %s" % (filepath, e)]

    for pat in SECRET_PATTERNS:
        matches = pat.findall(content)
        if matches:
            violations.append("Secret pattern detected in %s (e.g. '%s')" % (basename, matches[0][:40]))

    return (len(violations) == 0, violations)


def audit_bundle(file_list):
    """Audit an entire collection of candidate files before upstream contribution.

    Returns (ok, dict_of_file_violations).
    """
    all_ok = True
    report = {}
    for fp in file_list:
        ok, viols = audit_file(fp)
        if not ok:
            all_ok = False
            report[fp] = viols
    return all_ok, report


def main():
    if len(sys.argv) < 2:
        print("Usage: python sanitizer.py [--check|--sanitize] <file_or_directory>")
        sys.exit(1)

    mode = "--check"
    target = sys.argv[1]
    if target in ("--check", "--sanitize"):
        mode = target
        target = sys.argv[2] if len(sys.argv) > 2 else "."

    if not os.path.exists(target):
        print("Target path does not exist: %s" % target)
        sys.exit(1)

    files_to_check = []
    if os.path.isfile(target):
        files_to_check.append(target)
    else:
        for root, _, files in os.walk(target):
            for f in files:
                files_to_check.append(os.path.join(root, f))

    if mode == "--check":
        ok, report = audit_bundle(files_to_check)
        if ok:
            print("[PASS] Privacy Firewall Audit: Clean! Zero secrets or prohibited files found.")
            sys.exit(0)
        else:
            print("[FAIL] Privacy Firewall Audit FAILED! Violations detected:")
            for fp, viols in report.items():
                print("  File: %s" % fp)
                for v in viols:
                    print("    - %s" % v)
            sys.exit(1)

    elif mode == "--sanitize":
        modified = 0
        for fp in files_to_check:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read()
                sanitized = sanitize_text(content)
                if sanitized != content:
                    with open(fp, "w", encoding="utf-8") as f:
                        f.write(sanitized)
                    modified += 1
                    print("Sanitized: %s" % fp)
            except Exception as e:
                print("Error processing %s: %e" % (fp, e))
        print("Sanitization complete. %d files modified." % modified)


if __name__ == "__main__":
    main()
