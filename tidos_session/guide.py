"""GUIDE mode, just in time: for ONE user request, return only the guidance that matches it.

  python -I tidos_session/__main__.py guide "<the user's request>" [--project DIR]

Classifies the request (bugfix, feature, deploy, ui, ...), then returns, within ~1.5 KB:
  1. a checks-first step for that kind of task (define "done" before editing)
  2. this project's playbook for that task type (else the general one for the stack)
  3. this project's notes written by strong models
Weak models drown in long context, so nothing else is included.
"""
import glob
import os
import re

from . import brief, detect, pbstate

GUIDE_LIMIT = 1600

CHECKS_FIRST = {
    "bugfix": "Reproduce first: find or write a check that FAILS because of this bug (test, script, or exact "
              "steps + expected result). Fix the cause, then show the same check passing.",
    "feature": "Write down what 'done' means as checks (expected inputs/outputs or behavior) BEFORE coding; "
               "implement in small steps; run the checks after each step.",
    "deploy": "Deploys, releases and version bumps need the user's explicit OK for the exact command. Run the "
              "project checks/build first, show the output, then ask before deploying.",
    "ui": "Name the exact screen/widget file first. After the change run the analyzer/build, and tell the user "
          "exactly what they should see so they can confirm it.",
    "refactor": "Run the checks BEFORE and AFTER: behavior must not change. Keep public names and signatures.",
    "test": "A new test must fail without the fix (or for the missing behavior) and pass with it. Never weaken a test.",
    "review": "Do not modify code unless the user asks. Cite the exact files and lines for every finding.",
    "question": "Answer from the actual code: open the files and cite them. Do not change anything.",
    "docs": "Keep docs consistent with the code: check every command and path you write.",
}


