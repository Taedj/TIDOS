"""TIDOS kill switches: ~/.tidos/control.json (outside any repository).

Enforced by code, not by prompts:
  tracing         - tidos_brain hook records nothing when off
  auto_update     - scripts/start_tidos.* skip the update gate when off
  factory_sync    - scripts/factory_sync.* refuse to commit/push when off
  community_sync  - scripts/community_sync.* refuse to open PRs when off
  gptid           - scripts/gptid.* refuse to start the ChatGPT relay when off
  auth_gate       - scripts/start_tidos.* ask for Google sign-in only when on (opt-in)

Shell scripts read it with:  python -I tidos_brain/control.py get <switch>   (prints on/off, exit 0/1)
"""
import json
import os
import sys
from datetime import datetime, timezone

SWITCHES = {
    "tracing": (True, "Record Claude Code sessions into the brain"),
    "auto_update": (True, "Run the GitHub update gate on START TIDOS"),
    "factory_sync": (True, "Persona factory may commit + push generated personas"),
    "community_sync": (True, "Community sync may open upstream pull requests"),
    "gptid": (False, "ChatGPT browser relay (experimental, ToS risk)"),
    "auto_summarize": (True, "After strong-model sessions, a cheap strong model writes advice notes (max 2 per START, $0.05 each)"),
    "auth_gate": (False, "Require Google sign-in at START TIDOS (the /TIDOSZIT owner login is always on)"),
    "tool_install": (False, "Tool Scout may install a tool you approved when you press Install (pinned version or verified download, your user account only)"),
    "ask_llm": (True, "Ask TIDOS may send a sanitized digest of your traces to a cheap Claude model ($0.05 cap); off = local search only"),
}


def path():
    return os.environ.get("TIDOS_CONTROL_FILE") or os.path.join(os.path.expanduser("~"), ".tidos", "control.json")


def load():
    state = {name: default for name, (default, _) in SWITCHES.items()}
    try:
        with open(path(), "r", encoding="utf-8") as f:
            saved = json.load(f).get("switches", {})
        state.update({k: bool(v) for k, v in saved.items() if k in SWITCHES})
    except (OSError, ValueError):
        pass  # missing/corrupt file -> safe defaults
    return state


def is_on(name):
    return load()[name]


def set_switch(name, value):
    if name not in SWITCHES:
        raise KeyError(name)
    state = load()
    state[name] = bool(value)
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    tmp = path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"switches": state, "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
                  f, indent=2)
    os.replace(tmp, path())
    return state


def describe():
    state = load()
    return [{"name": n, "on": state[n], "default": d, "description": desc} for n, (d, desc) in SWITCHES.items()]


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "get" and sys.argv[2] in SWITCHES:
        on = is_on(sys.argv[2])
        print("on" if on else "off")
        sys.exit(0 if on else 1)
    print("usage: control.py get <%s>" % "|".join(SWITCHES), file=sys.stderr)
    sys.exit(2)
