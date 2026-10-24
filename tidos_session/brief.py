"""The text TIDOS gives the model at START TIDOS.

GUIDE mode (medium/weak models): a compact brief, hard-capped at 4 KB. The v4 boot (~86 KB of specs)
did not help even a small Claude model in evals (+55% cost, no gain), so weak models get only what
they can use: rules, project facts, how to check work, and the playbooks that match this project.

LEARN mode (frontier models): short. The strong model works normally; TIDOS records the session so
it can later turn it into playbooks for weaker models.
"""
import glob
import os
import re

from .detect import tidos_home

GUIDE_LIMIT = 4096
PLAYBOOK_LIMIT = 1200

WEAK_RULES = """\
1. Work in SMALL steps: one file, one change at a time. Never rewrite whole files.
2. Read before you edit: open the file and the code around the change first. Never guess a path,
   function name or API - check it. Use paths relative to the project folder.
3. Before changing behavior, find or write the check that proves it (an existing test, or a small
   script with the exact expected values from the user's request).
4. After EVERY change, run the project's checks (see "How to check work"). Read the exact error
   and fix that one thing. Never edit or delete tests to make them pass.
5. Never say "done" without showing the check output that proves it.
6. If the request is unclear, or touches deploys, data, money, credentials or deletions: ASK the user first.
7. If the same error comes back 3 times, STOP. Tell the user what you tried and suggest switching to
   a stronger model for this step."""


def _playbooks(stack, limit=2):
    """Playbooks learned from strong-model sessions whose `stack:` matches this project."""
    found = []
    for path in sorted(glob.glob(os.path.join(tidos_home(), "playbooks", "**", "*.md"), recursive=True)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        m = re.search(r"^stack:\s*(.+)$", text, re.M)
        tags = {t.strip().lower() for t in (m.group(1).split(",") if m else [])}
        score = len(tags & {s.lower() for s in stack}) + (0.5 if "any" in tags else 0)
        if score:
            body = re.sub(r"^---.*?---\s*", "", text, flags=re.S).strip()
            found.append((score, os.path.splitext(os.path.basename(path))[0], body))
    found.sort(key=lambda x: -x[0])
    return found[:limit]


def _cap(text, limit):
    return text if len(text) <= limit else text[: limit - 20].rstrip() + "\n...[cut]"


def guide_brief(session, facts):
    checks = "\n".join("- `%s`" % c for c in facts["checks"]) or \
        "- No test command detected: ask the user how they check this project, or write a small check script."
    notes = "".join("- %s\n" % n for n in facts["notes"])
    playbooks = _playbooks(facts["stack"])
    if playbooks:
        pb_text = "\n\n".join("### %s\n%s" % (name, _cap(body, PLAYBOOK_LIMIT)) for _, name, body in playbooks)
    else:
        pb_text = "None yet for this stack. (They are learned from sessions run on a strong model.)"
    text = (
        "# TIDOS GUIDE MODE\n"
        "You are running on `%s` (tier: %s). TIDOS will guide you so you can work well with the user.\n\n"
        "## Rules (follow them exactly)\n%s\n\n"
        "## Project: %s\n- Stack: %s\n%s\n"
        "## How to check work\n%s\n\n"
        "## Playbooks learned from strong models\n%s\n"
        % (session["model"], session["tier"], WEAK_RULES, facts["name"], ", ".join(facts["stack"]), notes,
           checks, pb_text))
    if len(text.encode("utf-8")) > GUIDE_LIMIT:  # playbooks are the only variable-size part
        text = text.encode("utf-8")[:GUIDE_LIMIT - 12].decode("utf-8", "ignore").rstrip() + "\n...[cut]\n"
    return text


def learn_brief(session, facts):
    return (
        "# TIDOS LEARN MODE\n"
        "You are running on `%s` (tier: frontier). Work at your normal level with the user.\n"
        "TIDOS records this session (tool calls, checks, corrections) into its local brain, outside the\n"
        "repository, so it can later teach weaker models how tasks are solved in this project.\n"
        "Help TIDOS learn: run the project's real checks before calling a task done, and say briefly\n"
        "which files you read first and why.\n\n"
        "Project: %s - stack: %s - checks: %s\n"
        % (session["model"], facts["name"], ", ".join(facts["stack"]), ", ".join(facts["checks"]) or "none detected"))
