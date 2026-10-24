"""OpenCode collector: imports sessions from OpenCode's own SQLite database (read-only).

Database: ~/.local/share/opencode/opencode.db (tables session / message / part; JSON in `data`).
Only session, message and part rows are read - never the account / credential tables.
A task = one user prompt + everything the assistant did until the next prompt. Sub-agent sessions
(parent_id set) and TIDOS's own test runs are skipped. Stored with the same scoring as Claude Code.
"""
import json
import os
import sqlite3
from datetime import datetime, timezone

from . import scoring
from .claude_code import finalize_tasks, is_synthetic, store

SOURCE = "opencode"
TOOL_KINDS = {"bash": "exec", "read": "read", "edit": "edit", "write": "edit", "patch": "edit", "multiedit": "edit",
              "grep": "search", "glob": "search", "list": "search", "webfetch": "web", "websearch": "web",
              "task": "delegate"}


def db_path():
    return os.environ.get("OPENCODE_DB") or os.path.join(os.path.expanduser("~"), ".local", "share", "opencode",
                                                         "opencode.db")


def _iso(ms):
    return datetime.fromtimestamp((ms or 0) / 1000, tz=timezone.utc).isoformat(timespec="seconds") if ms else None


def _summary(tool, inp):
    if not isinstance(inp, dict):
        return None
    for key in ("command", "filePath", "file_path", "path", "pattern", "url", "query", "description"):
        if inp.get(key):
            return str(inp[key])
    return None


def parse_session(src, session_row):
    sid, directory, title, created, updated = session_row
    session = {"id": "oc:" + sid, "source": SOURCE, "model": None, "cwd": directory, "project": None,
               "git_branch": None, "title": title, "transcript": "opencode:" + sid,
               "started_at": _iso(created), "ended_at": _iso(updated)}
    messages = src.execute("SELECT id, time_created, data FROM message WHERE session_id = ? ORDER BY time_created, id",
                           (sid,)).fetchall()
    parts = {}
    for mid, data in src.execute("SELECT message_id, data FROM part WHERE session_id = ? ORDER BY time_created, id",
                                 (sid,)):
        parts.setdefault(mid, []).append(json.loads(data))

    tasks, models, current = [], {}, None
    for mid, created_ms, data in messages:
        msg = json.loads(data)
        ts = _iso(created_ms)
        if msg.get("role") == "user":
            text = "\n".join(p.get("text", "") for p in parts.get(mid, []) if p.get("type") == "text"
                             and not p.get("synthetic")).strip()
            if not text:
                continue
            if current is not None and scoring.is_correction(text):
                current["corrected"] = 1
            current = {"seq": len(tasks), "prompt": text, "started_at": ts, "ended_at": ts, "model": None,
                       "calls": [], "verifications": [], "corrected": 0, "input_tokens": 0, "output_tokens": 0}
            tasks.append(current)
            continue
        if current is None:
            continue
        current["ended_at"] = ts
        if msg.get("modelID"):
            model = "%s/%s" % (msg.get("providerID", "?"), msg["modelID"])
            current["model"] = model
            models[model] = models.get(model, 0) + 1
        for part in parts.get(mid, []):
            if part.get("type") == "step-finish":
                tokens = part.get("tokens") or {}
                cache = tokens.get("cache") or {}
                current["input_tokens"] += int(tokens.get("input") or 0) + int(cache.get("read") or 0) \
                    + int(cache.get("write") or 0)
                current["output_tokens"] += int(tokens.get("output") or 0)
            if part.get("type") != "tool":
                continue
            tool = part.get("tool", "?")
            state = part.get("state") or {}
            summary = _summary(tool, state.get("input"))
            is_error = 1 if state.get("status") == "error" else 0
            kind = TOOL_KINDS.get(tool, "other")
            current["calls"].append({"ts": ts, "tool": tool, "kind": kind, "summary": summary, "is_error": is_error})
            if kind == "exec" and scoring.is_verify_command(summary):
                current["verifications"].append({
                    "ts": ts, "command": summary,
                    "passed": 1 if scoring.verify_passed(is_error, str(state.get("output", ""))) else 0})
    if models:
        session["model"] = max(models, key=models.get)
    if directory:
        norm = os.path.normpath(directory)
        home = os.path.normpath(os.path.expanduser("~"))
        session["project"] = "~" if os.path.normcase(norm) == os.path.normcase(home) else \
            (os.path.basename(norm.rstrip("\\/")) or norm)
    return session, finalize_tasks(tasks)


def import_all(conn, path=None):
    """Import every top-level OpenCode session. Returns [(session, tasks)] of imported sessions."""
    path = path or db_path()
    if not os.path.exists(path):
        return []
    src = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
    try:
        rows = src.execute("SELECT id, directory, title, time_created, time_updated FROM session "
                           "WHERE parent_id IS NULL ORDER BY time_created").fetchall()
        known = {r[0]: r[1] for r in conn.execute("SELECT id, ended_at FROM sessions WHERE source = ?", (SOURCE,))}
        results = []
        for row in rows:
            if is_synthetic(row[1]) or row[1] in ("/", ""):
                continue
            if known.get("oc:" + row[0]) == _iso(row[4]):
                continue  # unchanged since the last import
            session, tasks = parse_session(src, row)
            if tasks:
                store(conn, session, tasks)
                results.append((session, tasks))
        return results
    finally:
        src.close()
