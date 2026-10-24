"""TIDOS Privacy & Sanitization Firewall (v4.1).

Enforces the ZERO-LEAKAGE INVARIANT for community and upstream contributions.
Blocks secrets, credentials, local user paths, e-mail addresses and IPs from
leaving the user's machine.

Detection layers:
  1. gitleaks (if installed on PATH) — primary, maintained secret ruleset.
  2. Built-in regex rules (always on) — fallback and PII checks.

Stdlib only. Import-safe and usable as a CLI or verification module.

CLI:
  python sanitizer.py --check <file_or_dir> [--any-dir]
  python sanitizer.py --sanitize <file_or_dir>
Exit: 0 = clean / sanitized, 1 = violations or usage error
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Whitelist: ONLY these categories of files may ever be contributed upstream
ALLOWED_EXTENSIONS = {".md"}
ALLOWED_DIRECTORIES = {"personas", "evolution", "checklists", "docs", "skills", "playbooks"}

# Prohibited file names or patterns (instant reject)
PROHIBITED_FILES = {
    ".env", ".env.local", ".env.production", "secrets.json", "id_rsa", "id_ed25519",
    "credentials.json", "google-services.json", "GoogleService-Info.plist", "key.jks",
    "keystore", "token.txt", "token.json", "tidos.log", "gptid-relay.log",
    "tidos-session.json", "brain.db",
}

# Values that look like documentation placeholders, not real secrets
_PLACEHOLDER = re.compile(
    r"(?i)^(<.*>|\$\{?.*\}?|\{\{.*\}\}|x{4,}|\*{4,}|\.{3,}|your[_-].*|.*example.*|"
    r".*placeholder.*|.*redacted.*|changeme|null|none|true|false)$"
)

# High-confidence token formats (no context needed)
TOKEN_PATTERNS = [
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("github-fine-grained", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b")),
    ("gitlab-token", re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b")),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("openai-key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}")),
    ("stripe-key", re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")),
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("db-connection-string", re.compile(r"(?i)\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s:/@]+:[^\s@]+@\S+")),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{20,}=*")),
]

# key = value assignments; the value is checked against _looks_secret()
ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api[_-]?key|apikey|secret(?:[_-]?key)?|client[_-]?secret|password|passwd|pwd|"
    r"auth[_-]?token|access[_-]?token|refresh[_-]?token|id[_-]?token|cookie)\b"
    r"[\"']?\s*[:=]\s*[\"']?([^\s\"',;]+)"
)

# Backwards-compatible view used by older callers
SECRET_PATTERNS = [p for _, p in TOKEN_PATTERNS] + [ASSIGNMENT_PATTERN]

# PII / local machine fingerprints
# Windows user names may contain spaces ("Dr Jane Doe"): match up to the next separator
_WIN_USER_PATH = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+([^\\/\"'<>|*?\r\n]+)", re.IGNORECASE)
# /Users/ (macOS, Git Bash "/c/Users/Dr Jane Doe") may contain spaces; /home/ names cannot
_NIX_USER_PATH = re.compile(r"/(?:home/([^/\s\"'<>]+)|Users/([^/\"'<>|*?\r\n]+))")
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_IPV4 = re.compile(r"(?<![\w.])(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})(?![\w.])")

_SAFE_USERS = {"<user>", "user", "username", "public", "default", "you", "me", "shared"}
_SAFE_EMAIL_DOMAINS = ("example.com", "example.org", "anthropic.com", "users.noreply.github.com",
                       "noreply.github.com")


def _looks_secret(value):
    """Heuristic: is an assigned value a real credential rather than prose/placeholder?"""
    if len(value) < 8 or _PLACEHOLDER.match(value):
        return False
    if value.isalpha() and value.islower():  # plain words: "neverhardcode"
        return False
    classes = sum([any(c.islower() for c in value), any(c.isupper() for c in value),
                   any(c.isdigit() for c in value), any(not c.isalnum() for c in value)])
    return classes >= 2


def _is_reportable_ip(groups):
    octets = [int(g) for g in groups]
    if any(o > 255 for o in octets):
        return False
    if octets[0] in (0, 127) or octets == [255, 255, 255, 255]:
        return False
    # documentation ranges (RFC 5737) are safe in examples
    if octets[:3] in ([192, 0, 2], [198, 51, 100], [203, 0, 113]):
        return False
    return True


def find_secrets(text):
    """Return [(rule, sample)] for every secret found in text."""
    hits = []
    for rule, pat in TOKEN_PATTERNS:
        for m in pat.finditer(text):
            hits.append((rule, m.group(0)[:40]))
    for m in ASSIGNMENT_PATTERN.finditer(text):
        if _looks_secret(m.group(2)):
            hits.append(("assigned-" + m.group(1).lower(), m.group(0)[:40]))
    return hits


def _path_user(m):
    return next(g for g in m.groups() if g is not None)


def _local_user_names():
    """This machine's own user name(s) in every spelling tools use (spaces, dashes, 8.3 short name)."""
    names = {os.path.basename(os.path.expanduser("~")), os.environ.get("USERNAME", ""), os.environ.get("USER", "")}
    if os.name == "nt":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            if ctypes.windll.kernel32.GetShortPathNameW(os.path.expanduser("~"), buf, 260):
                names.add(os.path.basename(buf.value))  # e.g. DRTIDJ~1
        except (AttributeError, OSError):
            pass
    variants = set()
    for name in names:
        if len(name) < 3 or name.lower() in _SAFE_USERS:
            continue
        for sep in (" ", "-", "_", ""):
            variants.add(re.sub(r"[\s~]+", sep, name))
        # Claude Code encodes "C:\Users\Dr Jane" as "C--Users-Dr-Jane": every non-alnum -> "-"
        variants.add(re.sub(r"[^A-Za-z0-9]", "-", name))
    variants = sorted((v for v in variants if len(v) >= 3), key=len, reverse=True)
    if not variants:
        return None
    return re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])" % "|".join(map(re.escape, variants)), re.IGNORECASE)


