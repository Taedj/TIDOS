"""Status Window data: provisional XP / level / rank computed from scored traces.

Provisional until Phase 9 (eval-gated XP engine). Per task:
  success +20, unknown +5, failure -10, last verify passed +5, corrected by user -5
Level n needs 100 * (n-1)^1.5 XP. Ranks: E 1-4, D 5-9, C 10-19, B 20-34, A 35-49, S 50+.
"""
import os
from datetime import datetime, timedelta, timezone

RANKS = [(50, "S"), (35, "A"), (20, "B"), (10, "C"), (5, "D"), (1, "E")]
OUTCOME_XP = {"success": 20, "unknown": 5, "failure": -10}


def task_xp(row):
    xp = OUTCOME_XP.get(row["outcome"], 0)
    if row["verify_passed"] == 1:
        xp += 5
    if row["corrected"]:
        xp -= 5
    return xp


def level_for(xp):
    level = 1
    while 100 * level ** 1.5 <= xp:
        level += 1
    floor_xp = int(100 * (level - 1) ** 1.5)
    next_xp = int(100 * level ** 1.5)
    return level, floor_xp, next_xp


def rank_for(level):
    return next(r for threshold, r in RANKS if level >= threshold)


def _pct(num, den):
    return round(100 * num / den) if den else 0


def status(conn, now=None):
    now = now or datetime.now(timezone.utc)
    rows = conn.execute(
        "SELECT t.*, s.project FROM tasks t JOIN sessions s ON s.id = t.session_id ORDER BY t.started_at").fetchall()
    xp = max(0, sum(task_xp(r) for r in rows))
    level, floor_xp, next_xp = level_for(xp)

    total = len(rows)
    edits = [r for r in rows if r["files_edited"]]
    verified = [r for r in rows if r["verify_passed"] is not None]
    decided = [r for r in rows if r["outcome"] in ("success", "failure")]
    stats = [
        {"key": "INT", "name": "Intelligence", "value": _pct(sum(r["outcome"] == "success" for r in decided), len(decided)),
         "hint": "success rate of tasks with a clear outcome"},
        {"key": "PRE", "name": "Precision", "value": _pct(sum(r["verify_passed"] == 1 for r in verified), len(verified)),
         "hint": "last test/lint/build run passed"},
        {"key": "DIS", "name": "Discipline", "value": _pct(sum(r["verify_runs"] > 0 for r in edits), len(edits)),
         "hint": "tasks that edited code AND ran a verification"},
        {"key": "WIS", "name": "Wisdom", "value": 100 - _pct(sum(r["corrected"] for r in rows), total),
         "hint": "answers the user did not have to correct"},
        {"key": "AGI", "name": "Agility", "value": _pct(sum(r["tool_errors"] == 0 for r in rows), total),
         "hint": "tasks finished without a tool error"},
    ]

    domains = {}
    for r in rows:
        d = domains.setdefault(r["project"] or "?", {"name": r["project"] or "?", "xp": 0, "tasks": 0, "success": 0})
        d["xp"] += task_xp(r)
        d["tasks"] += 1
        d["success"] += r["outcome"] == "success"
    for d in domains.values():
        d["xp"] = max(0, d["xp"])
        d["level"] = level_for(d["xp"])[0]
        d["rank"] = rank_for(d["level"])
    top_domains = sorted(domains.values(), key=lambda d: d["xp"], reverse=True)[:8]

    today = now.date().isoformat()
    todays = [r for r in rows if (r["started_at"] or "").startswith(today)]
    today_edits = [r for r in todays if r["files_edited"]]
    quests = [
        {"title": "Clear 3 verified tasks", "progress": sum(r["verify_passed"] == 1 for r in todays), "goal": 3},
        {"title": "Zero corrections today", "progress": 0 if any(r["corrected"] for r in todays) else 1, "goal": 1,
         "failed": any(r["corrected"] for r in todays)},
        {"title": "Verify every code edit", "progress": sum(r["verify_runs"] > 0 for r in today_edits),
         "goal": max(1, len(today_edits))},
    ]
    for q in quests:
        q["done"] = not q.get("failed") and q["progress"] >= q["goal"]

    models = conn.execute("SELECT model, COUNT(*) n, AVG(score) s FROM tasks WHERE model IS NOT NULL"
                          " GROUP BY model ORDER BY n DESC").fetchall()
    cleared = [{"ts": r["ended_at"], "project": r["project"], "prompt": (r["prompt"] or "")[:140], "score": r["score"]}
               for r in reversed(rows) if r["outcome"] == "success"][:8]

    return {
        "player": {"xp": xp, "level": level, "rank": rank_for(level), "floor_xp": floor_xp, "next_xp": next_xp},
        "stats": stats,
        "totals": {"tasks": total, "sessions": conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0],
                   "success": sum(r["outcome"] == "success" for r in rows),
                   "failure": sum(r["outcome"] == "failure" for r in rows),
                   "tokens_in": sum(r["input_tokens"] or 0 for r in rows),
                   "tokens_out": sum(r["output_tokens"] or 0 for r in rows)},
        "domains": top_domains,
        "quests": quests,
        "models": [{"model": m["model"], "tasks": m["n"], "avg_score": round(m["s"] or 0, 2)} for m in models],
        "cleared": cleared,
        "provisional": True,
    }


