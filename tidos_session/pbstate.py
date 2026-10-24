"""Playbook usage + user overrides: ~/.tidos/playbook_state.json (survives playbook regeneration).

  served   {relative path: {"n": count, "last": date}}  - which playbooks GUIDE briefs actually used
  disabled [relative path, ...]                          - turned off in /TIDOSZIT; never served
"""
import json
import os
from datetime import datetime, timezone

from .detect import tidos_home


def playbooks_dir():
    return os.path.join(tidos_home(), "playbooks")


def _path():
    return os.path.join(tidos_home(), "playbook_state.json")


def load():
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        state = {}
    state.setdefault("served", {})
    state.setdefault("disabled", [])
    return state


def save(state):
    os.makedirs(tidos_home(), exist_ok=True)
    tmp = _path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)
    os.replace(tmp, _path())


def rel(path):
    return os.path.relpath(path, playbooks_dir()).replace("\\", "/")


def record_served(paths):
    state = load()
    today = datetime.now(timezone.utc).date().isoformat()
    for p in paths:
        entry = state["served"].setdefault(rel(p), {"n": 0, "last": None})
        entry["n"] += 1
        entry["last"] = today
    save(state)


def is_disabled(path):
    return rel(path) in load()["disabled"]


def set_disabled(relpath, disabled):
    state = load()
    items = set(state["disabled"])
    if disabled:
        items.add(relpath)
    else:
        items.discard(relpath)
    state["disabled"] = sorted(items)
    save(state)
    return state
