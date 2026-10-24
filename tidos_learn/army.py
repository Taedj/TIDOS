"""Shadow Army: TIDOS's subagents grow from evidence, not from being called often.

Units    Claude Code subagents: TIDOS units (repo .claude/agents), your personal units (~/.claude/agents),
         drafts (~/.tidos/drafts/agents), and the tools' built-in agents (general-purpose, Explore, OpenCode's
         explore/general) so you can see where delegated work really goes.
Mission  one delegation recorded in the brain ("unit: description"). A mission earns the XP of the task it
         served, with the same evidence rules as tidos_learn.xp (outcome, checks, first try, corrections):
         rank = quality, not volume.
Lessons  private memory per unit (~/.tidos/army/<unit>.md): what its good missions verified with, what went
         wrong (failures, your corrections). TIDOS units read it before they start (one generic line in
         their prompt), so the reviewer gets better at YOUR projects without private data in the repo.
ARISE    a kind of work (stack) that keeps succeeding with strong models but no unit covers -> a draft
         specialist built from the general playbooks. Drafts become active only when the owner activates
         them (personal units go to ~/.claude/agents, never into the public repo).
Trial    tidos_evals run --unit NAME: the unit's instructions vs plain on dungeons; the result is shown at
         activation. Units that keep failing are proposed for rework in the evolution queue.
"""
import glob
import json
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone

from tidos_brain import privacy
from tidos_brain.claude_code import is_synthetic
from tidos_session.detect import REPO_ROOT, tidos_home

from . import distill, xp

# built-in agents of the tools, merged under one display name
NATIVE = {"general-purpose": "general-purpose", "general": "general-purpose", "explore": "explore",
          "plan": "plan", "fork": "fork", "statusline-setup": "statusline-setup", "claude-code-guide": "claude-code-guide"}
ARISE_MIN_VERIFIED = 12      # verified strong-model successes in one stack before a specialist is drafted
RETIRE_MIN_MISSIONS = 5
RETIRE_MAX_SUCCESS = 0.4
LESSON_LIMIT = 4000


def army_dir():
    return os.path.join(tidos_home(), "army")


def personal_agents_dir():
    return os.path.join(os.path.expanduser("~"), ".claude", "agents")


def _state_path():
    return os.path.join(tidos_home(), "army.json")


