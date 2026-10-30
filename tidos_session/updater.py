"""Safe self-update: a new TIDOS release is tested in a separate copy before TIDOS switches to it.

  check     fetch; the newest release tag vX.Y.Z vs the version you run; patch / minor / major
  stage     check the release out in a git WORKTREE (~/.tidos/staging/<tag>) and run the daily-quest gates there
            with a throwaway TIDOS home: tests, spec validator, plugin sync, dungeon validation.
            Your checkout and your brain are not touched.
  apply     only a release whose staging passed. A PATCH release applies by itself (switch auto_update on);
            a minor or major release waits for you. Same guards as scripts/update.ps1: a genuine TIDOS checkout,
            the canonical origin, no edited system files, no local commits missing from the release. The switch is
            a plain `git checkout` (never --force, never clean): git itself refuses to overwrite local work.
  rollback  back to the exact version you ran before the last apply (also: Undo in the action journal)
State (private): ~/.tidos/update.json {target, bump, staged: {ok, gates, log, at}, previous, current, applied_at}.

  python -I tidos_session/__main__.py update [--auto | --stage | --apply | --rollback]   (no option: status)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from .detect import REPO_ROOT, tidos_home

CANONICAL = "https://github.com/Taedj/TIDOS.git"
MARKERS = ("TIDSTART.md", "core/kernel.md", "config/framework.md")
USER_DIRS = ("memory/", "evolution/")
GATES = [("tests", ["-m", "pytest", "-q", "-p", "no:cacheprovider", "tests", "browser_relay/tests"]),
         ("specs", ["scripts/validate_specs.py"]),
         ("plugin sync", ["scripts/build_plugin.py", "--check"]),
         ("dungeons valid", ["-I", "tidos_evals/__main__.py", "validate"])]
GATE_TIMEOUT = 1800


class Refused(Exception):
    pass


def _git(repo, *args, check=False):
    r = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check and r.returncode != 0:
        raise Refused("git %s failed: %s" % (" ".join(args[:2]), (r.stderr or r.stdout).strip()[:300]))
    return r


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def version(tag):
    m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag or "")
    return tuple(int(x) for x in m.groups()) if m else None


def bump(current, target):
    a, b = version(current), version(target)
    if not a or not b or b <= a:
        return None
    return "major" if b[0] > a[0] else "minor" if b[1] > a[1] else "patch"


def _state_path():
    return os.path.join(tidos_home(), "update.json")


def status():
    try:
        with open(_state_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(**fields):
    data = dict(status(), **fields)
    os.makedirs(tidos_home(), exist_ok=True)
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    return data


def _canonical():
    return os.environ.get("TIDOS_UPDATE_TEST_URL") or CANONICAL  # test harness only


def _norm(url):
    return re.sub(r"\.git$", "", (url or "").strip().rstrip("/")).lower().replace("\\", "/")


def _guard_checkout(repo):
    if not all(os.path.exists(os.path.join(repo, m)) for m in MARKERS):
        raise Refused("%s is not a TIDOS checkout" % repo)
    if _git(repo, "rev-parse", "--show-prefix").stdout.strip():
        raise Refused("%s is not the top of its git repository" % repo)
    origin = _git(repo, "remote", "get-url", "origin").stdout.strip()
    if _norm(origin) != _norm(_canonical()):
        raise Refused("origin is %r, not the TIDOS repository: update a fork with git yourself" % origin)


def _guard_clean(repo):
    dirty = [l for l in _git(repo, "status", "--porcelain", "--untracked-files=no").stdout.splitlines()
             if l.strip() and not l[3:].strip('"').startswith(USER_DIRS)]
    if dirty:
        raise Refused("TIDOS system files are edited (%s): commit or stash them first" % ", ".join(l[3:] for l in dirty[:3]))


# --- check / stage ----------------------------------------------------------------------------------------
def check(repo=REPO_ROOT, fetch=True):
    """{current, target, bump} after a fetch; target None when up to date. Never changes the checkout."""
    _guard_checkout(repo)
    if fetch and _git(repo, "fetch", "origin", "--tags", "--prune", "--force").returncode != 0:
        raise Refused("GitHub unreachable: staying on the version you run")
    current = _git(repo, "describe", "--tags", "--abbrev=0", "--match", "v*", "HEAD").stdout.strip() or None
    tags = [t for t in _git(repo, "tag", "-l", "v*").stdout.split() if version(t)]
    target = max(tags, key=lambda t: version(t) or (0, 0, 0), default=None)
    kind = bump(current, target) if current else ("major" if target else None)
    return {"current": current, "target": target if kind else None, "bump": kind}


def stage(info, repo=REPO_ROOT, gates=None):
    """Run the gates on the target release in a separate worktree. Returns the staged record (also saved)."""
    target = info["target"]
    root = os.path.join(tidos_home(), "staging")
    work, log = os.path.join(root, target), os.path.join(root, target + ".log")
    os.makedirs(root, exist_ok=True)
    if os.path.exists(work):
        _git(repo, "worktree", "remove", "--force", work)
        shutil.rmtree(work, ignore_errors=True)
    _git(repo, "worktree", "prune")
    _git(repo, "worktree", "add", "--detach", work, target, check=True)
    results = []
    home = tempfile.mkdtemp(prefix="tidos-stage-home-")
    env = dict(os.environ, TIDOS_HOME_DIR=home, TIDOS_CONTROL_FILE=os.path.join(home, "control.json"),
               PYTHONIOENCODING="utf-8")
    env.pop("TIDOS_E2E", None)  # browser tests need a display: they run in your own daily quest
    try:
        with open(log, "w", encoding="utf-8") as out:
            for name, args in (gates or GATES):
                out.write("$ python %s\n" % " ".join(args))
                out.flush()
                try:
                    code = subprocess.run([sys.executable] + args, cwd=work, env=env, stdout=out,
                                          stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                          timeout=GATE_TIMEOUT).returncode
                except subprocess.TimeoutExpired:
                    code = -1
                results.append({"gate": name, "ok": code == 0, "exit": code})
                out.write("\n[%s] exit %d\n\n" % (name, code))
                if code != 0:
                    break
    finally:
        _git(repo, "worktree", "remove", "--force", work)
        shutil.rmtree(home, ignore_errors=True)
    staged = {"ok": bool(results) and all(r["ok"] for r in results), "gates": results, "log": log, "at": _now()}
    _save(target=target, bump=info["bump"], current_tag=info["current"], staged=staged)
    return staged


# --- apply / rollback -------------------------------------------------------------------------------------
def _switch(repo, rev):
    previous = _git(repo, "rev-parse", "HEAD", check=True).stdout.strip()
    _git(repo, "checkout", "--detach", rev, check=True)  # no --force: git refuses to overwrite local changes
    return previous, _git(repo, "rev-parse", "HEAD", check=True).stdout.strip()


def apply(repo=REPO_ROOT):
    """Switch to the staged release. Refused unless staging passed for that exact target."""
    s = status()
    target, staged = s.get("target"), s.get("staged") or {}
    if not target or not staged.get("ok"):
        raise Refused("no release passed staging yet: run the update check first")
    _guard_checkout(repo)
    _guard_clean(repo)
    ahead = _git(repo, "rev-list", "--count", "%s..HEAD" % target).stdout.strip()
    if ahead and int(ahead) > 0:
        raise Refused("%s local commit(s) are not in %s: push or merge them first" % (ahead, target))
    previous, current = _switch(repo, target)
    _save(previous=previous, current=current, applied=target, applied_at=_now(), target=None, staged=None)
    return {"from": previous[:12], "to": target}


def rollback(repo=REPO_ROOT):
    """Back to the version you ran before the last apply."""
    s = status()
    if not s.get("previous"):
        raise Refused("nothing to roll back: no update was applied by TIDOS")
    _guard_checkout(repo)
    _guard_clean(repo)
    _, current = _switch(repo, s["previous"])
    _save(previous=None, current=current, rolled_back_from=s.get("applied"), rolled_back_at=_now())
    return {"to": current[:12], "from": s.get("applied")}


def auto(repo=REPO_ROOT, gates=None, apply_patch=None):
    """The autopilot job: check, stage, and apply a PATCH release that passed (switch auto_update on).
    Returns lines describing what happened."""
    if apply_patch is None:
        from tidos_brain import control
        apply_patch = control.is_on("auto_update")
    info = check(repo)
    if not info["target"]:
        _save(target=None, staged=None, checked_at=_now())
        return ["TIDOS is up to date (%s)." % (info["current"] or "no release tag")]
    lines = ["%s release available: %s -> %s" % (info["bump"], info["current"], info["target"])]
    s = status()
    staged = s.get("staged") if s.get("target") == info["target"] else None
    if not staged:
        staged = stage(info, repo, gates)
    lines.append("staging: %s (%s)" % ("PASSED" if staged["ok"] else "FAILED",
                                       ", ".join("%s %s" % (g["gate"], "ok" if g["ok"] else "exit %d" % g["exit"])
                                                 for g in staged["gates"])))
    if not staged["ok"]:
        return lines + ["not applied: the release failed its checks here (log: %s)" % staged["log"]]
    if info["bump"] != "patch":
        return lines + ["waiting for you: a %s release is applied only when you approve it" % info["bump"]]
    if not apply_patch:
        return lines + ["waiting for you: the auto_update switch is off"]
    try:
        done = apply(repo)
    except Refused as e:
        return lines + ["not applied: %s" % e]
    return lines + ["applied: %s -> %s (undo: rollback)" % (done["from"], done["to"])]
