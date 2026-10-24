"""Does GUIDE mode help in real work? Compare weak/medium-model tasks done after a GUIDE start vs without.

Every START TIDOS appends to ~/.tidos/guide_log.jsonl. A task is "guided" when it ran with the same tool in the
same project within GUIDE_WINDOW_HOURS after a GUIDE-mode start. Signals are objective: last check passed,
user corrections, tool errors. Strong-model (LEARN) sessions are not part of the comparison.
"""
import json
import os
from datetime import datetime, timedelta

from .detect import tidos_home, tier_for

GUIDE_WINDOW_HOURS = 12
SOURCES = {"claude-code": "claude-code", "opencode": "opencode"}


def log_path():
    return os.path.join(tidos_home(), "guide_log.jsonl")


def log_start(session):
    os.makedirs(tidos_home(), exist_ok=True)
    with open(log_path(), "a", encoding="utf-8") as f:
        f.write(json.dumps({k: session.get(k) for k in ("started_at", "tool", "model", "tier", "mode", "project")}) + "\n")


def _starts():
    try:
        with open(log_path(), "r", encoding="utf-8") as f:
            entries = [json.loads(line) for line in f if line.strip()]
    except (OSError, ValueError):
        return []
    out = []
    for e in entries:
        if e.get("mode") != "guide" or not e.get("started_at"):
            continue
        start = datetime.fromisoformat(e["started_at"])
        out.append((SOURCES.get(e.get("tool")), os.path.normcase(os.path.normpath(e.get("project") or "")), start,
                    start + timedelta(hours=GUIDE_WINDOW_HOURS)))
    return out


def _parse(ts):
    try:
        return datetime.fromisoformat((ts or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def guidance_effect(conn):
    """Per weak/medium model: guided vs unguided task stats."""
    starts = _starts()
    rows = conn.execute("SELECT t.model, t.started_at, t.verify_passed, t.corrected, t.tool_errors, s.source, s.cwd "
                        "FROM tasks t JOIN sessions s ON s.id = t.session_id WHERE t.model IS NOT NULL").fetchall()
    stats = {}
    for r in rows:
        if tier_for(r["model"])[0] == "frontier":
            continue
        when = _parse(r["started_at"])
        cwd = os.path.normcase(os.path.normpath(r["cwd"] or ""))
        guided = bool(when) and any(src == r["source"] and cwd == proj and lo <= when <= hi
                                    for src, proj, lo, hi in starts)
        side = stats.setdefault(r["model"], {"guided": _empty(), "unguided": _empty()})["guided" if guided else "unguided"]
        side["tasks"] += 1
        if r["verify_passed"] is not None:
            side["verified"] += 1
            side["passed"] += r["verify_passed"]
        side["corrected"] += r["corrected"]
        side["errors"] += r["tool_errors"] or 0
    result = []
    for model, sides in stats.items():
        row = {"model": model}
        for name, s in sides.items():
            row[name] = dict(s, pass_rate=round(100 * s["passed"] / s["verified"]) if s["verified"] else None,
                             correction_rate=round(100 * s["corrected"] / s["tasks"]) if s["tasks"] else None)
        result.append(row)
    return sorted(result, key=lambda r: -(r["guided"]["tasks"] + r["unguided"]["tasks"]))


def _empty():
    return {"tasks": 0, "verified": 0, "passed": 0, "corrected": 0, "errors": 0}
