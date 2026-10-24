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

from . import pbstate
from .detect import tidos_home

GUIDE_LIMIT = 4096
PLAYBOOK_LIMIT = 1000
SESSION_CLI = os.path.join(os.path.dirname(os.path.abspath(__file__)), "__main__.py")
LEARN_CLI = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tidos_learn", "__main__.py")

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


def _front(text, key):
    m = re.search(r"^%s:\s*(.+)$" % key, text, re.M)
    return m.group(1).strip() if m else ""


def _compact(text):
    """Playbook body for the brief: no front matter, no example requests (they cost bytes, teach little)."""
    body = re.sub(r"^---.*?---\s*", "", text, flags=re.S)
    body = re.split(r"\n## Example requests", body)[0]
    return body.strip()


def _playbooks(stack, project=None, limit=3, with_paths=False):
    """Playbooks learned from earlier sessions: this project's first, then same-stack general ones."""
    found = []
    wanted = {s.lower() for s in stack}
    for path in sorted(glob.glob(os.path.join(tidos_home(), "playbooks", "**", "*.md"), recursive=True)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except OSError:
            continue
        if pbstate.is_disabled(path):
            continue  # turned off by the user in /TIDOSZIT
        tags = {t.strip().lower() for t in _front(text, "stack").split(",") if t.strip()}
        same_project = bool(project) and _front(text, "project").lower() == project.lower()
        overlap = len(tags & wanted)
        if not (same_project or overlap or "any" in tags):
            continue
        kind = _front(text, "type")
        try:
            confidence = float(_front(text, "confidence") or 0.5)
        except ValueError:
            confidence = 0.5
        score = (3 if same_project else 0) + overlap + confidence + (2 if kind == "notes" and same_project else 0) \
            + (0.5 if kind in ("bugfix", "feature") else 0)
        name = "%s / %s" % (_front(text, "project") or "any", kind or os.path.basename(path)[:-3])
        found.append((score, name, _compact(text), path))
    found.sort(key=lambda x: -x[0])
    return found[:limit] if with_paths else [f[:3] for f in found[:limit]]


def _cap(text, limit):
    """Shorten to whole lines (a half line confuses weak models more than a missing one)."""
    if len(text) <= limit:
        return text
    head = text[: limit - 10]
    head = head.rsplit("\n", 1)[0] if "\n" in head else head
    return head.rstrip() + "\n...[more]"


def _user_rules(project, limit=4):
    """Standing directives the user repeated (learned by tidos_learn.prefs), this project's first."""
    path = os.path.join(tidos_home(), "memory", "LEARNED_PREFERENCES.md")
    try:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
    except OSError:
        return []
    sections = dict(re.findall(r"^## (.+?)\n(.*?)(?=^## |\Z)", text, re.M | re.S))
    rules, seen = [], []
    for name in (project, "All projects"):
        for line in sections.get(name, "").splitlines():
            if not line.startswith("- "):
                continue
            rule = re.sub(r"\s*_\(x\d+\)_$", "", line[2:].strip())[:150]
            words = {w for w in re.findall(r"[a-z0-9]+", rule.lower()) if len(w) > 3}
            # skip near-duplicates ("modify trading behavior" / "change trading behavior")
            if words and all(len(words & s) / len(words | s) < 0.5 for s in seen):
                rules.append(rule)
                seen.append(words)
    return rules[:limit]


def guide_brief(session, facts, record=True):
    rules = _user_rules(facts["name"])
    user_rules = ("## The user's standing rules (they repeated these; apply when relevant)\n%s\n\n"
                  % "\n".join("- " + r for r in rules)) if rules else ""
    checks = "\n".join("- `%s`" % c for c in facts["checks"]) or \
        "- No test command detected: ask the user how they check this project, or write a small check script."
    notes = "".join("- %s\n" % n for n in facts["notes"])
    selected = _playbooks(facts["stack"], facts["name"], limit=2, with_paths=True)
    if selected and record:
        pbstate.record_served([p for *_, p in selected])
    playbooks = [s[:3] for s in selected]
    if playbooks:
        pb_text = "\n\n".join("### %s\n%s" % (name, _cap(body, PLAYBOOK_LIMIT))
                              for _, name, body in playbooks).replace("\n# ", "\n#### ")
    else:
        pb_text = "None yet for this stack. (They are learned from sessions run on a strong model.)"
    if session.get("tool") == "claude-code":
        per_request = ""  # the UserPromptSubmit hook injects per-request guidance automatically
    else:
        per_request = ("## For EVERY new request from the user\nFirst run `python -I \"%s\" guide \"<the request in a "
                       "few words>\"` and follow what it prints.\n\n" % SESSION_CLI)
    text = (
        "# TIDOS GUIDE MODE\n"
        "You are running on `%s` (tier: %s). TIDOS will guide you so you can work well with the user.\n\n"
        "## Rules (follow them exactly)\n%s\n\n%s"
        "## Project: %s\n- Stack: %s\n%s\n"
        "## How to check work\n%s\n\n%s"
        "## Playbooks learned from strong models\n%s\n"
        % (session["model"], session["tier"], WEAK_RULES, per_request, facts["name"], ", ".join(facts["stack"]),
           notes, checks, user_rules, pb_text))
    lines = text.split("\n")
    while len("\n".join(lines).encode("utf-8")) > GUIDE_LIMIT - 12 and len(lines) > 3:
        lines.pop()  # playbooks are the only variable-size part; drop whole lines
    if len(lines) < len(text.split("\n")):
        text = "\n".join(lines).rstrip() + "\n...[more]\n"
    return text


def learn_brief(session, facts):
    return (
        "# TIDOS LEARN MODE\n"
        "You are running on `%s` (tier: frontier). Work at your normal level with the user.\n"
        "TIDOS records this session (tool calls, checks, corrections) into its local brain, outside the\n"
        "repository, so it can later teach weaker models how tasks are solved in this project.\n"
        "Help TIDOS learn: run the project's real checks before calling a task done.\n\n"
        "When you finish a significant task, leave ONE short piece of advice for weaker models working on\n"
        "this project later (where things live, the trap you avoided, how to verify), by running:\n"
        "  python -I \"%s\" note --project \"%s\" --stack \"%s\" \"<advice>\"\n\n"
        "Project: %s - stack: %s - checks: %s\n"
        % (session["model"], LEARN_CLI, facts["name"], ", ".join(facts["stack"]),
           facts["name"], ", ".join(facts["stack"]), ", ".join(facts["checks"]) or "none detected"))