_LOCAL_USER = _local_user_names()


def find_pii(text):
    """Return [(kind, sample)] for local paths, user names, e-mails and IPs found in text."""
    hits = []
    for pat in (_WIN_USER_PATH, _NIX_USER_PATH):
        for m in pat.finditer(text):
            if _path_user(m).lower() not in _SAFE_USERS:
                hits.append(("user-path", m.group(0)[:60]))
    if _LOCAL_USER:
        for m in _LOCAL_USER.finditer(text):
            hits.append(("local-user-name", m.group(0)))
    for m in _EMAIL.finditer(text):
        if not m.group(0).lower().endswith(_SAFE_EMAIL_DOMAINS):
            hits.append(("email", m.group(0)))
    for m in _IPV4.finditer(text):
        if _is_reportable_ip(m.groups()):
            hits.append(("ip-address", m.group(0)))
    return hits


def sanitize_text(text):
    """Redact secrets and local filesystem/PII fingerprints from text."""
    out = text
    for _, pat in TOKEN_PATTERNS:
        out = pat.sub("[REDACTED_SECRET]", out)
    out = ASSIGNMENT_PATTERN.sub(
        lambda m: m.group(0).replace(m.group(2), "[REDACTED_SECRET]") if _looks_secret(m.group(2)) else m.group(0),
        out,
    )
    out = _WIN_USER_PATH.sub(
        lambda m: m.group(0) if _path_user(m).lower() in _SAFE_USERS else m.group(0)[:2] + "\\Users\\<USER>", out)
    out = _NIX_USER_PATH.sub(
        lambda m: m.group(0) if _path_user(m).lower() in _SAFE_USERS
        else m.group(0)[: m.group(0).index("/", 1)] + "/<USER>", out)
    if _LOCAL_USER:
        out = _LOCAL_USER.sub("<USER>", out)
    out = _EMAIL.sub(lambda m: m.group(0) if m.group(0).lower().endswith(_SAFE_EMAIL_DOMAINS) else "<EMAIL_REDACTED>", out)
    out = _IPV4.sub(lambda m: "<IP_REDACTED>" if _is_reportable_ip(m.groups()) else m.group(0), out)
    return out


def _top_level_dir(filepath, root=REPO_ROOT):
    rel = os.path.relpath(os.path.abspath(filepath), root)
    if rel.startswith(".."):
        return None
    return rel.replace("\\", "/").split("/", 1)[0]


