"""Tool Scout recipes: set a tool up in ONE project, end to end, and undo it.

  detect     the tool fits the project (stack, files) and the project actually lacks this setup
  install    only if missing, only an APPROVED catalog tool (scout.install: pinned version, tool_install switch)
  configure  write the recipe's files; an existing file is never overwritten, a hook you wrote is never touched
  verify     run the tool in the project; it must start and answer with an expected exit code
  rollback   verify failed: every file written in this run is removed again
Undo later (unconfigure): a file is removed only if it is still exactly what TIDOS wrote; a hook block is cut out.
State (private): ~/.tidos/recipes.json {"<project>|<tool>": {tool, project, files: [{path, kind, sha256}], at}}.
Runs from the autopilot are governed by graduated trust (kind configure_tool, starts at 'propose').
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from tidos_session import detect

from . import scout

HOOK_HEAD = "#!/bin/sh\n# TIDOS-managed pre-commit hook: each block below was added by a Tool Scout recipe.\n"
VERIFY_TIMEOUT = 300


def _has(project, *names):
    return any(os.path.exists(os.path.join(project, n)) for n in names)


def _section(project, filename, marker):
    try:
        with open(os.path.join(project, filename), "r", encoding="utf-8") as f:
            return marker in f.read()
    except OSError:
        return False


def _ruff_needed(p):
    if _has(p, "ruff.toml", ".ruff.toml") or _section(p, "pyproject.toml", "[tool.ruff"):
        return "the project already configures ruff"
    return None


def _pytest_needed(p):
    if not os.path.isdir(os.path.join(p, "tests")):
        return "no tests/ folder"
    if _has(p, "pytest.ini") or _section(p, "pyproject.toml", "[tool.pytest") or _section(p, "setup.cfg", "[tool:pytest]") \
            or _section(p, "tox.ini", "[pytest]"):
        return "the project already configures pytest"
    return None


def _gitleaks_needed(p):
    if not os.path.isdir(os.path.join(p, ".git")):
        return "not a git repository"
    hook = os.path.join(p, ".git", "hooks", "pre-commit")
    if os.path.exists(hook) and HOOK_HEAD not in _read(hook):
        return "the project has its own pre-commit hook: add `gitleaks git --pre-commit --staged` to it yourself"
    if "# TIDOS:BEGIN gitleaks" in _read(hook):
        return "already set up"
    return None


RECIPES = {
    "gitleaks": {
        "what": "pre-commit hook: a commit that contains a secret is blocked",
        "missing": _gitleaks_needed,
        "files": [{"path": ".git/hooks/pre-commit", "kind": "hook",
                   "text": "gitleaks git --pre-commit --staged --no-banner --redact || exit 1"}],
        "verify": (["gitleaks", "git", "--pre-commit", "--staged", "--no-banner", "--redact"], (0,)),
    },
    "ruff": {
        "what": "ruff.toml with ruff's recommended rules, so every model and person lints the same way",
        "missing": _ruff_needed,
        "files": [{"path": "ruff.toml", "kind": "file", "text":
                   "# Added by TIDOS (Tool Scout recipe): ruff's recommended rules. Edit freely.\n"
                   "extend-exclude = [\"build\", \"dist\", \".venv\", \"node_modules\"]\n\n"
                   "[lint]\nselect = [\"E4\", \"E7\", \"E9\", \"F\"]\n"}],
        "verify": (["ruff", "check", "--quiet", "."], (0, 1)),  # 1 = it ran and found issues: set up correctly
    },
    "pytest": {
        "what": "pytest.ini pointing at tests/, so `pytest` finds the tests from anywhere in the project",
        "missing": _pytest_needed,
        "files": [{"path": "pytest.ini", "kind": "file",
                   "text": "# Added by TIDOS (Tool Scout recipe). Edit freely.\n[pytest]\ntestpaths = tests\n"}],
        "verify": (["python", "-m", "pytest", "--collect-only", "-q"], (0, 5)),  # 5 = no tests collected yet
    },
}


# --- state ------------------------------------------------------------------------------------------------
def _state_path():
    return os.path.join(detect.tidos_home(), "recipes.json")


def _load():
    try:
        with open(_state_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data):
    os.makedirs(detect.tidos_home(), exist_ok=True)
    tmp = _state_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, _state_path())


def _key(project, tool):
    return "%s|%s" % (os.path.normcase(os.path.abspath(project)), tool)


def configured(project=None):
    """[{tool, project, files, at}] set up by TIDOS (one project, or all)."""
    items = list(_load().values())
    if project:
        items = [i for i in items if _key(i["project"], "") == _key(project, "")]
    return items


# --- files ------------------------------------------------------------------------------------------------
def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _block(name, text):
    return "# TIDOS:BEGIN %s\n%s\n# TIDOS:END %s\n" % (name, text, name)


def _write(project, name, spec):
    """Write one recipe file. Returns its record, or raises ValueError when it must not be written."""
    path = os.path.join(project, spec["path"])
    if spec["kind"] == "file":
        if os.path.exists(path):
            raise ValueError("%s exists: left alone" % spec["path"])
        os.makedirs(os.path.dirname(path) or project, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(spec["text"])
        return {"path": spec["path"], "kind": "file", "sha256": _sha(path)}
    text = _read(path)
    if text and HOOK_HEAD not in text:
        raise ValueError("%s is your own hook: left alone" % spec["path"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write((text or HOOK_HEAD) + _block(name, spec["text"]))
    os.chmod(path, 0o755)
    return {"path": spec["path"], "kind": "hook", "block": name}


def _remove(project, rec):
    """Remove one file TIDOS wrote. Returns a status line; never removes a file you changed."""
    path = os.path.join(project, rec["path"])
    if not os.path.exists(path):
        return "%s: already gone" % rec["path"]
    if rec["kind"] == "file":
        if _sha(path) != rec["sha256"]:
            return "%s: changed since, left alone" % rec["path"]
        os.remove(path)
        return "%s: removed" % rec["path"]
    text = _read(path)
    begin, end = "# TIDOS:BEGIN %s\n" % rec["block"], "# TIDOS:END %s\n" % rec["block"]
    if begin in text and end in text:
        text = text[:text.index(begin)] + text[text.index(end) + len(end):]
    if text.strip() == HOOK_HEAD.strip():
        os.remove(path)
        return "%s: removed" % rec["path"]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return "%s: TIDOS block removed" % rec["path"]


def _verify(project, argv, ok, runner):
    exe = shutil.which(argv[0]) or (sys.executable if argv[0] == "python" else None)
    if not exe:
        return False, "%s not found" % argv[0]
    try:
        r = runner([exe] + argv[1:], cwd=project, capture_output=True, text=True, timeout=VERIFY_TIMEOUT,
                   stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-1:] or [""]
    return r.returncode in ok, "exit %d %s" % (r.returncode, tail[0][:200])


# --- the recipe -------------------------------------------------------------------------------------------
def plan(name, project):
    """What the recipe would do here, without doing it: {tool, what, applies, reason, files, verify}."""
    recipe = RECIPES.get(name)
    tool = next((t for t in scout.catalog() if t["name"] == name), None)
    if not recipe or not tool:
        raise ValueError("no recipe for %r" % name)
    if not os.path.isdir(project):
        raise ValueError("project does not exist: %s" % project)
    reason = None
    if not scout.applies(tool, detect.project_facts(project), project):
        reason = "%s does not fit this project's stack" % name
    reason = reason or recipe["missing"](project)
    return {"tool": name, "what": recipe["what"], "applies": reason is None, "reason": reason,
            "installed": scout.installed(tool, project, _mcp=set()),
            "files": [f["path"] for f in recipe["files"]], "verify": " ".join(recipe["verify"][0])}


def apply(name, project, runner=subprocess.run, install=None):
    """Run the recipe. Returns {ok, steps: [[step, status, detail]]}; on a failed verify every file is rolled back."""
    p = plan(name, project)
    steps = [["detect", "ok" if p["applies"] else "stop", p["reason"] or p["what"]]]
    if not p["applies"]:
        return {"ok": False, "steps": steps}
    if not p["installed"]:
        try:
            result = (install or scout.install)(name)
        except scout.InstallRefused as e:
            steps.append(["install", "stop", str(e)])
            return {"ok": False, "steps": steps}
        steps.append(["install", "ok" if result.get("ok") else "stop", result.get("detail", "")])
        if not result.get("ok"):
            return {"ok": False, "steps": steps}
    written = []
    for spec in RECIPES[name]["files"]:
        try:
            written.append(_write(project, name, spec))
            steps.append(["configure", "ok", spec["path"]])
        except (ValueError, OSError) as e:
            steps.append(["configure", "stop", str(e)])
            for rec in written:
                _remove(project, rec)
            return {"ok": False, "steps": steps}
    ok, detail = _verify(project, *RECIPES[name]["verify"], runner=runner)
    steps.append(["verify", "ok" if ok else "failed", detail])
    if not ok:
        steps.append(["rollback", "ok", "; ".join(_remove(project, rec) for rec in written)])
        scout._log("recipe %s in %s: verify failed, rolled back" % (name, project))
        return {"ok": False, "steps": steps}
    data = _load()
    data[_key(project, name)] = {"tool": name, "project": os.path.abspath(project), "files": written,
                                 "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _save(data)
    scout._log("recipe %s in %s: set up (%s)" % (name, project, ", ".join(r["path"] for r in written)))
    return {"ok": True, "steps": steps}


def unconfigure(name, project):
    """Undo apply(): remove what TIDOS wrote (files you changed are kept). Returns the status lines."""
    data = _load()
    rec = data.pop(_key(project, name), None)
    if rec is None:
        raise ValueError("%s was not set up by TIDOS in %s" % (name, project))
    lines = [_remove(rec["project"], f) for f in rec["files"]]
    _save(data)
    scout._log("recipe %s in %s: undone (%s)" % (name, project, "; ".join(lines)))
    return lines
