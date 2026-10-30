"""Graduated trust: each kind of action TIDOS can take earns (or loses) the right to run by itself.

Levels, lowest first:
  observe   shown only; TIDOS does not even suggest running it
  propose   TIDOS suggests it, you click
  act_undo  TIDOS runs it by itself, records it in the action journal and you can undo it
  act       TIDOS runs it by itself (still journaled)
A kind moves up one level after PROMOTE_AFTER good actions in a row (a job that finished, an activation you kept
for SETTLE_DAYS); an undo by you moves it down one level and resets the streak; a failed job resets the streak.
Some kinds are capped (CEILING): changing what your agents do is never more than act_undo.
You can set any level yourself in the control center; your choice is never raised again by TIDOS for that kind
until you clear it.

Files (private, ~/.tidos): trust.json {kind: {level, streak, pinned}} and actions.jsonl (the journal).
"""
import json
import os
from datetime import datetime, timedelta, timezone

from tidos_session.detect import tidos_home

LEVELS = ["observe", "propose", "act_undo", "act"]
AUTO = ("act_undo", "act")
DEFAULTS = {"distill": "act", "daily_quest": "act", "backup": "act", "diagnose": "act", "validate_dungeons": "act",
            "trial": "act", "raid": "act", "measure": "act", "summarize": "act",
            "self_improve": "act_undo", "activate_unit": "propose", "configure_tool": "propose"}
CEILING = {"self_improve": "act_undo", "activate_unit": "act_undo", "configure_tool": "act_undo"}
PROMOTE_AFTER = 3
SETTLE_DAYS = 3
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _undo_activate(action):
    from tidos_learn import army
    return "removed %s (the draft is kept)" % army.deactivate(action["target"])


def _undo_self_improve(action):
    """Delete the unmerged auto/ branch of that proposal and put the proposal back to 'new' (not re-implemented)."""
    import subprocess
    from tidos_learn import evolve
    item = next((i for i in evolve.load() if i["id"] == action["target"]), None)
    branch = (item or {}).get("branch")
    if branch:
        git = lambda *a: subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True, text=True)  # noqa: E731
        if git("merge-base", "--is-ancestor", branch, "HEAD").returncode == 0:
            raise ValueError("%s is already merged: revert it with git instead" % branch)
        if git("rev-parse", "--verify", "--quiet", branch).returncode == 0:
            out = git("branch", "-D", branch)
            if out.returncode != 0:
                raise ValueError("could not delete %s: %s" % (branch, out.stderr.strip()))
    if item:
        evolve.set_status(item["id"], "new", branch=None, note="implementation undone")
    return "deleted %s" % branch if branch else "nothing was committed"


def _undo_configure(action):
    from tidos_scout import recipes
    t = action["target"] or {}
    return "; ".join(recipes.unconfigure(t.get("tool"), t.get("project")))


UNDO = {"activate_unit": _undo_activate, "self_improve": _undo_self_improve,
        "configure_tool": _undo_configure}  # kind -> reverses one action


def _now():
    return datetime.now(timezone.utc)


def _path(name):
    return os.path.join(tidos_home(), name)


