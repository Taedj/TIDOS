"""Turn recorded sessions into playbooks: how tasks were actually solved, per project and in general.

Learning set (strong models count most):
  - tasks by a frontier-tier model that succeeded, or did edits and were not corrected by the user
  - tasks by any model whose final check really passed
Failures and user corrections are kept separately: they become the playbook's pitfalls.

Output: ~/.tidos/playbooks/<project>/<type>.md and ~/.tidos/playbooks/_general/<type>--<stack>.md
(private, outside every repo; regenerated on each run; `notes.md` files written by strong models are kept).
"""
import glob
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

from tidos_brain.claude_code import is_synthetic
from tidos_session.detect import tidos_home, tier_for

from . import classify

MIN_PROJECT_TASKS = 2
MIN_GENERAL_TASKS = 3
GENERATED_MARK = "generated: true"


def playbooks_dir():
    return os.path.join(tidos_home(), "playbooks")


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "general").lower()).strip("-") or "general"


def _short(text, limit=110):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def relpath(path, cwd):
    """Project-relative path, or None for files outside the project (temp, memory, other repos)."""
    if not path:
        return None
    norm = path.replace("\\", "/")
    if "<USER>" in norm or "/Temp/" in norm or "/.claude/" in norm:
        return None
    base = (cwd or "").replace("\\", "/").rstrip("/")
    if base and norm.lower().startswith(base.lower() + "/"):
        return norm[len(base) + 1:]
    if re.match(r"^[A-Za-z]:/|^/", norm):
        return None  # absolute path in another place
    return norm


# Reusable project checks; one-off inline scripts (python - <<EOF, variable assignments...) are not lessons
_CHECK_TOOLS = {"flutter", "dart", "npm", "npx", "pnpm", "yarn", "node", "pytest", "python", "python3", "py",
                "cargo", "go", "gradlew", "./gradlew", "mvn", "dotnet", "tsc", "eslint", "ruff", "mypy", "pyright",
                "make", "shellcheck"}


def normalize_check(command):
    """`cd D:/x && flutter analyze lib/a.dart 2>&1 | head` -> `flutter analyze`; None if not a reusable check."""
    cmd = re.sub(r"\s+", " ", command or "").strip()
    while re.match(r"^cd\s+(\"[^\"]*\"|\S+)(\s+&&|\s*;)\s*", cmd):
        cmd = re.sub(r"^cd\s+(\"[^\"]*\"|\S+)(\s+&&|\s*;)\s*", "", cmd, count=1)
    cmd = re.split(r"\s*(\||2>&1|2>|>|;|&&)\s*", cmd)[0].strip()
    tokens = cmd.split()
    if not tokens or "<<" in cmd or "=" in tokens[0]:
        return None
    tool = os.path.basename(tokens[0].strip('"')).lower().replace(".exe", "")
    if tool not in _CHECK_TOOLS:
        return None
    tokens[0] = tool
    if tool in ("python", "python3", "py"):
        if len(tokens) >= 3 and tokens[1] == "-m":
            return " ".join(["python", "-m", tokens[2]])
        return None  # running an ad-hoc script file is not a reusable check
    if tool in ("npm", "pnpm", "yarn") and len(tokens) >= 3 and tokens[1] == "run":
        return " ".join(tokens[:3])
    return " ".join(t for t in tokens[:2] if not re.search(r"[\\/]|\.\w+$", t) or t == tokens[0])


def load_tasks(conn):
    sessions = {r["id"]: dict(r) for r in conn.execute("SELECT * FROM sessions")}
    tasks = []
    by_session = defaultdict(dict)
    for r in conn.execute("SELECT * FROM tasks ORDER BY session_id, seq"):
        session = sessions.get(r["session_id"])
        if not session or is_synthetic(session["cwd"]):
            continue
        t = dict(r)
        t["project"] = session["project"] or "?"
        t["cwd"] = session["cwd"]
        t["calls"] = [dict(c) for c in conn.execute("SELECT * FROM tool_calls WHERE task_id = ? ORDER BY id", (r["id"],))]
        t["checks"] = [dict(v) for v in conn.execute("SELECT * FROM verifications WHERE task_id = ? ORDER BY id", (r["id"],))]
        _attribute_subrepo(t)
        t["type"] = classify.task_type(t["prompt"], t["calls"])
        t["stacks"] = classify.stacks(t["calls"])
        t["strong"] = tier_for(t["model"] or "unknown")[0] == "frontier"
        tasks.append(t)
        by_session[r["session_id"]][r["seq"]] = t
    for t in tasks:  # the user's next message after a corrected task is the lesson
        nxt = by_session[t["session_id"]].get(t["seq"] + 1)
        t["correction"] = nxt["prompt"] if (t["corrected"] and nxt) else None
    return tasks


