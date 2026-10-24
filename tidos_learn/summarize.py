"""LEARN mode, automatic: a strong model turns a finished session into advice for weaker models.

At START TIDOS (no hooks needed), up to MAX_PER_START recent strong-model sessions that have not been
summarized yet are digested (prompts, files, checks, corrections - no file contents) and sent to a cheap
strong model (`claude -p`, budget-capped). Its 1-3 lines of advice become notes in that project's
playbooks. Switch "auto_summarize" in /TIDOSZIT turns it off.
"""
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone

from tidos_brain import control
from tidos_session.detect import tidos_home, tier_for

from . import distill

MAX_PER_START = 2
MODEL = "haiku"
BUDGET_USD = 0.05
MIN_TASKS = 2

PROMPT = """You are the learning engine of TIDOS. Below is a digest of a coding session a strong AI model did with
the user on the project "{project}". Write 1 to 3 pieces of advice for a WEAKER model that will work on this
project later: where things live, a trap that was hit or avoided, how work is verified here.
Rules: each piece on its own line starting with "- ", at most 200 characters, concrete (real file paths and
commands from the digest), no secrets, no greetings, nothing else.

{digest}"""


def _state_path():
    return os.path.join(tidos_home(), "summarized.json")


def _load_state():
    try:
        with open(_state_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(state):
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump(state, f, indent=1)


def digest(conn, session_id, limit=12):
    """Compact, sanitized description of a session (all strings were sanitized at import)."""
    session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    lines = []
    for t in conn.execute("SELECT * FROM tasks WHERE session_id = ? ORDER BY seq LIMIT ?", (session_id, limit)):
        calls = conn.execute("SELECT kind, summary, is_error FROM tool_calls WHERE task_id = ? ORDER BY id", (t["id"],)).fetchall()
        reads = [distill.relpath(c["summary"], session["cwd"]) for c in calls if c["kind"] == "read"]
        edits = [distill.relpath(c["summary"], session["cwd"]) for c in calls if c["kind"] == "edit"]
        checks = conn.execute("SELECT command, passed FROM verifications WHERE task_id = ? ORDER BY id", (t["id"],)).fetchall()
        lines.append("Task: %s" % (t["prompt"] or "")[:200].replace("\n", " "))
        if reads:
            lines.append("  read: %s" % ", ".join(sorted({r for r in reads if r})[:6]))
        if edits:
            lines.append("  changed: %s" % ", ".join(sorted({e for e in edits if e})[:6]))
        for c in checks[-3:]:
            cmd = distill.normalize_check(c["command"]) or (c["command"] or "")[:60]
            lines.append("  check: %s -> %s" % (cmd, "passed" if c["passed"] else "FAILED"))
        lines.append("  outcome: %s%s" % (t["outcome"], ", user corrected it" if t["corrected"] else ""))
    return session["project"], "\n".join(lines)


def pending_sessions(conn, limit=MAX_PER_START):
    state = _load_state()
    rows = conn.execute("SELECT s.id, s.model, s.project, COUNT(t.id) n, SUM(t.outcome = 'success') ok FROM sessions s "
                        "JOIN tasks t ON t.session_id = s.id GROUP BY s.id ORDER BY s.ended_at DESC").fetchall()
    out = []
    for r in rows:
        if r["id"] in state or r["project"] in ("~", "?", None) or r["n"] < MIN_TASKS or not r["ok"]:
            continue
        if tier_for(r["model"] or "unknown")[0] != "frontier":
            continue
        out.append(r["id"])
        if len(out) >= limit:
            break
    return out


def ask_strong_model(prompt, model=MODEL, budget=BUDGET_USD):
    exe = shutil.which("claude")
    if not exe:
        return None, "claude CLI not found"
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    try:
        proc = subprocess.run([exe, "-p", "--model", model, "--output-format", "json", "--max-budget-usd", str(budget)],
                              input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=180, env=env, cwd=tidos_home())
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError, OSError) as e:
        return None, str(e)
    if data.get("is_error"):
        return None, data.get("subtype") or "error"
    return data.get("result", ""), None


def advice_lines(text):
    return [line[2:].strip()[:200] for line in (text or "").splitlines()
            if line.strip().startswith("- ") and len(line.strip()) > 12][:3]


def summarize_session(conn, session_id, ask=ask_strong_model):
    project, text = digest(conn, session_id)
    result, error = ask(PROMPT.format(project=project, digest=text))
    state = _load_state()
    lines = advice_lines(result) if result else []
    for line in lines:
        distill.add_note(project, "any", line, "session-summary")
    state[session_id] = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "notes": len(lines),
                         "error": error}
    _save_state(state)
    return lines, error


def summarize_pending(conn, ask=ask_strong_model, limit=MAX_PER_START):
    if not control.is_on("auto_summarize"):
        return []
    return [(sid,) + summarize_session(conn, sid, ask) for sid in pending_sessions(conn, limit)]