def _project_playbook(project, ttype, stack):
    """Best playbook for this request: project+type, then general type+stack. Disabled ones are skipped."""
    base = pbstate.playbooks_dir()
    candidates = [os.path.join(base, re.sub(r"[^a-z0-9]+", "-", project.lower()).strip("-"), "%s.md" % ttype)]
    for s in stack:
        candidates.append(os.path.join(base, "_general", "%s--%s.md" % (ttype, re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-"))))
    for path in candidates:
        if os.path.isfile(path) and not pbstate.is_disabled(path):
            with open(path, "r", encoding="utf-8") as f:
                return path, brief._compact(f.read())
    return None, None


def _project_notes(project, limit=4):
    path = os.path.join(pbstate.playbooks_dir(), re.sub(r"[^a-z0-9]+", "-", project.lower()).strip("-"), "notes.md")
    if not os.path.isfile(path) or pbstate.is_disabled(path):
        return None, []
    with open(path, "r", encoding="utf-8") as f:
        lines = [l for l in f.read().splitlines() if l.startswith("- ")]
    return path, [re.sub(r"^- \([^)]*\)\s*", "- ", l) for l in lines[-limit:]]


STUCK_REPEAT = 3
STUCK_MESSAGE = ("TIDOS: the same check failed %d times in a row (`%s`). STOP changing code. Tell the user what you "
                 "tried and the exact error, and suggest switching to a stronger model for this step.")


EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
GROUND_MESSAGE = ("TIDOS: read the file(s) you are about to change first (and search for related code). "
                  "Never edit from memory or guesswork.")
VERIFY_MESSAGE = ("TIDOS: you changed code but no check has passed since your last edit. Run the project's checks "
                  "now and show the output. If no check exists or it cannot run, say clearly that the change is "
                  "UNVERIFIED and tell the user how to check it.")


def _kind(tool):
    from tidos_brain import scoring
    return scoring.tool_kind(tool or "")


def _is_check(summary):
    from tidos_brain import scoring
    return scoring.is_verify_command(summary)


def _since_last_prompt(conn, session_id):
    """Live events of this session since the user's last request."""
    last = conn.execute("SELECT MAX(id) FROM live_events WHERE session_id = ? AND event = 'UserPromptSubmit'",
                        (session_id,)).fetchone()[0] or 0
    return conn.execute("SELECT id, event, tool, summary, is_error FROM live_events WHERE session_id = ? AND id > ? "
                        "ORDER BY id", (session_id, last)).fetchall()


def _active_guide_session(cwd):
    """The current START TIDOS session if it is in GUIDE mode and this hook comes from its project."""
    import json
    try:
        with open(os.path.join(detect.tidos_home(), "session.json"), "r", encoding="utf-8") as f:
            session = json.load(f)
    except (OSError, ValueError):
        return None
    if session.get("mode") != "guide" or not cwd:
        return None
    project = os.path.normcase(os.path.normpath(session.get("project", "")))
    here = os.path.normcase(os.path.normpath(cwd))
    return session if here == project or here.startswith(project + os.sep) else None


def hook_feedback(payload, conn):
    """Claude Code hook in GUIDE mode. Returns (stdout, stderr, exit_code).

    UserPromptSubmit -> stdout = guidance for that request (Claude Code adds it to the model's context)
    PostToolUse      -> exit 2 + stderr when the same check failed STUCK_REPEAT times in a row
    """
    session = _active_guide_session(payload.get("cwd"))
    if not session:
        return "", "", 0
    event = payload.get("hook_event_name")
    if event == "UserPromptSubmit" and payload.get("prompt"):
        return guidance(payload["prompt"], session["project"])[1], "", 0
    if event == "PreToolUse" and payload.get("tool_name") in EDIT_TOOLS:
        recent = _since_last_prompt(conn, payload.get("session_id"))
        if not any(r["event"] == "PostToolUse" and _kind(r["tool"]) in ("read", "search") for r in recent):
            return "", GROUND_MESSAGE, 2
    if event == "Stop" and not payload.get("stop_hook_active"):
        recent = _since_last_prompt(conn, payload.get("session_id"))
        edits = [r["id"] for r in recent if r["event"] == "PostToolUse" and _kind(r["tool"]) == "edit"]
        if edits:
            passed = [r for r in recent if r["id"] > edits[-1] and r["event"] == "PostToolUse"
                      and _kind(r["tool"]) == "exec" and _is_check(r["summary"]) and not r["is_error"]]
            if not passed:
                return "", VERIFY_MESSAGE, 2
    if event == "PostToolUse":
        rows = conn.execute("SELECT tool, summary, is_error FROM live_events WHERE session_id = ? AND event = "
                            "'PostToolUse' ORDER BY id DESC LIMIT ?", (payload.get("session_id"), STUCK_REPEAT)).fetchall()
        if len(rows) == STUCK_REPEAT and all(r["is_error"] for r in rows) \
                and len({(r["tool"], r["summary"]) for r in rows}) == 1:
            return "", STUCK_MESSAGE % (STUCK_REPEAT, rows[0]["summary"] or rows[0]["tool"]), 2
    return "", "", 0


def guidance(request, project_dir=".", record=True):
    from tidos_learn.classify import task_type  # local import: classification lives with the learner
    from . import effort  # local import: effort can swap in for other classifiers (kept out of hot paths)

    facts = detect.project_facts(os.path.abspath(project_dir))
    ttype = task_type(request)
    level = effort.classify(request)
    if level == "fast":
        text = ("# TIDOS guide for this request (type: %s, effort: fast)\n"
                "Trivial: do it directly, no playbook needed. Still show the exact check (even one line) that "
                "proves the result." % ttype)
        if facts["checks"]:
            text += "\n\n## Checks for this project\n" + ", ".join("`%s`" % c for c in facts["checks"])
        return ttype, text + "\n"
    parts = ["# TIDOS guide for this request (type: %s, effort: %s)" % (ttype, level)]
    if level == "deep":
        parts.append("Complex task: show a short plan first, then one file / one change per step.")
    parts.append("## First: define done\n" + CHECKS_FIRST.get(ttype, CHECKS_FIRST["feature"]))
    served = []
    pb_path, pb = _project_playbook(facts["name"], ttype, facts["stack"])
    if pb:
        served.append(pb_path)
        parts.append("## How this kind of task was solved before\n" + brief._cap(
            re.split(r"\n## Pitfalls", pb)[0].replace("\n# ", "\n### "), 700))
        pitfalls = re.search(r"\n## Pitfalls\n(.*?)(\n## |\Z)", pb, re.S)
        if pitfalls:
            parts.append("## Pitfalls\n" + brief._cap(pitfalls.group(1).strip(), 300))
    notes_path, notes = _project_notes(facts["name"])
    if notes:
        served.append(notes_path)
        parts.append("## Notes from strong models on %s\n%s" % (facts["name"], "\n".join(notes)))
    if facts["checks"]:
        parts.append("## Checks for this project\n" + ", ".join("`%s`" % c for c in facts["checks"]))
    text = "\n\n".join(parts) + "\n"
    lines = text.split("\n")
    while len("\n".join(lines).encode("utf-8")) > GUIDE_LIMIT - 12 and len(lines) > 3:
        lines.pop()  # drop whole trailing lines, never half a line
    if len(lines) < len(text.split("\n")):
        text = "\n".join(lines).rstrip() + "\n...[more]\n"
    if served and record:
        pbstate.record_served(served)
    return ttype, text