def _attribute_subrepo(t):
    """A session started in a parent folder (D:\\work\\Dev) often works inside one repo (TIDOS, ZTAP...):
    credit the task to that repo when most of its files live there and it has its own .git."""
    tops = Counter()
    for c in t["calls"]:
        if c["kind"] in ("read", "edit"):
            p = relpath(c["summary"], t["cwd"])
            if p and "/" in p:
                tops[p.split("/", 1)[0]] += 1
    if not tops:
        return
    top, n = tops.most_common(1)[0]
    sub = os.path.join(t["cwd"] or "", top)
    if n >= 0.6 * sum(tops.values()) and os.path.isdir(os.path.join(sub, ".git")):
        t["project"] = top
        t["cwd"] = sub


def is_learning_example(t):
    if t["corrected"] or t["outcome"] == "failure":
        return False
    if t["verify_passed"] == 1:
        return True
    return t["strong"] and (t["outcome"] == "success" or (t["files_edited"] and t["tool_errors"] <= 2))


def _summarize(examples, failures, cwd_paths=True):
    reads, edits, checks, check_pass = Counter(), Counter(), Counter(), Counter()
    retried = Counter()
    for t in examples:
        first_edit = next((i for i, c in enumerate(t["calls"]) if c["kind"] == "edit"), len(t["calls"]))
        if cwd_paths:
            for c in t["calls"][:first_edit]:
                if c["kind"] == "read":
                    p = relpath(c["summary"], t["cwd"])
                    if p:
                        reads[p] += 1
            for c in t["calls"]:
                if c["kind"] == "edit":
                    p = relpath(c["summary"], t["cwd"])
                    if p:
                        edits[p] += 1
        runs = [(normalize_check(v["command"]), v["passed"]) for v in t["checks"]]
        runs = [(cmd, ok) for cmd, ok in runs if cmd]
        for cmd in {cmd for cmd, _ in runs}:
            checks[cmd] += 1
            if any(ok for c, ok in runs if c == cmd):
                check_pass[cmd] += 1
        results = [ok for _, ok in runs]
        if results and 0 in results and results[-1] == 1:
            retried[next(cmd for cmd, ok in runs if not ok)] += 1
    pitfalls = []
    for cmd, n in retried.most_common(3):
        pitfalls.append("`%s` failed first in %d task(s) before passing: run it after every change and fix "
                        "the exact error it prints." % (cmd, n))
    for t in [t for t in failures if t.get("correction")][:4]:
        pitfalls.append('User corrected "%s" with: "%s"' % (_short(t["prompt"], 60), _short(t["correction"], 140)))
    informative = [t for t in failures if t["outcome"] == "failure" and not t.get("correction")
                   and len(re.sub(r"https?://\S+", "", t["prompt"] or "").strip()) >= 30]
    for t in informative[:2]:
        pitfalls.append('Failed attempt: "%s" (last check failed)' % _short(re.sub(r"https?://\S+", "<link>", t["prompt"]), 90))
    return reads, edits, checks, check_pass, pitfalls


def _render(scope, ttype, stack_list, examples, failures, project=None):
    reads, edits, checks, check_pass, pitfalls = _summarize(examples, failures, cwd_paths=project is not None)
    verified = sum(1 for t in examples if t["verify_passed"] == 1)
    strong = sum(1 for t in examples if t["strong"])
    confidence = min(1.0, 0.4 + 0.4 * verified / len(examples) + 0.2 * strong / len(examples))
    # decay: evidence older than 30 days counts less (projects change); at most halved
    newest = max((t["started_at"] or "") for t in examples)[:10]
    try:
        age = (datetime.now(timezone.utc).date() - datetime.fromisoformat(newest).date()).days
    except ValueError:
        age = 0
    confidence = round(confidence * max(0.5, 1 - max(0, age - 30) / 365), 2)
    models = sorted({t["model"] for t in examples if t["model"]})
    sample = sorted({_short(t["prompt"], 120) for t in examples if t["prompt"] and len(t["prompt"]) > 15},
                    key=len, reverse=True)[:3]
    steps = []
    dirs = Counter()
    for counter in (reads, edits):
        for p, n in counter.items():
            dirs[(os.path.dirname(p) or ".") + "/"] += n
    if dirs:
        steps.append("Where the code lives: " + ", ".join("`%s`" % d for d, _ in dirs.most_common(4))
                     + ". Find the exact file with a search before opening it.")
    if reads:
        steps.append("Read before editing (most read): " + ", ".join("`%s`" % p for p, _ in reads.most_common(3)))
    if edits:
        steps.append("Most often changed: " + ", ".join("`%s`" % p for p, _ in edits.most_common(3)))
    if checks:
        best = checks.most_common(1)[0][0]
        steps.append("Verify with `%s` after every change; never report done before it passes." % best)
    else:
        steps.append("No automatic check was recorded for this kind of task: ask the user how to confirm it works.")
    avg_calls = round(sum(t["tool_calls"] for t in examples) / len(examples))
    lines = [
        "---", GENERATED_MARK, "type: %s" % ttype, "stack: %s" % ", ".join(stack_list),
        "project: %s" % (project or "any"), "confidence: %s" % confidence,
        "evidence: %d tasks (%d verified, %d by strong models)" % (len(examples), verified, strong),
        "models: %s" % ", ".join(models), "newest_evidence: %s" % (newest or "?"), "updated: %s" % datetime.now(timezone.utc).date().isoformat(), "---",
        "# %s: %s%s" % (ttype, scope, " (%s)" % ", ".join(stack_list) if project else ""),
        "", "## How it was done (learned from %d successful tasks, ~%d tool steps each)" % (len(examples), avg_calls),
    ]
    lines += ["%d. %s" % (i + 1, s) for i, s in enumerate(steps)]
    if checks:
        lines += ["", "## Checks that confirmed the work"]
        lines += ["- `%s` (passed in %d of %d tasks)" % (cmd, min(check_pass[cmd], n), n) for cmd, n in checks.most_common(4)]
    if pitfalls:
        lines += ["", "## Pitfalls"] + ["- " + p for p in pitfalls]
    if sample:
        lines += ["", "## Example requests solved this way"] + ['- "%s"' % s for s in sample]
    return "\n".join(lines) + "\n", confidence, verified, models


