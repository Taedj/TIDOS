"""TIDOS kill switches: ~/.tidos/control.json (outside any repository).

Enforced by code, not by prompts:
  tracing         - tidos_brain hook records nothing when off
  auto_update     - scripts/start_tidos.* skip the update gate when off
  factory_sync    - scripts/factory_sync.* refuse to commit/push when off
  community_sync  - scripts/community_sync.* refuse to open PRs when off
  gptid           - scripts/gptid.* refuse to start the ChatGPT relay when off
  auth_gate       - scripts/start_tidos.* ask for Google sign-in only when on (opt-in)
  tool_install    - Tool Scout installs an approved tool only when on
  autopilot       - the control center runs the jobs TIDOS recommends by itself

Texts (same file): helper_model - the model TIDOS uses for its own jobs (tidos_session.helper): auto = the model
of your last START TIDOS (free fallback), none = local only. TIDOS is no-cost by design and works with any model.

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
    "auto_summarize": (True, "After strong-model sessions, the helper model writes advice notes for weaker models (max 2 per START)"),
    "auth_gate": (False, "Require Google sign-in at START TIDOS (the /TIDOSZIT owner login is always on)"),
    "tool_install": (False, "Tool Scout may install a tool you approved when you press Install (pinned version or verified download, your user account only)"),
    "autopilot": (False, "Autopilot: TIDOS runs the jobs it recommends by itself (one at a time, no-cost models only)"),
    "ask_llm": (True, "Ask TIDOS may send a sanitized digest of your traces to the helper model; off = local search only"),
}


TEXTS = {  # name -> (default, validator regex, description)
    "share_learning": ("unasked", r"^(unasked|agree|decline)$",
                       "Community learning: agree = share anonymous lessons (tidos_learn.share), decline = this computer only"),
    "helper_model": ("auto", r"^(auto|none|claude:[A-Za-z0-9.\-]+|gemini:[A-Za-z0-9.\-]+|"
                              r"opencode:[A-Za-z0-9._\-]+/[A-Za-z0-9._\-/]+)$",
                     "Model TIDOS uses for its own jobs: auto (the model of your last START TIDOS, else a free one), "
                     "none, or an explicit family:model"),
}


def path():
    return os.environ.get("TIDOS_CONTROL_FILE") or os.path.join(os.path.expanduser("~"), ".tidos", "control.json")


def _read():
    try:
        with open(path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}  # missing/corrupt file -> safe defaults


def _write(switches, texts):
    os.makedirs(os.path.dirname(path()), exist_ok=True)
    tmp = path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"switches": switches, "texts": texts,
                   "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}, f, indent=2)
    os.replace(tmp, path())


def load():
    state = {name: default for name, (default, _) in SWITCHES.items()}
    state.update({k: bool(v) for k, v in _read().get("switches", {}).items() if k in SWITCHES})
    return state


def texts():
    import re
    out = {name: spec[0] for name, spec in TEXTS.items()}
    for k, v in _read().get("texts", {}).items():
        if k in TEXTS and isinstance(v, str) and re.match(TEXTS[k][1], v):
            out[k] = v
    return out


def text(name):
    return texts()[name]


def set_text(name, value):
    import re
    if name not in TEXTS:
        raise KeyError(name)
    if not isinstance(value, str) or not re.match(TEXTS[name][1], value):
        raise ValueError("%s: not a valid value: %r" % (name, value))
    current = texts()
    current[name] = value
    _write(load(), current)
    return current


def is_on(name):
    return load()[name]


def set_switch(name, value):
    if name not in SWITCHES:
        raise KeyError(name)
    state = load()
    state[name] = bool(value)
    _write(state, texts())
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