def _load():
    try:
        with open(_path("trust.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data):
    os.makedirs(tidos_home(), exist_ok=True)
    tmp = _path("trust.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, _path("trust.json"))


def level(kind):
    return _load().get(kind, {}).get("level") or DEFAULTS.get(kind, "propose")


def allows_auto(kind):
    return level(kind) in AUTO


def levels():
    """[{kind, level, streak, pinned, default, ceiling}] for the control center."""
    data = _load()
    return [{"kind": k, "level": level(k), "streak": data.get(k, {}).get("streak", 0),
             "pinned": bool(data.get(k, {}).get("pinned")), "default": DEFAULTS[k], "ceiling": CEILING.get(k, "act")}
            for k in DEFAULTS]


def _move(kind, step, why):
    data = _load()
    s = data.setdefault(kind, {"level": level(kind), "streak": 0})
    s.setdefault("level", level(kind))
    if step == 0:
        s["streak"] = 0
    elif step > 0:
        s["streak"] = s.get("streak", 0) + 1
        top = LEVELS.index(CEILING.get(kind, "act"))
        if s["streak"] >= PROMOTE_AFTER and not s.get("pinned") and LEVELS.index(s["level"]) < top:
            s["level"], s["streak"] = LEVELS[LEVELS.index(s["level"]) + 1], 0
            s["changed"] = {"at": _now().isoformat(timespec="seconds"), "why": why}
    else:
        s["streak"] = 0
        s["level"] = LEVELS[max(0, LEVELS.index(s["level"]) - 1)]
        s["changed"] = {"at": _now().isoformat(timespec="seconds"), "why": why}
    _save(data)
    return s["level"]


def set_level(kind, new_level):
    """Your choice: pinned, so TIDOS never promotes it again (None clears it back to earned trust)."""
    if kind not in DEFAULTS:
        raise ValueError("unknown kind of action: %r" % kind)
    data = _load()
    if new_level is None:
        data.pop(kind, None)
    elif new_level not in LEVELS:
        raise ValueError("level must be one of %s" % ", ".join(LEVELS))
    else:
        data[kind] = {"level": new_level, "streak": 0, "pinned": True}
    _save(data)
    return level(kind)


# --- the action journal -----------------------------------------------------------------------------------
def journal(limit=None):
    items = []
    try:
        with open(_path("actions.jsonl"), "r", encoding="utf-8") as f:
            items = [json.loads(line) for line in f if line.strip()]
    except (OSError, ValueError):
        pass
    return items[-limit:] if limit else items


def _save_journal(items):
    os.makedirs(tidos_home(), exist_ok=True)
    tmp = _path("actions.jsonl.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        for item in items[-1000:]:
            f.write(json.dumps(item) + "\n")
    os.replace(tmp, _path("actions.jsonl"))


def record(kind, title, by="autopilot", target=None, job_id=None):
    """Write an action to the journal; its outcome is settled later (settle())."""
    items = journal()
    item = {"id": max([i["id"] for i in items] or [0]) + 1, "at": _now().isoformat(timespec="seconds"),
            "kind": kind, "title": title[:200], "by": by, "target": target, "job_id": job_id,
            "level": level(kind), "state": "open", "undoable": kind in UNDO}
    _save_journal(items + [item])
    return item


def _set(action_id, **fields):
    items = journal()
    for i in items:
        if i["id"] == action_id:
            i.update(fields)
            _save_journal(items)
            return i
    raise KeyError(action_id)


def undo(action_id):
    """Reverse one action (only kinds with an undo), mark it undone and lower that kind's trust one level."""
    item = next((i for i in journal() if i["id"] == action_id), None)
    if item is None:
        raise KeyError(action_id)
    if item["state"] == "undone":
        raise ValueError("already undone")
    if item["kind"] not in UNDO:
        raise ValueError("%s cannot be undone" % item["kind"])
    detail = UNDO[item["kind"]](item)
    _move(item["kind"], -1, "you undid #%d" % action_id)
    return _set(action_id, state="undone", undone_at=_now().isoformat(timespec="seconds"), undo_detail=detail)


def reversed_by_you(kind, target):
    """You reversed an action yourself (e.g. deactivated a unit TIDOS activated): same effect as an undo."""
    item = next((i for i in reversed(journal()) if i["kind"] == kind and i.get("target") == target
                 and i["state"] != "undone" and i["by"] != "owner"), None)
    if item is None:
        return None
    _move(kind, -1, "you reversed #%d" % item["id"])
    return _set(item["id"], state="undone", undone_at=_now().isoformat(timespec="seconds"), undo_detail="by you")


def settle(job_state=None):
    """Close open actions: a job that finished is good, a failed one resets the streak; other actions are good once
    they were kept SETTLE_DAYS. Each good action counts toward promotion. Returns the actions settled."""
    if job_state is None:
        from tidos_dashboard import jobs
        job_state = lambda job_id: (jobs.get(job_id) or {}).get("state")  # noqa: E731
    settled = []
    for i in journal():
        if i["state"] != "open":
            continue
        good = True
        if i.get("job_id"):
            state = job_state(i["job_id"])
            if state in ("running", "cancelling"):
                continue
            good = state == "done"
        young = _now() - datetime.fromisoformat(i["at"]) < timedelta(days=SETTLE_DAYS)
        if good and young and (i["kind"] in UNDO or not i.get("job_id")):
            continue  # an action you can undo counts only once you kept it SETTLE_DAYS
        _move(i["kind"], 1 if good else 0, "%d good actions in a row" % PROMOTE_AFTER)
        settled.append(_set(i["id"], state="kept" if good else "failed",
                            settled_at=_now().isoformat(timespec="seconds")))
    return settled
