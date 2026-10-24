"""TIDOS XP engine ("Solo Leveling"): growth measured by evidence, never by volume of text.

Per task (domain = the project, after sub-repo attribution):
  outcome success +20, unknown +5, failure -10
  last check passed +5, FIRST check already passed +5 (got it right first time)
  corrected by the user -10
Level n needs 100 * (n-1)^1.5 XP. Ranks: E 1-4, D 5-9, C 10-19, B 20-34, A 35-49, S 50+.

Growth unlocks (drafts only - never activated without the user):
  skill drafts  a playbook with >= SKILL_MIN_VERIFIED verified successes and rank B+ -> draft SKILL.md
  job change    a domain reaching JOB_LEVEL -> draft a project-specialist subagent from its playbooks
Drafts live in ~/.tidos/drafts/ (private).
"""
import glob
import os
import re
from collections import defaultdict
from datetime import datetime, timezone

from tidos_session.detect import tidos_home

from . import distill

RANKS = [(50, "S"), (35, "A"), (20, "B"), (10, "C"), (5, "D"), (1, "E")]
OUTCOME_XP = {"success": 20, "unknown": 5, "failure": -10}
SKILL_MIN_VERIFIED = 10
JOB_LEVEL = 15


def task_xp(task):
    """(delta, reason) for one task dict/row with outcome, verify_passed, corrected (+ optional checks list)."""
    delta, reasons = OUTCOME_XP.get(task["outcome"], 0), [task["outcome"]]
    if task["verify_passed"] == 1:
        delta += 5
        reasons.append("check passed")
    checks = task.get("checks") if isinstance(task, dict) else None
    if checks and checks[0]["passed"]:
        delta += 5
        reasons.append("first try")
    if task["corrected"]:
        delta -= 10
        reasons.append("corrected")
    return delta, ", ".join(reasons)


def level_for(xp):
    level = 1
    while 100 * level ** 1.5 <= xp:
        level += 1
    return level, int(100 * (level - 1) ** 1.5), int(100 * level ** 1.5)


def rank_for(level):
    return next(r for threshold, r in RANKS if level >= threshold)


def compute(conn):
    """Recompute xp_events from all traced tasks. Returns per-domain and global summaries."""
    tasks = distill.load_tasks(conn)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    events = []
    for t in tasks:
        delta, reason = task_xp(t)
        events.append((t["started_at"] or now, t["project"], delta, reason, t["id"]))
    with conn:
        conn.execute("DELETE FROM xp_events")
        conn.executemany("INSERT INTO xp_events (ts, domain, delta, reason, task_id) VALUES (?,?,?,?,?)", events)
    domains, counts = defaultdict(int), defaultdict(lambda: [0, 0])
    for (_, domain, delta, _, _), t in zip(events, tasks):
        domains[domain] += delta
        counts[domain][0] += 1
        counts[domain][1] += t["outcome"] == "success"
    summary = {}
    for domain, xp in domains.items():
        level = level_for(max(0, xp))[0]
        summary[domain] = {"xp": max(0, xp), "level": level, "rank": rank_for(level),
                           "tasks": counts[domain][0], "success": counts[domain][1]}
    total = max(0, sum(domains.values()))
    level, floor_xp, next_xp = level_for(total)
    return {"xp": total, "level": level, "rank": rank_for(level), "floor_xp": floor_xp, "next_xp": next_xp,
            "domains": summary}


def drafts_dir(kind):
    return os.path.join(tidos_home(), "drafts", kind)


def draft_skills(conn):
    """Proven playbooks become SKILL.md drafts (private) for the user to review and promote."""
    made = []
    for row in conn.execute("SELECT * FROM playbooks WHERE status = 'generated'"):
        if row["successes"] < SKILL_MIN_VERIFIED or row["rank"] not in ("B", "A", "S") or not os.path.isfile(row["path"]):
            continue
        with open(row["path"], "r", encoding="utf-8") as f:
            text = f.read()
        project = re.search(r"^project:\s*(.+)$", text, re.M).group(1).strip()
        name = "%s-%s" % (distill.slug(project if project != "any" else row["stack"]), row["task_type"])
        target = os.path.join(drafts_dir("skills"), name, "SKILL.md")
        if os.path.exists(target):
            continue
        body = re.sub(r"^---.*?---\s*", "", text, flags=re.S).strip()
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write("---\nname: %s\ndescription: How %s tasks are done in %s (learned from %d verified successes). "
                    "Use for %s work on %s.\n---\n\n%s\n\n<!-- DRAFT by TIDOS %s: review, generalize, then move to "
                    ".claude/skills/ to activate. -->\n" % (name, row["task_type"], project, row["successes"],
                                                            row["task_type"], project, body,
                                                            datetime.now(timezone.utc).date().isoformat()))
        made.append(target)
    return made


def job_change(summary):
    """A domain that reached JOB_LEVEL earns a draft specialist subagent built from its playbooks."""
    made = []
    for domain, info in summary["domains"].items():
        if info["level"] < JOB_LEVEL or domain in ("~", "?"):
            continue
        target = os.path.join(drafts_dir("agents"), "%s-specialist.md" % distill.slug(domain))
        if os.path.exists(target):
            continue
        sources = sorted(glob.glob(os.path.join(tidos_home(), "playbooks", distill.slug(domain), "*.md")))
        knowledge = []
        for path in sources:
            with open(path, "r", encoding="utf-8") as f:
                body = re.sub(r"^---.*?---\s*", "", f.read(), flags=re.S)
            knowledge.append(re.split(r"\n## Example requests", body)[0].strip())
        from tidos_session.brief import _user_rules  # the user's standing rules bind the specialist first
        rules = _user_rules(domain, limit=8)
        if rules:
            knowledge.insert(0, "## The user's standing rules (they repeated these: obey them unless the user explicitly asks otherwise in the current request)\n" + "\n".join("- " + r for r in rules))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8", newline="\n") as f:
            f.write("---\nname: %s-specialist\ndescription: Specialist for the %s project (level %d, rank %s in TIDOS). "
                    "Knows where its code lives, how it is verified and its pitfalls.\ntools: Read, Grep, Glob, Bash, "
                    "Edit, Write\nmodel: inherit\n---\n\nYou are the %s specialist. Use this project knowledge, learned "
                    "from verified sessions:\n\n%s\n\n<!-- DRAFT by TIDOS (job change at level %d): review, then copy to "
                    "the project's .claude/agents/ to activate. -->\n"
                    % (distill.slug(domain), domain, info["level"], info["rank"], domain,
                       "\n\n".join(knowledge)[:6000], info["level"]))
        made.append(target)
    return made


def level_up(conn):
    """Run after distillation: XP, then growth drafts. Returns (summary, skill drafts, agent drafts)."""
    summary = compute(conn)
    return summary, draft_skills(conn), job_change(summary)
