"""Classify traced tasks: task type (from the request + what was done) and stack (from files/commands).

Requests are often short ("Phase 1", "go"), so when the words say nothing the actions decide:
edits -> feature, reads only -> question. English + French keywords.
"""
import os
import re

TYPE_RULES = [
    ("deploy", r"\bdeploy|\brelease\b|\bpublish|bump (the )?version|version bump|\baab\b|\bapk\b|play console|"
               r"\bhosting\b|store listing|d[ée]ploi"),
    ("bugfix", r"\bfix|\bbug|\berror|\bcrash|broken|not work|n'?t work|dont work|ne (marche|fonctionne) pas|"
               r"\berreur|\bissue\b|\bproblem|\bfail|empty screen|black screen|\bwrong\b|\bstuck\b"),
    # an explicit review/explain request is the intent, even when it mentions screens or buttons
    ("review", r"\breview|\bexplain|\banaly[sz]e|\baudit|what do you think|\bfeedback|\bopinion|\bcompare"),
    ("ui", r"\bscreens?\b|\bbutton|\blayout|\bui\b|\bux\b|\bdesign|\bicon|\btheme|dark mode|\bpage\b|\bwidget|"
           r"\b[ée]cran|\bbouton"),
    ("refactor", r"refactor|\brename|clean ?up|reorgani[sz]|simplif|restructur"),
    ("test", r"\btests?\b|coverage|\btesting\b"),
    ("docs", r"\breadme\b|\bdocs?\b|documentation|changelog|release notes?|\bplan\b"),
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


def task_type(prompt, calls):
    text = prompt or ""
    for name, pattern in _COMPILED:
        if pattern.search(text):
            return name
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
            if os.path.basename(summary).lower() in ("firebase.json", "firestore.rules", "firestore.indexes.json"):
                stack = "firebase"
            if stack and stack != "docs" and stack not in found:
                found.append(stack)
        elif c.get("kind") == "exec":
            low = summary.lower()
            for needle, stack in CMD_STACKS:
                if needle in low and stack not in found:
                    found.append(stack)
    return found or ["general"]
