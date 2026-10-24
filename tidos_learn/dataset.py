"""Trace -> dataset: verified work from the brain as JSONL, for evals or (later) fine-tuning a small model.

Each record is the USER's request plus the WORKFLOW TIDOS observed (step kinds with project-relative targets,
checks and their results, outcome). No model-written text (answers, code, reasoning) is exported: the dataset
teaches *how work is done* (read -> edit -> check), and avoids redistributing provider outputs. Check your
model providers' terms before training on anything derived from their sessions.

Every string passes the privacy firewall again; files outside the project are dropped.
"""
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

from tidos_brain import privacy
from tidos_session.detect import tidos_home

from . import distill

MAX_STEPS = 40
SCHEMA = "tidos-workflow/1"


_SKIP = ("cd ", "pushd ", "set ", "export ", "source ", "$env:")
_ABS = re.compile(r"""[A-Za-z]:[\\/]|^["']?(/[a-z]/|/home/|/Users/|~[\\/])|<USER>""")
_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def command(cmd):
    """The meaningful part of a shell command: drop `cd X &&` prefixes, keep a known check or the first
    4 tokens with absolute paths replaced by <path>."""
    for part in re.split(r"&&|\|\||;|\n", cmd or ""):
        part = part.strip().strip("()")
        if not part or part.lower().startswith(_SKIP) or part.lower() == "cd" or _ASSIGN.match(part):
            continue
        check = distill.normalize_check(part)
        if check:
            return check
        return " ".join("<path>" if _ABS.search(tok) else tok for tok in part.split()[:4])
    return ""


def _step(call, cwd):
    kind = call["kind"] or "other"
    summary = call["summary"] or ""
    if kind in ("read", "edit"):
        target = distill.relpath(summary, cwd)
        if not target:
            return None  # outside the project: private or irrelevant
    elif kind == "exec":
        target = command(summary)
    elif kind == "search":
        target = summary[:60]
    else:
        target = ""
    return {"kind": kind, "target": privacy.clean(target, 160) if target else "", "error": bool(call["is_error"])}


def record(t):
    steps = [s for s in (_step(c, t["cwd"]) for c in t["calls"]) if s][:MAX_STEPS]
    checks = [{"command": privacy.clean(command(c["command"]), 160),
               "passed": bool(c["passed"])} for c in t["checks"]]
    return {
        "schema": SCHEMA,
        "id": hashlib.sha256(("%s/%s" % (t["session_id"], t["seq"])).encode()).hexdigest()[:16],
        "request": privacy.clean(t["prompt"], privacy.MAX_PROMPT_CHARS),
        "task_type": t["type"],
        "stacks": t["stacks"],
        "model_tier": "strong" if t["strong"] else "other",
        "steps": steps,
        "checks": checks,
        "outcome": t["outcome"],
        "verified": t["verify_passed"] == 1,
        "first_check_passed": bool(checks and checks[0]["passed"]),
    }


def export(conn, out=None, strong_only=True, include_projects=None):
    """Write the dataset. Returns (path, stats). include_projects: optional set of project names."""
    tasks = distill.load_tasks(conn)
    picked = [t for t in tasks if distill.is_learning_example(t) and (t["strong"] or not strong_only)
              and t["prompt"] and (include_projects is None or t["project"] in include_projects)]
    out = out or os.path.join(tidos_home(), "datasets",
                              "tidos-workflow-%s.jsonl" % datetime.now(timezone.utc).strftime("%Y%m%d"))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    stats = Counter()
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        for t in picked:
            rec = record(t)
            if not rec["steps"]:
                continue
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            stats["records"] += 1
            stats["type:" + rec["task_type"]] += 1
            stats["verified"] += rec["verified"]
    card = os.path.splitext(out)[0] + ".md"
    with open(card, "w", encoding="utf-8", newline="\n") as f:
        f.write("# TIDOS workflow dataset (%s)\n\n- records: %d (verified: %d)\n- types: %s\n- source: %s tasks "
                "that TIDOS judged good examples\n- schema: %s (request, task_type, stacks, steps, checks, outcome)\n\n"
                "Private by default: it holds your own requests. Contains no model-written text; still check your "
                "providers' terms before using it to train a model.\n" % (
                    datetime.now(timezone.utc).date().isoformat(), stats["records"], stats["verified"],
                    ", ".join("%s %d" % (k[5:], v) for k, v in sorted(stats.items()) if k.startswith("type:")),
                    "strong-model" if strong_only else "all", SCHEMA))
    return out, dict(stats)
