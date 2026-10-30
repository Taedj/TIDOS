"""Diagnose: TIDOS reads its own evidence and files improvement proposals for itself.

Each rule looks at the brain (last WINDOW_DAYS) or the job history and returns findings. A finding becomes a
proposal in the evolution queue with its evidence, a success measure and the numbers it starts from, so the
result can be checked later. Nothing is applied: you accept or reject proposals; accepted ones go to self-improve.
  weak_unguided     weak/free models did real work and none of it was guided by TIDOS
  guide_no_help     guided tasks of a model pass checks no more often than unguided ones
  failing_check     the same check (pytest, flutter analyze...) keeps failing in one project
  corrections       you keep correcting one kind of task in one project
  stuck             a weak model keeps hitting tool errors (5+ in one task)
  job_failing       an autopilot / control-center job failed several times this week
One proposal per finding key: an open one gets fresh evidence; a rejected one is not filed again for REJECT_DAYS.

  python -I tidos_learn/__main__.py diagnose [--dry-run]
"""
import os
import re
from datetime import datetime, timedelta, timezone

from tidos_session.detect import tier_for

from . import evolve

WINDOW_DAYS = 30
REJECT_DAYS = 30
CHECKS = [("flutter analyze", r"flutter\s+analyze"), ("flutter test", r"flutter\s+test"),
          ("dart analyze", r"dart\s+analyze"), ("pytest", r"\bpytest\b"), ("unittest", r"-m\s+unittest"),
          ("ruff", r"\bruff\b"), ("mypy", r"\bmypy\b"), ("tsc", r"\btsc\b"), ("eslint", r"\beslint\b"),
          ("npm test", r"\bnpm\s+(run\s+)?test"), ("node --test", r"node\s+--test"), ("jest", r"\bjest\b"),
          ("vitest", r"\bvitest\b"), ("cargo test", r"cargo\s+test"), ("go test", r"go\s+test"),
          ("gradle", r"gradlew?\s+\w*(test|check|build)")]