def distill(conn, out_dir=None):
    """Regenerate all playbooks. Returns a list of (path, type, stack, project, confidence, n)."""
    out_dir = out_dir or playbooks_dir()
    tasks = load_tasks(conn)
    examples = [t for t in tasks if is_learning_example(t)]
    lessons = [t for t in tasks if t["corrected"] or t["outcome"] == "failure"]
    written = []

    groups = defaultdict(list)
    for t in examples:
        groups[(t["project"], t["type"])].append(t)
    for (project, ttype), group in groups.items():
        if len(group) < MIN_PROJECT_TASKS or project in ("~", "?"):
            continue
        stack_list = [s for s, _ in Counter(s for t in group for s in t["stacks"]).most_common(3)]
        fails = [t for t in lessons if t["project"] == project and t["type"] == ttype]
        text, conf, verified, models = _render(project, ttype, stack_list, group, fails, project)
        path = os.path.join(out_dir, slug(project), "%s.md" % ttype)
        written.append((path, text, ttype, ", ".join(stack_list), project, conf, len(group), verified, models))

    general = defaultdict(list)
    for t in examples:
        general[(t["type"], t["stacks"][0])].append(t)
    for (ttype, stack), group in general.items():
        if len(group) < MIN_GENERAL_TASKS or stack == "general":
            continue
        fails = [t for t in lessons if t["type"] == ttype and stack in t["stacks"]]
        text, conf, verified, models = _render("all projects", ttype, [stack], group, fails)
        path = os.path.join(out_dir, "_general", "%s--%s.md" % (ttype, slug(stack)))
        written.append((path, text, ttype, stack, "any", conf, len(group), verified, models))

    keep = {w[0] for w in written}
    for old in glob.glob(os.path.join(out_dir, "**", "*.md"), recursive=True):
        if old not in keep:
            with open(old, "r", encoding="utf-8") as f:
                generated = GENERATED_MARK in f.read(400)
            if generated:
                os.remove(old)  # stale generated playbook; hand/strong-model notes are never removed
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute("DELETE FROM playbooks WHERE status = 'generated'")
        for path, text, ttype, stack, project, conf, n, verified, models in written:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            conn.execute("INSERT INTO playbooks (task_type, stack, path, source_models, uses, successes, rank, status,"
                         " created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                         (ttype, stack, path, ", ".join(models), n, verified, rank_for(conf, n), "generated", now, now))
    from . import prefs  # standing user directives, learned alongside the playbooks
    prefs.write(prefs.learn(conn))
    from . import xp  # XP + growth drafts (skill drafts, job change) from the fresh playbooks
    xp.level_up(conn)
    return [(w[0], w[2], w[3], w[4], w[5], w[6]) for w in written]


def rank_for(confidence, evidence):
    for rank, conf, n in (("S", 0.9, 10), ("A", 0.8, 6), ("B", 0.7, 4), ("C", 0.6, 3), ("D", 0.5, 2)):
        if confidence >= conf and evidence >= n:
            return rank
    return "E"


def add_note(project, stack, text, ttype="notes"):
    """A strong model (LEARN mode) records advice for weaker models, in its own words."""
    path = os.path.join(playbooks_dir(), slug(project), "notes.md")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("---\ntype: notes\nstack: %s\nproject: %s\nconfidence: 0.9\n---\n"
                    "# Notes from strong models: %s\n" % (stack, project, project))
    stamp = datetime.now(timezone.utc).date().isoformat()
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        f.write("- (%s, %s) %s\n" % (stamp, ttype, _short(text, 400)))
    return path
