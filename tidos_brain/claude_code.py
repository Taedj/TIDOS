"""Claude Code collector: transcript importer + hook handler.

Transcripts: ~/.claude/projects/<project>/<session-id>.jsonl (one JSON object per line).
A *task* is one real user prompt plus everything the assistant did until the next prompt.
Subagent (sidechain) lines are skipped; their parent's Agent tool call is kept.
"""
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

from . import privacy, scoring

SOURCE = "claude-code"
PROJECTS_DIR = os.path.join(os.path.expanduser("~"), ".claude", "projects")

# Injected, non-human user messages
_NOT_A_PROMPT = re.compile(r"^\s*(<system-reminder>|<local-command-|Caveat:|Base directory for this skill|"
                           r"\[Request interrupted|<task-notification>|This session is being continued)")
_SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL)
_COMMAND = re.compile(r"<command-name>(.*?)</command-name>.*?(?:<command-args>(.*?)</command-args>)?", re.DOTALL)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def extract_prompt(entry):
    """Return the human prompt text of a user entry, or None if it is not a real prompt."""
    if entry.get("isMeta") or entry.get("isCompactSummary"):
        return None
    content = entry.get("message", {}).get("content")
    if isinstance(content, list) and content and all(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    text = _text_of(content)
    cmd = _COMMAND.search(text)
    if cmd:
        return ("%s %s" % (cmd.group(1).strip(), (cmd.group(2) or "").strip())).strip()
    text = _SYSTEM_REMINDER.sub("", text).strip()
    if not text or _NOT_A_PROMPT.match(text):
        return None
    return text


def _summary(tool, tool_input):
    if not isinstance(tool_input, dict):
        return None
    for key in ("command", "file_path", "notebook_path", "pattern", "url", "query", "description", "skill"):
        if tool_input.get(key):
            return str(tool_input[key])
    return None


def _result_text(block):
    content = block.get("content")
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return str(content or "")


def parse_transcript(path):
    """Parse a transcript into (session_dict, [task_dict]). Pure function, no DB."""
    session = {"id": None, "source": SOURCE, "model": None, "cwd": None, "project": None,
               "git_branch": None, "title": None, "transcript": path,
               "started_at": None, "ended_at": None}
    tasks, pending = [], {}  # pending: tool_use_id -> (task, call)
    models = {}
    counted_messages = set()
    current = None

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            etype = entry.get("type")
            if etype == "ai-title" and entry.get("aiTitle"):
                session["title"] = entry["aiTitle"]
                continue
            if etype not in ("user", "assistant") or entry.get("isSidechain"):
                continue

            session["id"] = session["id"] or entry.get("sessionId")
            session["cwd"] = session["cwd"] or entry.get("cwd")
            session["git_branch"] = session["git_branch"] or entry.get("gitBranch")
            ts = entry.get("timestamp")
            if ts:
                session["started_at"] = session["started_at"] or ts
                session["ended_at"] = ts
            message = entry.get("message") or {}

            if etype == "user":
                prompt = extract_prompt(entry)
                if prompt is not None:
                    if current is not None and scoring.is_correction(prompt):
                        current["corrected"] = 1
                    current = {"seq": len(tasks), "prompt": prompt, "started_at": ts, "ended_at": ts,
                               "model": None, "calls": [], "verifications": [],
                               "corrected": 0, "input_tokens": 0, "output_tokens": 0}
                    tasks.append(current)
                    continue
                for block in message.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        task_call = pending.pop(block.get("tool_use_id"), None)
                        if not task_call:
                            continue
                        task, call = task_call
                        call["is_error"] = 1 if block.get("is_error") else 0
                        if call["verify"]:
                            task["verifications"].append({
                                "ts": ts, "command": call["summary"],
                                "passed": 1 if scoring.verify_passed(call["is_error"], _result_text(block)) else 0})
                continue

            # assistant entry
            if current is None:
                continue
            current["ended_at"] = ts or current["ended_at"]
            model = message.get("model")
            if model and not model.startswith("<"):
                current["model"] = model
                models[model] = models.get(model, 0) + 1
            # one API message is split over several lines that repeat the same usage
            if message.get("id") not in counted_messages:
                counted_messages.add(message.get("id"))
                usage = message.get("usage") or {}
                # with prompt caching most input is reported as cache reads/writes
                current["input_tokens"] += sum(int(usage.get(k) or 0) for k in (
                    "input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
                current["output_tokens"] += int(usage.get("output_tokens") or 0)
            for block in message.get("content") or []:
                if not isinstance(block, dict) or block.get("type") != "tool_use":
                    continue
                tool = block.get("name", "?")
                summary = _summary(tool, block.get("input"))
                call = {"ts": ts, "tool": tool, "kind": scoring.tool_kind(tool), "summary": summary,
                        "is_error": 0,
                        "verify": scoring.tool_kind(tool) == "exec" and scoring.is_verify_command(summary)}
                current["calls"].append(call)
                pending[block.get("id")] = (current, call)

    if models:
        session["model"] = max(models, key=models.get)
    if session["cwd"]:
        cwd = os.path.normpath(session["cwd"])
        # the home folder's name is the user's name: never store it as a project name
        if os.path.normcase(cwd) == os.path.normcase(os.path.normpath(os.path.expanduser("~"))):
            session["project"] = "~"
        else:
            session["project"] = os.path.basename(cwd.rstrip("\\/")) or cwd
    if not session["id"]:
        session["id"] = os.path.splitext(os.path.basename(path))[0]

    for task in tasks:
        verifs = task["verifications"]
        task["tool_calls"] = len(task["calls"])
        task["tool_errors"] = sum(c["is_error"] for c in task["calls"])
        task["files_edited"] = len({c["summary"] for c in task["calls"] if c["kind"] == "edit"})
        task["verify_runs"] = len(verifs)
        task["verify_passed"] = verifs[-1]["passed"] if verifs else None
        task["score"], task["outcome"] = scoring.score_task(
            None if task["verify_passed"] is None else bool(task["verify_passed"]),
            task["corrected"], task["tool_errors"])
    return session, tasks


def store(conn, session, tasks):
    """Replace a session's trace in the DB (idempotent re-import)."""
    clean = privacy.clean
    with conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session["id"],))  # cascades to tasks/calls
        conn.execute(
            "INSERT INTO sessions (id, source, model, cwd, project, git_branch, title, transcript,"
            " started_at, ended_at, imported_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (session["id"], session["source"], session["model"], clean(session["cwd"]),
             session["project"], session["git_branch"], clean(session["title"]), session["transcript"],
             session["started_at"], session["ended_at"], _now()))
        for t in tasks:
            cur = conn.execute(
                "INSERT INTO tasks (session_id, seq, prompt, model, started_at, ended_at, tool_calls,"
                " tool_errors, files_edited, verify_runs, verify_passed, corrected, input_tokens,"
                " output_tokens, score, outcome) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (session["id"], t["seq"], clean(t["prompt"], privacy.MAX_PROMPT_CHARS), t["model"],
                 t["started_at"], t["ended_at"], t["tool_calls"], t["tool_errors"], t["files_edited"],
                 t["verify_runs"], t["verify_passed"], t["corrected"], t["input_tokens"],
                 t["output_tokens"], t["score"], t["outcome"]))
            task_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO tool_calls (task_id, ts, tool, kind, summary, is_error) VALUES (?,?,?,?,?,?)",
                [(task_id, c["ts"], c["tool"], c["kind"], clean(c["summary"]), c["is_error"])
                 for c in t["calls"]])
            conn.executemany(
                "INSERT INTO verifications (task_id, ts, command, passed) VALUES (?,?,?,?)",
                [(task_id, v["ts"], clean(v["command"]), v["passed"]) for v in t["verifications"]])