def load_state():
    try:
        with open(_state_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_state(data):
    os.makedirs(tidos_home(), exist_ok=True)
    with open(_state_path() + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(_state_path() + ".tmp", _state_path())


def _front(path):
    with open(path, "r", encoding="utf-8") as f:
        head = f.read(3000)
    m = re.match(r"^---\s*\n(.*?)\n---", head, re.S)
    return dict(re.findall(r"^(\w[\w-]*):\s*(.+)$", m.group(1), re.M)) if m else {}


def units():
    """{name: {name, state: active|draft, scope: tidos|personal|draft, path, description}} from the agent files."""
    out = {}
    sources = [(os.path.join(REPO_ROOT, ".claude", "agents"), "active", "tidos"),
               (personal_agents_dir(), "active", "personal"),
               (os.path.join(tidos_home(), "drafts", "agents"), "draft", "draft")]
    for folder, state, scope in sources:
        for path in sorted(glob.glob(os.path.join(folder, "*.md"))):
            front = _front(path)
            name = front.get("name", os.path.splitext(os.path.basename(path))[0]).strip()
            if name in out and out[name]["state"] == "active":
                continue  # an active unit wins over its draft
            out[name] = {"name": name, "state": state, "scope": scope, "path": path,
                         "description": front.get("description", "")[:200]}
    return out


def unit_name(summary):
    name = (summary or "").split(":", 1)[0].strip() if ":" in (summary or "") else "general-purpose"
    return NATIVE.get(name.lower(), name)


def missions(conn):
    """Every recorded delegation with the evidence of the task it served."""
    rows = conn.execute(
        "SELECT tc.summary, t.id task_id, t.session_id, t.seq, t.outcome, t.verify_passed, t.corrected, t.prompt, "
        "t.started_at, s.project, s.cwd FROM tool_calls tc JOIN tasks t ON t.id = tc.task_id "
        "JOIN sessions s ON s.id = t.session_id WHERE tc.kind = 'delegate' ORDER BY t.started_at").fetchall()
    rows = [dict(r) for r in rows if not is_synthetic(r["cwd"])]
    if not rows:
        return []
    ids = sorted({r["task_id"] for r in rows})
    checks = defaultdict(list)
    for i in range(0, len(ids), 500):
        chunk = ids[i:i + 500]
        for v in conn.execute("SELECT task_id, command, passed FROM verifications WHERE task_id IN (%s) ORDER BY id"
                              % ",".join("?" * len(chunk)), chunk):
            checks[v["task_id"]].append({"command": v["command"], "passed": v["passed"]})
    for r in rows:
        r["unit"] = unit_name(r["summary"])
        r["description"] = (r["summary"] or "").split(":", 1)[-1].strip()
        r["checks"] = checks[r["task_id"]]
        r["xp"] = xp.task_xp(r)[0]
    return rows


def compute(conn):
    """Army roster with level/rank from mission evidence. Units with no file but missions appear as 'native' or
    'external' (a project's own subagent)."""
    roster = {n: dict(u) for n, u in units().items()}
    by_unit = defaultdict(list)
    for m in missions(conn):
        by_unit[m["unit"]].append(m)
    for name in by_unit:
        if name not in roster:
            roster[name] = {"name": name, "state": "native" if name in NATIVE.values() else "external",
                            "scope": "native" if name in NATIVE.values() else "external", "path": None,
                            "description": ""}
    trials = load_state().get("trials", {})
    for name, u in roster.items():
        ms = by_unit.get(name, [])
        total = sum(m["xp"] for m in ms)
        level, floor_xp, next_xp = xp.level_for(max(0, total))
        decided = [m for m in ms if m["outcome"] in ("success", "failure")]
        u.update(missions=len(ms), xp=total, level=level, floor_xp=floor_xp, next_xp=next_xp,
                 rank=xp.rank_for(level) if ms else "-",
                 success=round(sum(m["outcome"] == "success" for m in decided) / len(decided), 2) if decided else None,
                 corrected=sum(1 for m in ms if m["corrected"]),
                 projects=[p for p, _ in Counter(m["project"] or "?" for m in ms).most_common(3)],
                 last=ms[-1]["started_at"] if ms else None, trial=trials.get(name),
                 has_lessons=os.path.isfile(os.path.join(army_dir(), "%s.md" % distill.slug(name))))
    order = {"active": 0, "draft": 1, "native": 2, "external": 3}
    return sorted(roster.values(), key=lambda u: (order.get(u["state"], 9), -u["xp"], u["name"]))


# --- lessons -----------------------------------------------------------------------------------------
def _correction(conn, m):
    row = conn.execute("SELECT prompt FROM tasks WHERE session_id = ? AND seq = ?", (m["session_id"], m["seq"] + 1)).fetchone()
    return privacy.clean(row["prompt"], 220) if row and row["prompt"] else None


def lessons_text(conn, name, ms):
    good = [m for m in ms if m["outcome"] == "success" and not m["corrected"]]
    bad = [m for m in ms if m["outcome"] == "failure" or m["corrected"]]
    verified = Counter()
    for m in good:
        for c in m["checks"]:
            if c["passed"]:
                cmd = distill.normalize_check(c["command"] or "")
                if cmd:
                    verified[cmd] += 1
    lines = ["# Lessons for %s (from %d missions in your projects)" % (name, len(ms)), "",
             "Learned by TIDOS from real delegations. Private: never copy this into a public repo.", ""]
    if verified:
        lines += ["## Good missions were verified with"] + ["- `%s` (%dx)" % (c, n) for c, n in verified.most_common(5)] + [""]
    if bad:
        lines.append("## Watch out (missions that failed or that the user corrected)")
        for m in bad[-6:]:
            fix = _correction(conn, m) if m["corrected"] else None
            lines.append("- [%s] %s: %s%s" % (m["project"] or "?", "corrected" if m["corrected"] else "failed",
                                              privacy.clean(m["description"], 120),
                                              " -> the user then said: \"%s\"" % fix if fix else ""))
        lines.append("")
    lines.append("## Recent missions")
    for m in ms[-8:]:
        lines.append("- [%s] %s (%s)" % (m["project"] or "?", privacy.clean(m["description"], 120), m["outcome"]))
    text = "\n".join(lines) + "\n"
    return text if len(text) <= LESSON_LIMIT else text[:LESSON_LIMIT - 40] + "\n...(older lessons trimmed)\n"


def write_lessons(conn):
    """~/.tidos/army/<unit>.md for every unit with missions. Returns the paths written."""
    by_unit = defaultdict(list)
    for m in missions(conn):
        by_unit[m["unit"]].append(m)
    os.makedirs(army_dir(), exist_ok=True)
    written = []
    for name, ms in by_unit.items():
        path = os.path.join(army_dir(), "%s.md" % distill.slug(name))
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(lessons_text(conn, name, ms))
        written.append(path)
    return written


def lessons(name):
    path = os.path.join(army_dir(), "%s.md" % distill.slug(name))
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# --- ARISE: new specialists for uncovered recurring work --------------------------------------------
def _covers(unit, stack):
    words = [w for w in re.split(r"[/\s-]+", stack.lower()) if len(w) > 2]
    text = (unit["name"] + " " + unit["description"]).lower()
    return any(w in text for w in words)


def arise(conn, tasks=None):
    """Draft a specialist for each stack with >= ARISE_MIN_VERIFIED verified strong successes that no active
    unit covers. Returns the draft paths created."""
    tasks = tasks if tasks is not None else distill.load_tasks(conn)
    counts = Counter()
    for t in tasks:
        if t["strong"] and t["verify_passed"] == 1 and distill.is_learning_example(t):
            for s in t["stacks"]:
                counts[s] += 1
    roster = units()
    active = [u for u in roster.values() if u["state"] == "active"]
    made = []
    for stack, n in counts.most_common():
        if n < ARISE_MIN_VERIFIED or any(_covers(u, stack) for u in active):
            continue
        name = "%s-specialist" % distill.slug(stack)
        target = os.path.join(tidos_home(), "drafts", "agents", "%s.md" % name)
        if name in roster or os.path.exists(target):
            continue
        sources = sorted(glob.glob(os.path.join(tidos_home(), "playbooks", "_general", "*--%s.md" % distill.slug(stack))))
        if not sources:
            continue
        knowledge = []
        for path in sources:
            with open(path, "r", encoding="utf-8") as f:
                body = re.sub(r"^---.*?---\s*", "", f.read(), flags=re.S)
            knowledge.append(re.split(r"\n## Example requests", body)[0].strip())
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write("---\nname: %s\ndescription: %s specialist across all your projects: how this kind of work is done, "
                    "verified and where it goes wrong (learned from %d verified strong-model tasks).\ntools: Read, Grep, "
                    "Glob, Bash, Edit, Write\nmodel: inherit\n---\n\nYou are the %s specialist. Read before you edit, "
                    "run the checks below after every change, and report the check output.\n\n%s\n\n"
                    "<!-- DRAFT by TIDOS (ARISE): review, then activate from /TIDOSZIT (Army) or copy to "
                    "~/.claude/agents/. -->\n" % (name, stack, n, stack, "\n\n".join(knowledge)[:6000]))
        made.append(target)
    return made


# --- rework proposals ---------------------------------------------------------------------------------
def retire_proposals(roster):
    """Active units whose missions mostly fail -> one proposal each in the evolution queue (no duplicates)."""
    from . import evolve
    existing = {p["title"] for p in evolve.load()}
    filed = []
    for u in roster:
        if u["state"] != "active" or u["missions"] < RETIRE_MIN_MISSIONS or u["success"] is None:
            continue
        if u["success"] <= RETIRE_MAX_SUCCESS:
            title = "Rework or retire subagent %s" % u["name"]
            if title in existing:
                continue
            filed.append(evolve.add(title, "Its %d missions succeeded only %d%% of the time (XP %d, %d corrected). "
                                           "Read ~/.tidos/army/%s.md, then sharpen its instructions or retire it." % (
                                               u["missions"], 100 * u["success"], u["xp"], u["corrected"],
                                               distill.slug(u["name"])), "medium"))
    return filed


def refresh(conn, tasks=None):
    """Run after distillation: lessons, ARISE drafts, rework proposals."""
    lessons_written = write_lessons(conn)
    drafts = arise(conn, tasks)
    roster = compute(conn)
    return {"lessons": lessons_written, "arise": drafts, "proposals": retire_proposals(roster), "roster": roster}


# --- activation (owner only: dashboard button or CLI) -------------------------------------------------
def activate(name):
    """Draft -> ~/.claude/agents/<name>.md (personal, every project). Never into the public repo."""
    u = units().get(name)
    if not u or u["state"] != "draft":
        raise ValueError("%s is not a draft" % name)
    target = os.path.join(personal_agents_dir(), "%s.md" % distill.slug(name))
    if os.path.exists(target):
        raise ValueError("%s already exists" % target)
    with open(u["path"], "r", encoding="utf-8") as f:
        text = "".join(line for line in f.readlines() if not line.startswith("<!-- DRAFT by TIDOS"))
    os.makedirs(personal_agents_dir(), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip() + "\n")
    data = load_state()
    data.setdefault("activated", {})[name] = {"path": target, "draft": u["path"],
                                              "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _save_state(data)
    return target


def deactivate(name):
    """Undo activate(): remove the personal unit TIDOS activated (the draft stays). Never touches other files."""
    data = load_state()
    rec = data.get("activated", {}).get(name)
    if not rec:
        raise ValueError("%s was not activated by TIDOS" % name)
    if os.path.isfile(rec["path"]) and os.path.dirname(os.path.abspath(rec["path"])) == os.path.abspath(personal_agents_dir()):
        if not os.path.exists(rec["draft"]):  # keep the knowledge: put it back as a draft
            os.makedirs(os.path.dirname(rec["draft"]), exist_ok=True)
            shutil.copy(rec["path"], rec["draft"])
        os.remove(rec["path"])
    del data["activated"][name]
    _save_state(data)
    return rec["path"]


def record_trial(name, agent, tasks, plain, with_unit):
    data = load_state()
    data.setdefault("trials", {})[name] = {"agent": agent, "tasks": tasks, "plain": round(plain), "unit": round(with_unit),
                                           "passed": with_unit >= plain,
                                           "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    _save_state(data)
    return data["trials"][name]


def unit_prompt(name):
    """The unit's instructions (frontmatter removed) for a dungeon trial."""
    u = units().get(name)
    if not u:
        raise KeyError(name)
    with open(u["path"], "r", encoding="utf-8") as f:
        text = f.read()
    return re.sub(r"^---.*?---\s*", "", text, flags=re.S).replace("<!-- DRAFT by TIDOS", "<!-- ").strip()
