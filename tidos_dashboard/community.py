"""The developer's view of community learning: every user's anonymous pack, merged (owner only).

Packs are cumulative snapshots, so only the LATEST pack of each installation counts (never twice).
export() writes community/knowledge.json into this checkout: reviewed by the developer and shipped with the
next TIDOS release, it reaches every user at their next START TIDOS.
"""
import json
import os
from collections import defaultdict
from datetime import datetime, timezone

from tidos_session.detect import REPO_ROOT

EXPORT = os.path.join(REPO_ROOT, "community", "knowledge.json")


def latest_per_install(packs):
    best = {}
    for p in packs:
        key = p.get("install") or p.get("_path")
        if key not in best or str(p.get("date")) > str(best[key].get("date")):
            best[key] = p
    return list(best.values())


def _rate(a, b):
    return round(100.0 * a / b) if b else None


def aggregate(packs):
    packs = [p for p in packs if p.get("schema") == "tidos-pack/1"]
    latest = latest_per_install(packs)
    work = defaultdict(lambda: defaultdict(int))
    checks = defaultdict(lambda: defaultdict(int))
    guide = defaultdict(lambda: {"guided": [0, 0], "unguided": [0, 0]})
    dungeons = defaultdict(lambda: [0, 0])
    tools = defaultdict(lambda: [0, 0])
    army = defaultdict(lambda: [0, 0])
    versions = defaultdict(int)
    for p in latest:
        versions[p.get("tidos_version", "?")] += 1
        for w in p.get("work", []):
            row = work[(w.get("type"), w.get("stack"), bool(w.get("strong")))]
            for k in ("tasks", "success", "verified", "first_try", "corrected"):
                row[k] += int(w.get(k) or 0)
        for c in p.get("checks", []):
            row = checks[(c.get("stack"), c.get("check"))]
            row["runs"] += int(c.get("runs") or 0)
            row["passed"] += int(c.get("passed") or 0)
            row["users"] += 1
        for g in p.get("guide", []):
            for side in ("guided", "unguided"):
                s = g.get(side) or {}
                guide[g.get("model")][side][0] += int(s.get("passed") or 0)
                guide[g.get("model")][side][1] += int(s.get("verified") or 0)
        for d in p.get("dungeons", []):
            dungeons[(d.get("agent"), d.get("mode"))][0] += int(d.get("passed") or 0)
            dungeons[(d.get("agent"), d.get("mode"))][1] += int(d.get("runs") or 0)
        for t in p.get("tools", []):
            tools[t.get("tool")][0] += int(t.get("passed") or 0)
            tools[t.get("tool")][1] += int(t.get("runs") or 0)
        for a in p.get("army", []):
            army[a.get("unit")][0] += int(a.get("missions") or 0)
            army[a.get("unit")][1] += int(a.get("xp") or 0)
    return {
        "contributors": len(latest), "packs": len(packs),
        "latest": max((str(p.get("date")) for p in packs), default=None),
        "versions": dict(versions),
        "work": sorted(({"type": k[0], "stack": k[1], "strong": k[2], **v,
                         "success_rate": _rate(v["success"], v["tasks"]), "first_try_rate": _rate(v["first_try"], v["tasks"])}
                        for k, v in work.items()), key=lambda r: -r["tasks"]),
        "checks": sorted(({"stack": k[0], "check": k[1], **v, "pass_rate": _rate(v["passed"], v["runs"])}
                          for k, v in checks.items()), key=lambda r: (-r["users"], -r["runs"]))[:60],
        "guide": sorted(({"model": m, "guided": _rate(*v["guided"]), "unguided": _rate(*v["unguided"]),
                          "guided_n": v["guided"][1], "unguided_n": v["unguided"][1]} for m, v in guide.items()),
                        key=lambda r: -(r["guided_n"] + r["unguided_n"])),
        "dungeons": sorted(({"agent": k[0], "mode": k[1], "pass_rate": _rate(*v), "runs": v[1]}
                            for k, v in dungeons.items()), key=lambda r: (r["agent"] or "", r["mode"] or "")),
        "tools": sorted(({"tool": k, "pass_rate": _rate(*v), "runs": v[1]} for k, v in tools.items()),
                        key=lambda r: -r["runs"]),
        "army": sorted(({"unit": k, "missions": v[0], "xp": v[1]} for k, v in army.items()), key=lambda r: -r["missions"]),
    }


def export(summary, path=EXPORT):
    """community/knowledge.json for the next release (no install ids: only merged numbers)."""
    data = dict(summary, schema="tidos-community/1",
                exported_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1)
    return path
