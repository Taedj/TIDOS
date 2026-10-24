"""Detect which tool and model a TIDOS session runs on, and what the project looks like.

Weak models often do not know their own model id, so TIDOS reads it from the tool's own files:
  Claude Code : model of the last assistant message in the newest transcript for this project
  OpenCode    : most recent model in ~/.local/state/opencode/model.json
An explicit --model always wins. Unknown models fall back to the "weak" tier (safe side).
"""
import fnmatch
import glob
import json
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REGISTRY = os.path.join(REPO_ROOT, "config", "models.json")
TIERS = ("frontier", "medium", "weak")


def tidos_home():
    return os.environ.get("TIDOS_HOME_DIR") or os.path.join(os.path.expanduser("~"), ".tidos")


# --- tool ---------------------------------------------------------------------
def detect_tool(explicit=None, env=None):
    env = os.environ if env is None else env
    if explicit and explicit != "auto":
        return explicit.lower()
    if env.get("CLAUDECODE") or env.get("CLAUDE_CODE_ENTRYPOINT"):
        return "claude-code"
    if env.get("OPENCODE") or env.get("OPENCODE_BIN_PATH") or env.get("OPENCODE_SERVER"):
        return "opencode"
    if env.get("GEMINI_CLI"):
        return "gemini-cli"
    return "unknown"


# --- model --------------------------------------------------------------------
def _claude_project_dir(project):
    encoded = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(project))
    return os.path.join(os.path.expanduser("~"), ".claude", "projects", encoded)


def _claude_model(project):
    files = glob.glob(os.path.join(_claude_project_dir(project), "*.jsonl"))
    if not files:
        return None
    newest = max(files, key=os.path.getmtime)
    model = None
    with open(newest, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"assistant"' not in line or '"model"' not in line:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            candidate = (entry.get("message") or {}).get("model")
            if entry.get("type") == "assistant" and candidate and not candidate.startswith("<"):
                model = candidate
    return model


def _opencode_model():
    path = os.path.join(os.path.expanduser("~"), ".local", "state", "opencode", "model.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            recent = json.load(f).get("recent") or []
    except (OSError, ValueError):
        return None
    if recent and recent[0].get("modelID"):
        first = recent[0]
        return "%s/%s" % (first.get("providerID", "?"), first["modelID"])
    return None


def detect_model(tool, explicit=None, project="."):
    """Return (model, source)."""
    if explicit and explicit.lower() not in ("auto", "unknown", ""):
        return explicit, "given"
    if tool == "claude-code":
        model = _claude_model(project)
        if model:
            return model, "claude transcript"
    if tool == "opencode":
        model = _opencode_model()
        if model:
            return model, "opencode state"
    return "unknown", "not detected"


# --- tier ---------------------------------------------------------------------
def _rules(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return [tuple(r) for r in json.load(f).get("rules", [])]
    except (OSError, ValueError):
        return []


def tier_for(model, registry=DEFAULT_REGISTRY):
    """Return (tier, matched pattern). User rules (~/.tidos/models.json) are checked first."""
    rules = _rules(os.path.join(tidos_home(), "models.json")) + _rules(registry)
    name = (model or "unknown").lower()
    for pattern, tier in rules:
        if tier in TIERS and fnmatch.fnmatch(name, pattern.lower()):
            return tier, pattern
    return "weak", "(default)"


# --- project ------------------------------------------------------------------
def project_facts(project):
    """Stack + how to check the work, detected from manifest files (no model involved)."""
    def has(*names):
        return any(os.path.exists(os.path.join(project, n)) for n in names)

    stack, checks, notes = [], [], []
    if has("pubspec.yaml"):
        stack.append("flutter/dart")
        checks += ["flutter analyze", "flutter test"]
    if has("package.json"):
        stack.append("node/javascript")
        try:
            with open(os.path.join(project, "package.json"), encoding="utf-8") as f:
                scripts = json.load(f).get("scripts", {})
            checks += ["npm run %s" % s for s in ("lint", "test", "build") if s in scripts]
        except (OSError, ValueError):
            pass
    if has("pyproject.toml", "requirements.txt", "setup.py", "pytest.ini") or glob.glob(os.path.join(project, "*.py")) \
            or glob.glob(os.path.join(project, "*", "__init__.py")):  # packages without a manifest
        stack.append("python")
        if has("tests", "pytest.ini") or glob.glob(os.path.join(project, "test_*.py")):
            checks.append("python -m pytest -q")
    if has("Cargo.toml"):
        stack.append("rust")
        checks.append("cargo test")
    if has("go.mod"):
        stack.append("go")
        checks.append("go test ./...")
    if glob.glob(os.path.join(project, "*.ps1")):
        stack.append("powershell")
    if has("firebase.json"):
        stack.append("firebase")
        notes.append("firebase.json present: never deploy without the user's explicit OK")
    if has(".git"):
        notes.append("git repository: check `git status` before and after changes")
    return {"name": os.path.basename(os.path.abspath(project)), "stack": stack or ["unknown"],
            "checks": checks, "notes": notes, "path": os.path.abspath(project)}
