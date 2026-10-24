"""TIDOS MCP server (stdio, JSON-RPC 2.0, stdlib only).

Any MCP client (Claude Code, OpenCode, Cursor, Gemini CLI, ...) can call TIDOS directly:
  tidos_start    START TIDOS for this project: detect model/tier, return the LEARN or GUIDE brief
  tidos_guide    guidance for ONE user request (task type, checks-first step, matching playbook, notes)
  tidos_verify   run the project's checks (or one given check command) and return exit codes + output
  tidos_recall   search what TIDOS learned (playbooks, strong-model notes, memory) for a keyword
  tidos_note     LEARN mode: leave one piece of advice for weaker models on this project
  tidos_propose  record an improvement idea for TIDOS itself (evolution queue, never auto-applied)
Messages are newline-delimited JSON on stdin/stdout (MCP stdio transport). Logs go to stderr only.
"""
import glob
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from tidos_session import cli as session_cli, detect, guide  # noqa: E402

PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
SERVER_INFO = {"name": "tidos", "version": "5.1.0"}
VERIFY_TIMEOUT = 300
# tidos_verify only runs check SUBCOMMANDS of known tools - never `python -c`, `node -e` or any shell
CHECK_RULES = {
    "python": ("-m", {"pytest", "unittest", "py_compile", "compileall", "mypy", "ruff", "flake8", "pylint"}),
    "python3": ("-m", {"pytest", "unittest", "py_compile", "compileall", "mypy", "ruff", "flake8", "pylint"}),
    "py": ("-m", {"pytest", "unittest", "py_compile", "compileall", "mypy", "ruff", "flake8", "pylint"}),
    "node": (None, {"--test"}),
    "npm": (None, {"test", "run"}), "pnpm": (None, {"test", "run"}), "yarn": (None, {"test", "run"}),
    "npx": (None, {"tsc", "eslint", "jest", "vitest"}),
    "flutter": (None, {"analyze", "test"}), "dart": (None, {"analyze", "test"}),
    "cargo": (None, {"test", "check", "clippy", "build"}), "go": (None, {"test", "vet", "build"}),
    "gradlew": (None, {"test", "build", "lint", "assembleDebug"}), "mvn": (None, {"test", "verify"}),
    "dotnet": (None, {"test", "build"}), "make": (None, {"test", "check"}),
    "pytest": (None, None), "tsc": (None, None), "eslint": (None, None), "ruff": (None, None), "mypy": (None, None),
}


def allowed_check(argv):
    """True when argv is a known check: tool + allowed subcommand (or `python -m <checker>`)."""
    if not argv:
        return False
    tool = os.path.basename(argv[0]).lower().replace(".exe", "").replace(".cmd", "").replace(".bat", "")
    if tool not in CHECK_RULES:
        return False
    flag, subs = CHECK_RULES[tool]
    if subs is None:
        return True
    if flag:
        return len(argv) >= 3 and argv[1] == flag and argv[2] in subs
    return len(argv) >= 2 and argv[1] in subs

TOOLS = [
    {"name": "tidos_start",
     "description": "START TIDOS for a project: detects the model tier and returns the brief to follow for the whole "
                    "session (LEARN mode on strong models, GUIDE mode on weak/free models). Call it once at the start.",
     "inputSchema": {"type": "object", "properties": {
         "project_dir": {"type": "string", "description": "absolute path of the user's project"},
         "model": {"type": "string", "description": "your exact model id if you know it"},
         "tool": {"type": "string", "description": "client name, e.g. claude-code, opencode"}},
         "required": ["project_dir"]}},
    {"name": "tidos_guide",
     "description": "Guidance for ONE user request: its task type, the first step (define done / checks first), "
                    "how this kind of task was solved before in this project, pitfalls and notes. Call it at the "
                    "start of every new request in GUIDE mode.",
     "inputSchema": {"type": "object", "properties": {
         "request": {"type": "string"}, "project_dir": {"type": "string"}}, "required": ["request", "project_dir"]}},
    {"name": "tidos_verify",
     "description": "Run the project's checks (detected: tests, analyzer, build) or one given check command, and "
                    "return the real exit codes and output. Use it before saying a task is done.",
     "inputSchema": {"type": "object", "properties": {
         "project_dir": {"type": "string"},
         "command": {"type": "string", "description": "optional check command, e.g. 'flutter analyze'"}},
         "required": ["project_dir"]}},
    {"name": "tidos_recall",
     "description": "Search what TIDOS learned from earlier sessions (playbooks, strong-model notes, user memory).",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string"}, "project": {"type": "string", "description": "optional project name"}},
         "required": ["query"]}},
    {"name": "tidos_note",
     "description": "LEARN mode: leave one short, concrete piece of advice for weaker models that will work on this "
                    "project later (where things live, a trap, how to verify).",
     "inputSchema": {"type": "object", "properties": {
         "project": {"type": "string"}, "advice": {"type": "string"}, "stack": {"type": "string"}},
         "required": ["project", "advice"]}},
    {"name": "tidos_propose",
     "description": "Record an improvement idea for TIDOS itself. It goes to a review queue; nothing is applied "
                    "automatically.",
     "inputSchema": {"type": "object", "properties": {
         "title": {"type": "string"}, "reason": {"type": "string"}}, "required": ["title", "reason"]}},
]