def _since(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()[:19]


def check_name(command):
    """The check a verification ran ('pytest', 'flutter analyze'...), or None."""
    for name, pattern in CHECKS:
        if re.search(pattern, command or ""):
            return name
    return None


def _weak(model):
    return bool(model) and tier_for(model)[0] != "frontier"


def _finding(key, title, reason, measure, baseline, priority="medium"):
    return {"key": key, "title": title, "reason": reason, "measure": measure, "baseline": baseline,
            "priority": priority}


# --- rules ----------------------------------------------------------------------------------------------
def weak_unguided(effect_rows):
    tasks = sum(r["guided"]["tasks"] + r["unguided"]["tasks"] for r in effect_rows)
    guided = sum(r["guided"]["tasks"] for r in effect_rows)
    if tasks >= 20 and guided == 0:
        top = ", ".join("%s (%d)" % (r["model"], r["unguided"]["tasks"]) for r in effect_rows[:3])
        return [_finding("weak_unguided", "Weak/free-model work never gets TIDOS guidance",
                         "%d tasks by weak or free models, 0 guided by TIDOS. Most used: %s. Connect TIDOS to those "
                         "tools (control center > Tool Scout) or make guidance reach them another way." % (tasks, top),
                         "guided tasks > 0 within 14 days", {"tasks": tasks, "guided": 0}, "high")]
    return []


def guide_no_help(effect_rows, min_verified=5):
    out = []
    for r in effect_rows:
        g, u = r["guided"], r["unguided"]
        if g["verified"] >= min_verified and u["verified"] >= min_verified and g["pass_rate"] <= u["pass_rate"]:
            out.append(_finding(
                "guide_no_help:" + r["model"], "GUIDE mode does not help %s" % r["model"],
                "Checks passed: guided %d%% (%d tasks) vs unguided %d%% (%d tasks). Review what the brief and "
                "tidos_guide tell this model; ablate rules that add nothing." % (
                    g["pass_rate"], g["verified"], u["pass_rate"], u["verified"]),
                "guided pass rate above unguided", {"guided": g["pass_rate"], "unguided": u["pass_rate"]}, "high"))
    return out


def failing_check(conn, min_fails=3):
    rows = conn.execute("SELECT s.project, v.command, v.passed, v.task_id FROM verifications v "
                        "JOIN tasks t ON t.id = v.task_id JOIN sessions s ON s.id = t.session_id "
                        "WHERE v.ts >= ? AND s.project IS NOT NULL", (_since(WINDOW_DAYS),)).fetchall()
    stats = {}
    for r in rows:
        name = check_name(r["command"])
        if name:
            s = stats.setdefault((r["project"], name), {"runs": 0, "fails": 0, "tasks": set()})
            s["runs"] += 1
            s["fails"] += 0 if r["passed"] else 1
            if not r["passed"]:
                s["tasks"].add(r["task_id"])
    out = []
    for (project, name), s in sorted(stats.items()):
        rate = 100 * (s["runs"] - s["fails"]) // s["runs"]
        if s["fails"] >= min_fails and len(s["tasks"]) >= 2 and rate < 50:
            out.append(_finding(
                "failing_check:%s:%s" % (project, name), "`%s` keeps failing in %s" % (name, project),
                "%d of %d runs failed in %d tasks (last %d days). Add a project note or playbook step on what "
                "usually breaks it and how it was fixed." % (s["fails"], s["runs"], len(s["tasks"]), WINDOW_DAYS),
                "pass rate of `%s` in %s at least 70%% (now %d%%)" % (name, project, rate), {"pass_rate": rate}))
    return out


def corrections(conn, min_tasks=5, min_rate=30):
    rows = conn.execute("SELECT s.project, t.task_type, COUNT(*) n, SUM(t.corrected) c FROM tasks t "
                        "JOIN sessions s ON s.id = t.session_id WHERE t.started_at >= ? AND s.project IS NOT NULL "
                        "AND t.task_type IS NOT NULL GROUP BY s.project, t.task_type", (_since(WINDOW_DAYS),))
    out = []
    for r in rows:
        rate = 100 * (r["c"] or 0) // r["n"]
        if r["n"] >= min_tasks and rate >= min_rate:
            out.append(_finding(
                "corrections:%s:%s" % (r["project"], r["task_type"]),
                "You often correct %s tasks in %s" % (r["task_type"], r["project"]),
                "%d of %d %s tasks were followed by a correction (last %d days). Turn the corrections into a "
                "preference or a playbook rule for this project." % (r["c"], r["n"], r["task_type"], WINDOW_DAYS),
                "correction rate below %d%% (now %d%%)" % (rate // 2, rate), {"correction_rate": rate}))
    return out


def stuck(conn, errors=5, min_tasks=3):
    rows = conn.execute("SELECT t.model, COUNT(*) n, SUM(CASE WHEN t.tool_errors >= ? THEN 1 ELSE 0 END) k "
                        "FROM tasks t WHERE t.started_at >= ? AND t.model IS NOT NULL GROUP BY t.model",
                        (errors, _since(WINDOW_DAYS)))
    out = []
    for r in rows:
        if _weak(r["model"]) and (r["k"] or 0) >= min_tasks:
            out.append(_finding(
                "stuck:" + r["model"], "%s gets stuck on tool errors" % r["model"],
                "%d of %d tasks had %d+ tool errors (last %d days). Add a GUIDE rule: after 2 failures of the same "
                "command, stop, read the error and change approach (or escalate)." % (r["k"], r["n"], errors, WINDOW_DAYS),
                "tasks with %d+ tool errors halved (now %d)" % (errors, r["k"]), {"stuck_tasks": r["k"]}))
    return out


def job_failing(history, min_fails=2, days=7):
    since = _since(days)
    fails = {}
    for j in history:
        if j.get("state") == "failed" and (j.get("started") or "") >= since:
            fails.setdefault(j["job"], []).append(j)
    return [_finding("job_failing:" + job, "Job `%s` keeps failing" % job,
                     "%d failed runs in %d days (last: %s, log %s)." % (len(items), days, items[-1].get("started"),
                                                                       os.path.basename(items[-1].get("log") or "")),
                     "next 3 runs succeed", {"failed": len(items)})
            for job, items in sorted(fails.items()) if len(items) >= min_fails]


# --- run ------------------------------------------------------------------------------------------------
def findings(conn, history=None):
    from tidos_session import effect
    effect_rows = effect.guidance_effect(conn)
    if history is None:
        from tidos_dashboard import jobs
        history = jobs.history()
    out = (weak_unguided(effect_rows) + guide_no_help(effect_rows) + failing_check(conn)
           + corrections(conn) + stuck(conn) + job_failing(history))
    return out


def file(found):
    """Add new findings to the evolution queue, refresh open ones. Returns [(status, item)]."""
    items = evolve.load()
    by_key = {}
    for i in items:
        if i.get("key"):
            by_key[i["key"]] = i  # the latest proposal for that key wins
    recent_reject = _since(REJECT_DAYS)
    done = []
    for f in found:
        old = by_key.get(f["key"])
        if old and old["status"] == "rejected" and (old.get("decided") or old.get("at", "")) >= recent_reject:
            done.append(("skipped (you rejected it)", old))
        elif old and old["status"] in ("new", "accepted"):
            done.append(("refreshed", evolve.update(old["id"], reason=f["reason"][:2000], evidence_at=_since(0))))
        elif old and old["status"] == "implemented":
            done.append(("still seen after implementation", evolve.update(old["id"], recurred=f["reason"][:500])))
        else:
            item = evolve.add(f["title"], f["reason"], f["priority"])
            done.append(("new", evolve.update(item["id"], source="diagnose", key=f["key"], measure=f["measure"],
                                              baseline=f["baseline"])))
    return done


def run(conn, dry_run=False, history=None):
    found = findings(conn, history)
    return [("would file", f) for f in found] if dry_run else file(found)
