"""Classify traced tasks: task type (from the request + what was done) and stack (from files/commands).

Requests are often short ("Phase 1", "go"), so when the words say nothing the actions decide:
edits -> feature, reads only -> question. English + French keywords.
"""
import os
import re

from tidos_brain.paths import leaf

TYPE_RULES = [
    # "release" alone is not a deploy ("pre-release identifiers" is a coding spec): only release ACTIONS count
    ("deploy", r"\bdeploy|\bpublish|(?<!-)\brelease (the |a |new )?(app|apk|aab|build|version)|"
               r"\bmake a release|bump (the )?version|version bump|\baab\b|\bapk\b|play console|"
               r"\bhosting\b|store listing|d[ée]ploi"),
    ("bugfix", r"\bfix|\bbug|\berror|\bcrash|broken|not work|n'?t work|dont work|ne (marche|fonctionne) pas|"
               r"\berreur|\bissue\b|\bproblem|\bfail|empty screen|black screen|\bwrong\b|\bstuck\b"),
    # an explicit review/explain request is the intent, even when it mentions screens or buttons
    ("review", r"\breview|\bexplain|\banaly[sz]e|\baudit|what do you think|\bfeedback|\bopinion"),
    ("ui", r"\bscreens?\b|\bbutton|\blayout|\bui\b|\bux\b|\bdesign|\bicon|\btheme|dark mode|\bpage\b|\bwidget|"
           r"\b[ée]cran|\bbouton"),
    ("refactor", r"refactor|\brename|clean ?up|reorgani[sz]|simplif|restructur"),
    ("test", r"\b(write|add|more|missing|unit|integration) tests?\b|test coverage|\bcoverage\b"),
    ("docs", r"\breadme\b|\bdocumentation|changelog|release notes?|\bupdate the docs\b"),
    ("feature", r"\badd\b|\bimplement|\bcreate|\bbuild\b|\bmake\b|\bnew\b|\bajout|\bfeature|\bsupport|\boption|"
                r"\benable|\ballow"),
]
_COMPILED = [(name, re.compile(pattern, re.IGNORECASE)) for name, pattern in TYPE_RULES]

EXT_STACKS = {
    ".dart": "flutter/dart", ".py": "python", ".js": "node/javascript", ".ts": "node/javascript",
    ".jsx": "node/javascript", ".tsx": "node/javascript", ".ps1": "powershell", ".sql": "sql",
    ".kt": "android", ".gradle": "android", ".rules": "firebase", ".md": "docs", ".html": "web", ".css": "web",
}
CMD_STACKS = [("flutter", "flutter/dart"), ("dart ", "flutter/dart"), ("firebase", "firebase"), ("npm ", "node/javascript"),
              ("node ", "node/javascript"), ("pytest", "python"), ("python", "python"), ("gradlew", "android"),
              ("powershell", "powershell")]


# The opening verb states the intent best ("Implement X ... raise ValueError" is a feature, not a bugfix)
OPENING_VERBS = [
    ("deploy", r"(deploy|publish|ship)\b"),
    ("bugfix", r"(fix|repair|debug|resolve)\b"),
    ("review", r"(review|explain|analy[sz]e|audit|investigate)\b"),
    ("refactor", r"(refactor|rename|reorgani[sz]e|clean ?up|simplify|replace)\b"),
    ("test", r"(write|add) (unit |integration )?tests?\b"),
    ("feature", r"(implement|add|create|build|write|make|support|allow|enable|generate|ajoute)\b"),
]
_OPENING = [(name, re.compile(r"^\W*(?:(?:can|could|would|will) you\s+)?(?:please\s+|now\s+|then\s+)?" + p,
                              re.IGNORECASE)) for name, p in OPENING_VERBS]
_QUESTION = re.compile(r"^\W*(what|why|how|where|which|when|who|can|could|does|do|is|are|should)\b|\?\s*$", re.IGNORECASE)


def task_type(prompt, calls=None):
    """calls=None means a raw request (GUIDE mode, before any work): no actions to look at."""
    text = (prompt or "").strip()
    first = re.split(r"(?<=[.!?:])\s|\n", text, maxsplit=1)[0]
    for name, pattern in _OPENING:
        if pattern.search(first):
            return name
    bug = dict(_COMPILED)["bugfix"]
    if calls is None and _QUESTION.search(first) and not bug.search(text):
        return "question"  # "why does X load slowly?" asks for an answer; "why does X crash?" is a bug
    for name, pattern in _COMPILED:
        if pattern.search(text):
            return name
    if calls is None:
        return "question" if _QUESTION.search(first) else "feature"
    commands = " ".join((c.get("summary") or "") for c in calls if c.get("kind") == "exec").lower()
    if "deploy" in commands:
        return "deploy"
    if any(c.get("kind") == "edit" for c in calls):
        return "feature"
    return "question"


def stacks(calls):
    found = []
    for c in calls:
        summary = (c.get("summary") or "")
        if c.get("kind") in ("edit", "read"):
            stack = EXT_STACKS.get(os.path.splitext(summary.split()[0] if summary else "")[1].lower())
            if leaf(summary).lower() in ("firebase.json", "firestore.rules", "firestore.indexes.json"):
                stack = "firebase"
            if stack and stack != "docs" and stack not in found:
                found.append(stack)
        elif c.get("kind") == "exec":
            low = summary.lower()
            for needle, stack in CMD_STACKS:
                if needle in low and stack not in found:
                    found.append(stack)
    return found or ["general"]