def _text(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def tool_start(args):
    session, facts, text = session_cli.start(args.get("tool") or "auto", args.get("model") or "auto",
                                             args["project_dir"], learn=True)
    return _text(session_cli.report(session, facts) + "\n" + text)


def tool_guide(args):
    return _text(guide.guidance(args["request"], args["project_dir"])[1])


def tool_verify(args):
    project = args["project_dir"]
    if not os.path.isdir(project):
        return _text("project_dir does not exist: %s" % project, True)
    commands = [args["command"]] if args.get("command") else detect.project_facts(project)["checks"]
    if not commands:
        return _text("No check command detected. Ask the user how this project is checked, or pass `command`.", True)
    results, failed = [], False
    for command in commands:
        argv = shlex.split(command, posix=os.name != "nt")
        if not allowed_check(argv):
            results.append("REFUSED `%s`: only check commands can run here (e.g. python -m pytest, node --test, "
                           "flutter analyze, npm test, cargo test)." % command)
            failed = True
            continue
        exe = _which(argv[0])
        try:
            proc = subprocess.run([exe] + argv[1:], cwd=project, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=VERIFY_TIMEOUT, stdin=subprocess.DEVNULL)
            output = (proc.stdout + proc.stderr).strip()
            results.append("$ %s\nexit code %d\n%s" % (command, proc.returncode, output[-3000:]))
            failed = failed or proc.returncode != 0
        except (OSError, subprocess.TimeoutExpired) as e:
            results.append("$ %s\nfailed to run: %s" % (command, e))
            failed = True
    verdict = "SOME CHECKS FAILED - the task is not done." if failed else "ALL CHECKS PASSED."
    return _text(verdict + "\n\n" + "\n\n".join(results), failed)


def _which(name):
    import shutil
    return shutil.which(name) or name


def tool_recall(args):
    query = args["query"].lower()
    words = [w for w in re.findall(r"\w+", query) if len(w) > 2]
    home = detect.tidos_home()
    hits = []
    for path in glob.glob(os.path.join(home, "playbooks", "**", "*.md"), recursive=True) + \
            glob.glob(os.path.join(home, "memory", "*.md")):
        rel = os.path.relpath(path, home).replace("\\", "/")
        if args.get("project") and args["project"].lower() not in rel.lower() and "_general" not in rel \
                and "memory/" not in rel:
            continue
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                low = line.lower()
                score = sum(w in low for w in words)
                if score and line.strip() and not line.startswith("---"):
                    hits.append((score, rel, line.strip()[:240]))
    hits.sort(key=lambda h: -h[0])
    if not hits:
        return _text("Nothing learned yet about '%s'." % args["query"])
    return _text("\n".join("[%s] %s" % (rel, line) for _, rel, line in hits[:15]))


def tool_note(args):
    from tidos_learn import distill
    path = distill.add_note(args["project"], args.get("stack") or "any", args["advice"], "mcp-note")
    return _text("Noted for weaker models: %s" % os.path.basename(os.path.dirname(path)))


def tool_propose(args):
    from tidos_learn import evolve
    item = evolve.add(args["title"], args["reason"], args.get("priority", "medium"))
    return _text("Proposal #%d recorded for the user's review (not applied)." % item["id"])


HANDLERS = {"tidos_start": tool_start, "tidos_guide": tool_guide, "tidos_verify": tool_verify,
            "tidos_recall": tool_recall, "tidos_note": tool_note, "tidos_propose": tool_propose}


def handle(message):
    """Return the JSON-RPC response for one message, or None for notifications."""
    method, msg_id = message.get("method"), message.get("id")
    if msg_id is None:
        return None  # notifications (initialized, cancelled...) need no answer
    try:
        if method == "initialize":
            asked = (message.get("params") or {}).get("protocolVersion")
            result = {"protocolVersion": asked if asked in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[-1],
                      "capabilities": {"tools": {}}, "serverInfo": SERVER_INFO,
                      "instructions": "TIDOS: call tidos_start once per session and follow the brief it returns."}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = message.get("params") or {}
            handler = HANDLERS.get(params.get("name"))
            if not handler:
                return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "unknown tool"}}
            try:
                result = handler(params.get("arguments") or {})
            except KeyError as e:
                result = _text("missing argument: %s" % e, True)
            except Exception as e:  # noqa: BLE001 - tool errors are reported to the model, never crash the server
                result = _text("TIDOS tool error: %s: %s" % (type(e).__name__, e), True)
        else:
            return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "method not found"}}
    except Exception as e:  # noqa: BLE001
        return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32603, "message": str(e)}}
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def serve(stdin=sys.stdin, stdout=sys.stdout):
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except ValueError:
            stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}) + "\n")
            stdout.flush()
            continue
        response = handle(message)
        if response is not None:
            stdout.write(json.dumps(response) + "\n")
            stdout.flush()
