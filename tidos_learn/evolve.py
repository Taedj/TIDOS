"""TIDOS evolution queue: improvement proposals for TIDOS itself, reviewed by a human.

~/.tidos/proposals.jsonl, one JSON object per line:
  {id, at, title, reason, priority: high|medium|low, status: new|accepted|rejected|implemented, branch?, note?}
Sources: the MCP tool tidos_propose, `tidos_learn propose`, the dashboard. Nothing is applied automatically:
accepted proposals can be implemented by scripts/self_improve.py on a separate branch, never pushed.
"""
import json
import os
import re
from datetime import datetime, timezone

from tidos_session.detect import tidos_home

STATUSES = ("new", "accepted", "rejected", "implemented")
PRIORITY = {"high": 3, "medium": 2, "low": 1}


def path():
    return os.path.join(tidos_home(), "proposals.jsonl")


def load():
    items = []
    try:
        with open(path(), "r", encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if line.strip():
                    item = json.loads(line)
                    item.setdefault("id", n)
                    item.setdefault("priority", "medium")
                    item.setdefault("status", "new")
                    items.append(item)
    except (OSError, ValueError):
        pass
    return items


def save(items):
    os.makedirs(tidos_home(), exist_ok=True)
    tmp = path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item) + "\n")
    os.replace(tmp, path())


def add(title, reason, priority="medium"):
    items = load()
    item = {"id": max([i["id"] for i in items] or [0]) + 1,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "title": title[:200], "reason": reason[:2000],
            "priority": priority if priority in PRIORITY else "medium", "status": "new"}
    items.append(item)
    save(items)
    return item


def set_status(item_id, status, **extra):
    if status not in STATUSES:
        raise ValueError("status must be one of %s" % ", ".join(STATUSES))
    items = load()
    for item in items:
        if item["id"] == item_id:
            item["status"] = status
            item["decided"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            item.update(extra)
            save(items)
            return item
    raise KeyError(item_id)


def update(item_id, **fields):
    """Attach evidence to a proposal (impact of its branch, measured effect) without changing its status."""
    items = load()
    for item in items:
        if item["id"] == item_id:
            item.update(fields)
            save(items)
            return item
    raise KeyError(item_id)


def ranked(status=None):
    items = [i for i in load() if status is None or i["status"] == status]
    return sorted(items, key=lambda i: (-PRIORITY.get(i["priority"], 2), i["id"]))


def issue_draft(item):
    """Markdown for a GitHub issue (privacy-checked text only); returned with the gh command to create it."""
    slug = re.sub(r"[^a-z0-9]+", "-", item["title"].lower()).strip("-")[:50] or "proposal"
    body = ("%s\n\n**Priority:** %s\n**Proposed:** %s\n\n_Created from the TIDOS evolution queue (#%d)._\n"
            % (item["reason"], item["priority"], item.get("at", "?"), item["id"]))
    folder = os.path.join(tidos_home(), "drafts", "issues")
    os.makedirs(folder, exist_ok=True)
    target = os.path.join(folder, "%03d-%s.md" % (item["id"], slug))
    with open(target, "w", encoding="utf-8", newline="\n") as f:
        f.write("# %s\n\n%s" % (item["title"], body))
    command = 'gh issue create --repo Taedj/TIDOS --title "%s" --body-file "%s" --label "evolution,%s"' % (
        item["title"].replace('"', "'"), target, item["priority"])
    return target, command
