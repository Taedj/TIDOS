"""Community learning: with the user's "Agree", TIDOS shares ANONYMOUS lessons so it improves for everyone.

Consent: asked once at the first START TIDOS ("Agree" / "Not agree"); "Not agree" never blocks anything, TIDOS
keeps working and learns only on this computer. Change it any time:
  python -I tidos_session/__main__.py consent agree | decline      (or the Security tab)

The learning pack is WHITELIST-ONLY. Every field is a known category, a count, a model id or a check command
reduced to "tool subcommand" - anything else is dropped before it is built:
  work         per task type x stack: tasks, successes, verified, right-first-time, corrected
  checks       which checks confirm work per stack ("flutter test", "python -m pytest"), runs and passes
  guide        does GUIDE help weak models: guided vs unguided pass rates per model
  dungeons     pass rates per agent and mode
  tools        Tool Scout catalog tools used as checks, runs and passes
  army         built-in and TIDOS subagents (never your own specialists): missions, success
Never: prompts, code, answers, file names or paths, project names, your rules, e-mail, IP.
  python -I tidos_learn/__main__.py share --show      prints exactly what would be sent
Upload: once a day after START TIDOS, to contributions/<your uid>/packs/<date> in the TIDOS Firebase project
(Firestore rules: you can only write your own packs; only the TIDOS developer can read them all).
"""
import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from tidos_brain import control
from tidos_session.detect import REPO_ROOT, tidos_home

from . import classify, distill

SCHEMA = "tidos-pack/1"
EVERY = timedelta(hours=20)
_CHECK = re.compile(r"^[a-z0-9][a-z0-9 ._:/-]{1,60}$")
_MODEL = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/\-]{1,80}$")
TYPES = {name for name, _ in classify.TYPE_RULES} | {"question", "feature"}
STACKS = set(classify.EXT_STACKS.values()) | {v for _, v in classify.CMD_STACKS}


def consent():
    return control.text("share_learning")


def set_consent(answer):
    control.set_text("share_learning", {"agree": "agree", "decline": "decline"}[answer])
    return consent()


def _version():
    try:
        with open(os.path.join(REPO_ROOT, "VERSION.md"), "r", encoding="utf-8") as f:
            m = re.search(r"\*\*Current Version\*\*:\s*(\S+)", f.read())
        return m.group(1) if m else "unknown"
    except OSError:
        return "unknown"


def _model(m):
    return m if m and _MODEL.match(m) and "\\" not in m and ":/" not in m and not m.startswith("/") else None


def build(conn):
    """The anonymous learning pack (dict). Only whitelisted categories, counts and ids."""
    from tidos_dashboard import accounts
    work = defaultdict(lambda: {"tasks": 0, "success": 0, "verified": 0, "first_try": 0, "corrected": 0})
    checks = defaultdict(lambda: {"runs": 0, "passed": 0})
    for t in distill.load_tasks(conn):
        ttype = t["type"] if t["type"] in TYPES else "other"
        for stack in [s for s in t["stacks"] if s in STACKS] or ["unknown"]:
            w = work[(ttype, stack, bool(t["strong"]))]
            w["tasks"] += 1
            w["success"] += t["outcome"] == "success"
            w["verified"] += t["verify_passed"] == 1
            w["first_try"] += bool(t["checks"] and t["checks"][0]["passed"])
            w["corrected"] += bool(t["corrected"])
            for c in t["checks"]:
                cmd = distill.normalize_check(c["command"] or "")
                if cmd and _CHECK.match(cmd):
                    checks[(stack, cmd)]["runs"] += 1
                    checks[(stack, cmd)]["passed"] += bool(c["passed"])
    pack = {
        "schema": SCHEMA, "tidos_version": _version(), "install": accounts.install_id(),
        "date": datetime.now(timezone.utc).date().isoformat(),
        "work": [dict(v, type=k[0], stack=k[1], strong=k[2]) for k, v in sorted(work.items())],
        "checks": sorted((dict(v, stack=k[0], check=k[1]) for k, v in checks.items()),
                         key=lambda c: -c["runs"])[:40],
        "guide": [], "dungeons": [], "tools": [], "army": [],
    }
    from tidos_session import effect
    for row in effect.guidance_effect(conn):
        model = _model(row["model"])
        if model:
            pack["guide"].append({"model": model, **{side: {k: row[side][k] for k in ("tasks", "verified", "passed")}
                                                     for side in ("guided", "unguided")}})
    for r in conn.execute("SELECT model, with_tidos, COUNT(*) n, SUM(passed) p FROM evals "
                          "WHERE agent NOT IN ('reference', 'noop') AND COALESCE(error, '') NOT LIKE 'contaminated%' "
                          "GROUP BY model, with_tidos"):
        model = _model((r["model"] or "").split(" [")[0])
        if model:
            pack["dungeons"].append({"agent": model, "mode": {0: "off", 1: "on", 2: "guide", 3: "unit"}.get(r["with_tidos"], "?"),
                                     "runs": r["n"], "passed": r["p"] or 0})
    from tidos_scout import scout
    for name, u in scout.usage_xp(conn).items():
        pack["tools"].append({"tool": name, "runs": u["runs"], "passed": u["passed"]})
    from . import army
    public = {os.path.splitext(f)[0] for f in os.listdir(os.path.join(REPO_ROOT, ".claude", "agents"))} \
        | set(army.NATIVE.values())
    for u in army.compute(conn):
        if u["name"] in public and u["missions"]:  # never the names of your own (project) specialists
            pack["army"].append({"unit": u["name"], "missions": u["missions"], "xp": u["xp"], "success": u["success"]})
    return pack


# --- upload ---------------------------------------------------------------------------------------------
def _state_path():
    return os.path.join(tidos_home(), "share.json")


def last_upload():
    try:
        with open(_state_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _google_session():
    try:
        with open(os.path.join(tidos_home(), "tidos-session.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def due():
    last = last_upload().get("at")
    if not last:
        return True
    return datetime.now(timezone.utc) - datetime.fromisoformat(last) > EVERY


def upload(conn, fb=None, cfg=None):
    """Send today's pack (only with consent). Returns (ok, detail)."""
    if consent() != "agree":
        return False, "not shared: you did not agree (TIDOS works normally and learns only on this computer)"
    session = _google_session()
    if not session or not session.get("refreshToken"):
        return False, "sign in with Google once to share: python -I tidos_session/__main__.py consent agree"
    if fb is None:
        from tidos_dashboard import firebase as fb
    if cfg is None:
        from tidos_dashboard import config
        cfg = config.load()
    try:
        id_token, uid = fb.refresh_id_token(cfg, session["refreshToken"])
        pack = build(conn)
        fb.set_doc(cfg, id_token, "contributions/%s/packs/%s" % (uid, pack["date"]), pack)
    except fb.FirebaseError as e:
        return False, "upload failed: %s" % e
    state = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "date": pack["date"],
             "work_rows": len(pack["work"])}
    os.makedirs(tidos_home(), exist_ok=True)
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f)
    return True, "shared the %s pack (%d work rows, %d checks)" % (pack["date"], len(pack["work"]), len(pack["checks"]))
