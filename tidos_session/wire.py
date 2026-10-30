"""Connect TIDOS to the AI tools on this machine, one tool at a time, only when the user asks.

Each tool needs two things (nothing else in its files is touched):
  1. the `tidos` MCP server: the model gets tidos_start, tidos_guide, tidos_verify...
  2. a TIDOS block in the tool's GLOBAL instructions file: call tidos_start once, tidos_guide at every request,
     tidos_verify before saying done
Locations (from each tool's documentation, 2026-10):
  OpenCode           ~/.config/opencode/opencode.json "mcp"             ~/.config/opencode/AGENTS.md
  Gemini CLI         ~/.gemini/settings.json "mcpServers"              ~/.gemini/GEMINI.md
  Antigravity        ~/.gemini/config/mcp_config.json "mcpServers"     ~/.gemini/GEMINI.md (shared with Gemini CLI)
  VS Code + Copilot  ~/.copilot/mcp-config.json "mcpServers"           ~/.copilot/copilot-instructions.md
  Codex CLI          ~/.codex/config.toml [mcp_servers.tidos]          ~/.codex/AGENTS.md
  Cline              ~/.cline/data/settings/cline_mcp_settings.json    ~/Documents/Cline/Rules/tidos.md
  Cursor, Windsurf   locations not confirmed: TIDOS shows what to paste, the user adds it
  Claude Code        the TIDOS plugin (hooks + MCP), not here
Nothing runs by itself: the control center (Tools) or `tidos_session wire --tool <id>` connects a tool.
A file that is not plain JSON (comments, errors) is left alone. Before the first change each file is copied to
<file>.tidos-backup. Disconnect removes exactly what was added.
"""
import json
import os
import shutil
import sys

from .detect import REPO_ROOT

BEGIN = "<!-- TIDOS:BEGIN (added by TIDOS; disconnect the tool in the control center to remove it) -->"
END = "<!-- TIDOS:END -->"
TOML_BEGIN = "# TIDOS:BEGIN (added by TIDOS; disconnect the tool in the control center to remove it)"
TOML_END = "# TIDOS:END"
BLOCK = """## TIDOS
TIDOS is connected to you through the `tidos` MCP tools. Use them in every session:
1. At the start of the session, call `tidos_start` once with `project_dir` = the absolute path of the current
   project (and `model` = your exact model id if you know it). Follow the brief it returns.
2. At every new request from the user, call `tidos_guide` with the request and `project_dir`, and follow it.
3. Before saying a task is done, call `tidos_verify` with `project_dir` and report its real result.
Never ask for, repeat or store passwords or tokens in the chat."""


def _server():
    return [sys.executable, "-I", os.path.join(REPO_ROOT, "tidos_mcp", "__main__.py")]


def _home_env(var, home, default):
    """A tool's own home (COPILOT_HOME, CODEX_HOME...) on the real machine; tests pass `home` and get the default."""
    return (os.environ.get(var) if home is None else None) or default