def audit_file(filepath, enforce_dirs=False, root=REPO_ROOT):
    """Audit a single file for zero-leakage compliance.

    Returns (ok, list_of_violations).
    """
    violations = []
    basename = os.path.basename(filepath)
    _, ext = os.path.splitext(filepath)

    if basename in PROHIBITED_FILES or basename.startswith(".env"):
        violations.append("Prohibited sensitive file name: %s" % basename)

    if ext.lower() not in ALLOWED_EXTENSIONS:
        violations.append("File extension '%s' is not in upstream contribution whitelist (.md only)" % ext)

    if enforce_dirs:
        top = _top_level_dir(filepath, root)
        if top not in ALLOWED_DIRECTORIES:
            violations.append("Directory '%s' is not in contribution whitelist %s"
                              % (top or "<outside repository>", sorted(ALLOWED_DIRECTORIES)))

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except OSError as e:
        return False, ["Unable to read file %s: %s" % (filepath, e)]

    for rule, sample in find_secrets(content):
        violations.append("Secret detected [%s] in %s (e.g. '%s')" % (rule, basename, sample))
    for kind, sample in find_pii(content):
        violations.append("PII detected [%s] in %s (e.g. '%s')" % (kind, basename, sample))

    return (len(violations) == 0, violations)


def gitleaks_scan(paths):
    """Run gitleaks over paths if installed. Returns {file: [violations]} or None if unavailable."""
    exe = shutil.which("gitleaks")
    if not exe:
        return None
    report = {}
    for path in paths:
        fd, out = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            for args in (["dir", path], ["detect", "--no-git", "--source", path]):
                proc = subprocess.run([exe, *args, "--no-banner", "--report-format", "json",
                                       "--report-path", out, "--exit-code", "0"],
                                      capture_output=True, text=True)
                if proc.returncode == 0:
                    break
            else:
                return None
            with open(out, "r", encoding="utf-8") as f:
                findings = json.load(f) or []
            for item in findings:
                fp = item.get("File", path)
                report.setdefault(fp, []).append("gitleaks [%s] line %s" % (item.get("RuleID"), item.get("StartLine")))
        except (OSError, ValueError):
            return None
        finally:
            os.remove(out)
    return report


def audit_bundle(file_list, enforce_dirs=False, use_gitleaks=True, root=REPO_ROOT):
    """Audit an entire collection of candidate files before upstream contribution.

    Returns (ok, dict_of_file_violations).
    """
    report = {}
    for fp in file_list:
        ok, viols = audit_file(fp, enforce_dirs=enforce_dirs, root=root)
        if not ok:
            report[fp] = viols
    if use_gitleaks:
        for fp, viols in (gitleaks_scan(file_list) or {}).items():
            report.setdefault(fp, []).extend(viols)
    return (len(report) == 0, report)


def _collect(target):
    if os.path.isfile(target):
        return [target]
    files = []
    for root, _, names in os.walk(target):
        files.extend(os.path.join(root, n) for n in names)
    return files


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    any_dir = "--any-dir" in argv
    argv = [a for a in argv if a != "--any-dir"]
    if not argv:
        print("Usage: python sanitizer.py [--check|--sanitize] <file_or_directory> [--any-dir]")
        return 1

    mode = "--check"
    if argv[0] in ("--check", "--sanitize"):
        mode = argv.pop(0)
    target = argv[0] if argv else "."

    if not os.path.exists(target):
        print("Target path does not exist: %s" % target)
        return 1

    files_to_check = _collect(target)

    if mode == "--check":
        ok, report = audit_bundle(files_to_check, enforce_dirs=not any_dir)
        if shutil.which("gitleaks") is None:
            print("[INFO] gitleaks not installed - using built-in rules only.")
        if ok:
            print("[PASS] Privacy Firewall Audit: Clean! Zero secrets, PII or prohibited files found.")
            return 0
        print("[FAIL] Privacy Firewall Audit FAILED! Violations detected:")
        for fp, viols in report.items():
            print("  File: %s" % fp)
            for v in viols:
                print("    - %s" % v)
        return 1

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
        except (OSError, UnicodeDecodeError) as e:
            print("Error processing %s: %s" % (fp, e))
    print("Sanitization complete. %d files modified." % modified)
    return 0


if __name__ == "__main__":
    sys.exit(main())