def live(conn, since_id=0, limit=200):
    rows = conn.execute("SELECT * FROM live_events WHERE id > ? ORDER BY id DESC LIMIT ?", (since_id, limit)).fetchall()
    return [dict(r) for r in reversed(rows)]


def active_sessions(conn, now=None, minutes=10):
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    rows = conn.execute(
        "SELECT session_id, MAX(ts) last_ts, COUNT(*) events, SUM(is_error) errors,"
        " (SELECT tool FROM live_events l2 WHERE l2.session_id = l.session_id ORDER BY id DESC LIMIT 1) last_tool,"
        " (SELECT cwd FROM live_events l3 WHERE l3.session_id = l.session_id AND cwd IS NOT NULL"
        "  ORDER BY id DESC LIMIT 1) cwd"
        " FROM live_events l WHERE ts > ? GROUP BY session_id ORDER BY last_ts DESC", (since,)).fetchall()
    return [dict(r) for r in rows]


def recent_tasks(conn, limit=40):
    rows = conn.execute(
        "SELECT t.id, t.prompt, t.model, t.started_at, t.ended_at, t.tool_calls, t.tool_errors, t.files_edited,"
        " t.verify_runs, t.verify_passed, t.corrected, t.score, t.outcome, s.project"
        " FROM tasks t JOIN sessions s ON s.id = t.session_id ORDER BY t.started_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def dungeons(conn):
    """Dungeon (eval) board: per-agent pass rates with/without TIDOS + latest result per task."""
    from tidos_evals import dungeon  # local import: the dashboard must start even without evals

    tasks = [{"id": t.id, "suite": t.suite, "name": t.name, "title": t.title, "difficulty": t.difficulty}
             for t in dungeon.load_tasks()]
    rows = conn.execute(
        "SELECT e.* FROM evals e JOIN (SELECT MAX(id) id FROM evals WHERE agent NOT IN ('reference', 'noop')"
        " AND COALESCE(error, '') NOT LIKE 'contaminated%'"
        " GROUP BY suite, task_name, model, with_tidos) latest ON latest.id = e.id").fetchall()
    columns, cells, board = [], {}, {}
    for r in rows:
        col = "%s|%d" % (r["model"], r["with_tidos"])
        if col not in columns:
            columns.append(col)
        cells["%s/%s|%s" % (r["suite"], r["task_name"], col)] = {"passed": r["passed"], "seconds": r["duration_s"],
                                                                 "cost": r["cost_usd"], "error": r["error"]}
        b = board.setdefault(r["model"], {"model": r["model"], "off": [0, 0], "on": [0, 0], "cost": 0.0})
        side = b["on" if r["with_tidos"] else "off"]
        side[0] += r["passed"]
        side[1] += 1
        b["cost"] += r["cost_usd"] or 0
    leaderboard = []
    for b in board.values():
        off = round(100 * b["off"][0] / b["off"][1]) if b["off"][1] else None
        on = round(100 * b["on"][0] / b["on"][1]) if b["on"][1] else None
        leaderboard.append({"model": b["model"], "off": off, "on": on, "off_n": b["off"], "on_n": b["on"],
                            "lift": on - off if off is not None and on is not None else None,
                            "cost": round(b["cost"], 3)})
    leaderboard.sort(key=lambda b: max(b["on"] or 0, b["off"] or 0), reverse=True)
    columns.sort(key=lambda c: (c.split("|")[0], c.split("|")[1]))
    last = conn.execute("SELECT MAX(run_at) FROM evals").fetchone()[0]
    return {"tasks": tasks, "columns": columns, "cells": cells, "leaderboard": leaderboard, "last_run": last}


def playbooks(conn):
    """Playbook Library: every learned playbook + notes, with rank, served counts and disabled flag."""
    import glob
    import re as _re
    from tidos_session import pbstate

    state = pbstate.load()
    ranks = {r["path"]: r["rank"] for r in conn.execute("SELECT path, rank FROM playbooks")}
    items = []
    base = pbstate.playbooks_dir()
    for path in sorted(glob.glob(os.path.join(base, "**", "*.md"), recursive=True)):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read(1500)
        except OSError:
            continue
        front = dict(_re.findall(r"^(\w+):\s*(.+)$", text.split("\n---", 1)[0], _re.M))
        rel = pbstate.rel(path)
        served = state["served"].get(rel, {})
        items.append({"path": rel, "project": front.get("project", "?"), "type": front.get("type", "?"),
                      "stack": front.get("stack", ""), "confidence": front.get("confidence", ""),
                      "evidence": front.get("evidence", ""), "rank": ranks.get(path, "notes" if front.get("type") == "notes" else "-"),
                      "served": served.get("n", 0), "last_served": served.get("last"),
                      "disabled": rel in state["disabled"]})
    items.sort(key=lambda i: (i["project"] == "any", i["project"], i["type"]))
    return {"playbooks": items, "dir": "~/.tidos/playbooks"}


def playbook_text(relpath):
    from tidos_session import pbstate
    base = os.path.realpath(pbstate.playbooks_dir())
    full = os.path.realpath(os.path.join(base, relpath))
    if not full.startswith(base + os.sep) or not full.endswith(".md") or not os.path.isfile(full):
        return None
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def security_log(conn, limit=50):
    return [dict(r) for r in conn.execute("SELECT * FROM security_log ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