# id, label, cli (on PATH = installed), marker folders, MCP (file, format, section), instructions (file, mode)
def _tools(home=None):
    h = home or os.path.expanduser("~")
    j = os.path.join
    gem, oc = j(h, ".gemini"), j(h, ".config", "opencode")
    copilot = _home_env("COPILOT_HOME", home, j(h, ".copilot"))
    codex = _home_env("CODEX_HOME", home, j(h, ".codex"))
    cline_mcp = _home_env("CLINE_MCP_SETTINGS_PATH", home, j(h, ".cline", "data", "settings", "cline_mcp_settings.json"))
    return [
        {"id": "claude-code", "label": "Claude Code", "cli": "claude", "dirs": [j(h, ".claude")], "plugin": True},
        {"id": "opencode", "label": "OpenCode", "cli": "opencode", "dirs": [oc],
         "mcp": (j(oc, "opencode.json"), "opencode", "mcp"), "rules": (j(oc, "AGENTS.md"), "block")},
        {"id": "gemini-cli", "label": "Gemini CLI", "cli": "gemini", "dirs": [], "files": [j(gem, "settings.json")],
         "mcp": (j(gem, "settings.json"), "json", "mcpServers"), "rules": (j(gem, "GEMINI.md"), "block")},
        {"id": "antigravity", "label": "Antigravity", "cli": "antigravity",
         "dirs": [j(gem, "config"), j(gem, "antigravity"), j(gem, "antigravity-ide")],
         "mcp": (j(gem, "config", "mcp_config.json"), "json", "mcpServers"), "rules": (j(gem, "GEMINI.md"), "block")},
        {"id": "vscode-copilot", "label": "VS Code + Copilot", "cli": "code", "dirs": [copilot],
         "mcp": (j(copilot, "mcp-config.json"), "json", "mcpServers"),
         "rules": (j(copilot, "copilot-instructions.md"), "block")},
        {"id": "codex", "label": "Codex CLI", "cli": "codex", "dirs": [codex],
         "mcp": (j(codex, "config.toml"), "toml", "mcp_servers"), "rules": (j(codex, "AGENTS.md"), "block")},
        {"id": "cline", "label": "Cline", "cli": "cline", "dirs": [j(h, ".cline"), j(h, "Documents", "Cline")],
         "mcp": (cline_mcp, "json", "mcpServers"), "rules": (j(h, "Documents", "Cline", "Rules", "tidos.md"), "file")},
        {"id": "cursor", "label": "Cursor", "cli": "cursor", "dirs": [j(h, ".cursor")], "manual": True},
        {"id": "windsurf", "label": "Windsurf", "cli": "windsurf", "dirs": [j(h, ".codeium", "windsurf"), j(h, ".devin")],
         "manual": True},
    ]


def _installed(t, home):
    if any(os.path.isdir(d) for d in t["dirs"]) or any(os.path.isfile(f) for f in t.get("files", [])):
        return True
    return home is None and bool(shutil.which(t["cli"]))  # tests (explicit home) never look at the real PATH


def find(tool_id, home=None):
    t = next((t for t in _tools(home) if t["id"] == tool_id), None)
    if t is None:
        raise ValueError("unknown tool: %r" % tool_id)
    return t


def manual_snippet():
    """What to paste into a tool TIDOS cannot configure itself (its MCP settings, then its rules)."""
    cmd = _server()
    return json.dumps({"mcpServers": {"tidos": {"command": cmd[0], "args": cmd[1:]}}}, indent=2) + "\n\n" + BLOCK