def import_transcript(conn, path):
    session, tasks = parse_transcript(path)
    store(conn, session, tasks)
    return session, tasks


def import_all(conn, projects_dir=PROJECTS_DIR):
    """Import every top-level transcript (subagent transcripts live in subfolders and are skipped)."""
    results = []
    for path in sorted(glob.glob(os.path.join(projects_dir, "*", "*.jsonl"))):
        try:
            results.append(import_transcript(conn, path))
        except (OSError, ValueError) as e:
            print("skip %s: %s" % (path, e), file=sys.stderr)
    return results


# --- Hook handler -----------------------------------------------------------

def handle_hook(conn, payload, background_import=True):
    """Record one Claude Code hook event. Must be fast and must never raise to the caller."""
    event = payload.get("hook_event_name") or "unknown"
    tool = payload.get("tool_name")
    summary = None
    is_error = 0
    if event == "UserPromptSubmit":
        summary = payload.get("prompt")
    elif tool:
        summary = _summary(tool, payload.get("tool_input"))
        response = payload.get("tool_response")
        if isinstance(response, dict) and (response.get("is_error") or response.get("interrupted")):
            is_error = 1
    with conn:
        conn.execute(
            "INSERT INTO live_events (ts, session_id, source, event, tool, summary, is_error, cwd)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (_now(), payload.get("session_id"), SOURCE, event, tool, privacy.clean(summary),
             is_error, privacy.clean(payload.get("cwd"))))

    transcript = payload.get("transcript_path")
    if event in ("Stop", "SessionEnd") and transcript and os.path.isfile(transcript):
        if background_import:
            _spawn_import(transcript)
        else:
            import_transcript(conn, transcript)


def _spawn_import(transcript):
    """Re-import the transcript in a detached process so the hook returns immediately."""
    main = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__main__.py")
    kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, "-I", main, "import-claude", "--transcript", transcript], **kwargs)
