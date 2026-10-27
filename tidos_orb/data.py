"""What the TIDOS orb shows: one read-only snapshot of the brain (no login, nothing is changed).

The same numbers as `/tidos-status` and the Control Center; actions stay behind the Control Center login.
"""
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone

from tidos_dashboard import stats
from tidos_session import detect


def growth(conn, now=None, days=14):
    """XP gained and tasks cleared per day, oldest first (the 'revolution' chart)."""
    now = now or datetime.now(timezone.utc)
    first = (now.date() - timedelta(days=days - 1)).isoformat()
    by_day = {(now.date() - timedelta(days=i)).isoformat(): {"xp": 0, "cleared": 0, "tasks": 0}
              for i in range(days)}
    for row in conn.execute("SELECT * FROM tasks WHERE started_at >= ?", (first,)):
        day = by_day.get((row["started_at"] or "")[:10])
        if day is None:
            continue
        day["tasks"] += 1
        day["xp"] += stats.task_xp(row)
        day["cleared"] += row["outcome"] == "success"
    return [dict(day=d, **by_day[d]) for d in sorted(by_day)]


def _session():
    try:
        with open(os.path.join(detect.tidos_home(), "session.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return {"tool": data.get("tool"), "model": data.get("model"), "mode": data.get("mode"),
            "project": os.path.basename(data.get("project") or "") or None, "started_at": data.get("started_at")}


def _recommendations(conn):
    try:
        from tidos_dashboard import autopilot
        return [{"title": r["title"], "reason": r["reason"], "verdict": r["verdict"], "auto": r["auto"]}
                for r in autopilot.decide(conn)]
    except Exception:  # noqa: BLE001 - the orb must show something even if the autopilot cannot decide
        return []


def snapshot(conn, now=None):
    now = now or datetime.now(timezone.utc)
    status = stats.status(conn, now)
    evo = stats.evolution()
    proposals = [{k: p.get(k) for k in ("id", "title", "reason", "priority", "status", "branch")}
                 for p in evo["proposals"]]
    return {
        "updated_at": now.isoformat(timespec="seconds"),
        "session": _session(),
        "player": status["player"],
        "stats": status["stats"],
        "totals": status["totals"],
        "domains": status["domains"][:6],
        "quests": status["quests"],
        "growth": growth(conn, now),
        "proposals": proposals[:12],
        "proposal_counts": dict(Counter(p["status"] for p in proposals)),
        "report": evo["report"],
        "drafts": evo["drafts"],
        "notifications": stats.notifications(conn),
        "solutions": status["cleared"],
        "next": _recommendations(conn)[:8],
    }


def attention(snap):
    """(count, mood) for the orb badge: mood is 'bad' (something broke), 'act' (your call) or 'calm'."""
    notes = snap.get("notifications") or []
    bad = sum(n["level"] == "bad" for n in notes)
    act = sum(n["level"] == "ok" for n in notes) + (snap.get("proposal_counts") or {}).get("new", 0)
    return bad + act, "bad" if bad else "act" if act else "calm"