# --- files ------------------------------------------------------------------------------------------------
def _backup(path):
    if os.path.isfile(path) and not os.path.exists(path + ".tidos-backup"):
        shutil.copy2(path, path + ".tidos-backup")


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _write(path, text):
    _backup(path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _read_json(path):
    """dict, {} for a missing file, or None when the file is not plain JSON (left alone)."""
    if not os.path.isfile(path):
        return {}
    try:
        data = json.loads(_read(path))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _entry(fmt):
    cmd = _server()
    if fmt == "opencode":
        return {"type": "local", "command": cmd, "enabled": True}
    return {"command": cmd[0], "args": cmd[1:]}


def _toml_block():
    cmd = _server()  # JSON string escaping is valid TOML basic-string escaping
    return "%s\n[mcp_servers.tidos]\ncommand = %s\nargs = [%s]\n%s" % (
        TOML_BEGIN, json.dumps(cmd[0]), ", ".join(json.dumps(a) for a in cmd[1:]), TOML_END)


def _replace_block(text, begin, end, block):
    """text with the marked block inserted / replaced (block) or removed (None)."""
    if begin in text and end in text:
        start, stop = text.index(begin), text.index(end) + len(end)
        head, tail = text[:start].rstrip("\n"), text[stop:].lstrip("\n")
        parts = [p for p in (head, block, tail) if p]
        return "\n\n".join(parts).strip("\n") + ("\n" if parts else "")
    if block is None:
        return text
    return (text.rstrip("\n") + "\n\n" if text.strip() else "") + block + "\n"


def _has_mcp(t):
    path, fmt, section = t["mcp"]
    if fmt == "toml":
        return TOML_BEGIN in _read(path)
    return "tidos" in ((_read_json(path) or {}).get(section) or {})


def _has_rules(t):
    path, mode = t["rules"]
    return os.path.isfile(path) and (mode == "file" or BEGIN in _read(path))


# --- connect / disconnect ---------------------------------------------------------------------------------
def _set_mcp(t, on):
    path, fmt, section = t["mcp"]
    if fmt == "toml":
        text = _read(path)
        if on and "[mcp_servers.tidos]" in text and TOML_BEGIN not in text:
            return "skipped: a tidos server is already set by hand in %s" % path
        new = _replace_block(text, TOML_BEGIN, TOML_END, _toml_block() if on else None)
        if new == text:
            return "current"
        _write(path, new)
        return "added" if on else "removed"
    data = _read_json(path)
    if data is None:
        return "skipped: %s is not plain JSON, add the tidos server by hand" % path
    servers = data.get(section) or {}
    if on and servers.get("tidos") == _entry(fmt):
        return "current"
    if not on and "tidos" not in servers:
        return "current"
    if on:
        servers["tidos"] = _entry(fmt)
    else:
        del servers["tidos"]
    if servers:
        data[section] = servers
    else:
        data.pop(section, None)
    _write(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    return "added" if on else "removed"


def _set_rules(t, on, home):
    path, mode = t["rules"]
    if mode == "file":
        if on:
            if _read(path) == BLOCK + "\n":
                return "current"
            _write(path, BLOCK + "\n")
            return "added"
        if not os.path.isfile(path):
            return "current"
        os.remove(path)
        return "removed"
    if not on:  # a file shared with another connected tool (Gemini CLI + Antigravity) keeps the block
        others = [o for o in connectable(home) if o["id"] != t["id"] and o["rules"][0] == path and _has_mcp(o)]
        if others:
            return "kept: %s still uses it" % others[0]["label"]
    text = _read(path)
    new = _replace_block(text, BEGIN, END, (BEGIN + "\n" + BLOCK + "\n" + END) if on else None)
    if new == text:
        return "current"
    if not new.strip():  # the file only held the TIDOS block (TIDOS created it): remove it
        os.remove(path)
        if os.path.exists(path + ".tidos-backup") and not _read(path + ".tidos-backup").strip():
            os.remove(path + ".tidos-backup")
        return "removed"
    _write(path, new)
    return "added" if on else "removed"


def connectable(home=None):
    return [t for t in _tools(home) if "mcp" in t and _installed(t, home)]


def connect(tool_id, home=None):
    """Connect one tool. Returns [(file, status)]."""
    t = find(tool_id, home)
    if "mcp" not in t:
        raise ValueError("%s is not configured by TIDOS (%s)" % (t["label"], "plugin" if t.get("plugin") else "manual"))
    return [(t["mcp"][0], _set_mcp(t, True)), (t["rules"][0], _set_rules(t, True, home))]


def disconnect(tool_id, home=None):
    """Remove exactly what connect() added. Returns [(file, status)]."""
    t = find(tool_id, home)
    if "mcp" not in t:
        raise ValueError("%s is not configured by TIDOS" % t["label"])
    return [(t["mcp"][0], _set_mcp(t, False)), (t["rules"][0], _set_rules(t, False, home))]


def hint(tool_id, home=None):
    """One line for START TIDOS when the tool in use could be connected but is not ('' otherwise)."""
    row = next((r for r in tools(home) if r["id"] == tool_id), None)
    if not row or row["how"] != "auto" or row["connected"] or not row["installed"]:
        return ""
    return ("TIDOS is not connected to %s: any model there gets TIDOS by itself once you connect it in the "
            "control center (/TIDOSZIT > Tool Scout > Connect)." % row["label"])


def tools(home=None):
    """Every known tool for the control center: installed?, how it connects, connected?, the files involved."""
    out = []
    for t in _tools(home):
        row = {"id": t["id"], "label": t["label"], "installed": _installed(t, home)}
        if t.get("plugin"):
            row.update(how="plugin", connected=None, files=[])
        elif t.get("manual"):
            row.update(how="manual", connected=None, files=[])
        else:
            mcp, rules = _has_mcp(t), _has_rules(t)
            row.update(how="auto", mcp=mcp, instructions=rules, connected=mcp and rules,
                       files=[t["mcp"][0], t["rules"][0]])
        out.append(row)
    return out
