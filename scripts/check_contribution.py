"""Community contribution gate for skills, subagents and personas (run in CI on every pull request).

  python scripts/check_contribution.py [PATH ...]     default: every public skill/agent/persona + AGENTS.md

A contribution is rejected when it:
  - would be changed by the TIDOS privacy firewall (secrets, user paths, e-mails, IPs, local usernames)
  - is an unreviewed TIDOS draft (learned from someone's private traces) or quotes private learned data
  - has a SKILL.md / agent without name + description frontmatter, a name that does not match its folder,
    or is too large to be useful context (> MAX_BYTES)
Quality (does it raise eval scores?) is measured separately with the dungeons:
  python -I tidos_evals/__main__.py run --agent <agent> --tidos guide   (before vs after the change)
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import sanitizer  # noqa: E402

MAX_BYTES = 16000          # skills and subagents are loaded into context: keep them small
MAX_PERSONA_BYTES = 40000  # personas are full specs
DEFAULT = [".claude/skills/*/SKILL.md", ".claude/agents/*.md", "personas/*.md", "AGENTS.md"]
PRIVATE_MARKERS = [
    (re.compile(r"DRAFT by TIDOS"), "unreviewed TIDOS draft: generalize it and remove the DRAFT line"),
    (re.compile(r"learned from \d+ (verified|successful) (tasks|successes|sessions)", re.I),
     "quotes private learned data (task counts from someone's traces)"),
    (re.compile(r"standing rules \(they repeated these", re.I), "contains a user's private standing rules"),
]


def frontmatter(text):
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    return dict(re.findall(r"^(\w[\w-]*):\s*(.+)$", m.group(1), re.M)) if m else None


def check(path):
    problems = []
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if sanitizer.sanitize_text(text) != text:
        problems.append("privacy firewall would redact something (secret, user path, e-mail, IP or username)")
    for pattern, why in PRIVATE_MARKERS:
        if pattern.search(text):
            problems.append(why)
    rel = os.path.abspath(path).replace("\\", "/")
    is_skill, is_agent = rel.endswith("/SKILL.md"), "/agents/" in rel
    limit = MAX_BYTES if (is_skill or is_agent) else MAX_PERSONA_BYTES
    if len(text.encode("utf-8")) > limit:
        problems.append("too large (%d bytes > %d): keep it short and focused" % (len(text.encode()), limit))
    if is_skill or is_agent:
        front = frontmatter(text)
        if not front or not front.get("name") or not front.get("description"):
            problems.append("missing name/description frontmatter")
        else:
            expected = os.path.basename(os.path.dirname(path)) if is_skill \
                else os.path.splitext(os.path.basename(path))[0]
            if front["name"].strip() != expected:
                problems.append("name %r does not match %r" % (front["name"].strip(), expected))
    return problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    paths = argv or sorted(p for pattern in DEFAULT for p in glob.glob(os.path.join(ROOT, pattern)))
    bad = 0
    for path in paths:
        if not os.path.isfile(path):
            continue
        for problem in check(path):
            bad += 1
            print("%s: %s" % (os.path.basename(os.path.dirname(path)) + "/" + os.path.basename(path), problem))
    print("%d file(s) checked, %d problem(s)" % (len(paths), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
