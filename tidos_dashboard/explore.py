"""Control center tools: global search, "Ask TIDOS", settings editor, brain backups.

Search and the Ask digest only read TIDOS's own private data (brain.db, ~/.tidos). Ask TIDOS sends that digest
to a cheap Claude model with every tool disabled, only when the `ask_llm` switch is on.
"""
import glob
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone

from tidos_brain import control
from tidos_session import detect

STOPWORDS = set("a an the and or of to in on for with why what which who how when did does do is are was were "
                "this that these those my me i it its this week today last most more less tidos".split())
PER_KIND = 12


def _words(query):
    return [w for w in re.findall(r"[\w.+-]{2,}", query.lower()) if w not in STOPWORDS][:6]


def _snippet(text, word, width=140):
    i = text.lower().find(word)
    start = max(0, i - 40) if i >= 0 else 0
    return re.sub(r"\s+", " ", text[start:start + width]).strip()


def _md_files(sub):
    home = detect.tidos_home()
    for path in sorted(glob.glob(os.path.join(home, sub, "**", "*.md"), recursive=True)):
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            yield os.path.relpath(path, home).replace("\\", "/"), f.read()


def search(conn, query):
    """All words must match. Results grouped by kind: task, playbook, memory, eval, proposal."""
    words = _words(query)
    if not words:
        return {"query": query, "words": [], "results": []}
    results = []
    where = " AND ".join(["LOWER(t.prompt) LIKE ?"] * len(words))
    for r in conn.execute("SELECT t.prompt, t.outcome, t.started_at, t.model, s.project FROM tasks t JOIN sessions s "
                          "ON s.id = t.session_id WHERE %s ORDER BY t.started_at DESC LIMIT ?" % where,
                          ["%" + w + "%" for w in words] + [PER_KIND]):
        results.append({"kind": "task", "title": _snippet(r["prompt"] or "", words[0]), "project": r["project"],
                        "when": (r["started_at"] or "")[:16], "detail": "%s · %s" % (r["outcome"], r["model"] or "?")})
    for kind, sub in (("playbook", "playbooks"), ("memory", "memory"), ("memory", "drafts")):
        n = 0
        for rel, text in _md_files(sub):
            low = text.lower()
            if all(w in low for w in words):
                results.append({"kind": kind, "title": rel, "detail": _snippet(text, words[0]), "path": rel})
                n += 1
                if n >= PER_KIND:
                    break
    where = " AND ".join(["LOWER(suite || ' ' || task_name || ' ' || model) LIKE ?"] * len(words))
    for r in conn.execute("SELECT suite, task_name, model, with_tidos, passed, run_at FROM evals WHERE %s "
                          "ORDER BY run_at DESC LIMIT ?" % where, ["%" + w + "%" for w in words] + [PER_KIND]):
        results.append({"kind": "eval", "title": "%s/%s" % (r["suite"], r["task_name"]),
                        "detail": "%s · %s · %s" % (r["model"], {0: "plain", 1: "v4", 2: "guide"}.get(r["with_tidos"]),
                                                     "CLEAR" if r["passed"] else "FAIL"),
                        "when": (r["run_at"] or "")[:16]})
    from tidos_learn import evolve
    for p in evolve.load():
        if all(w in (p["title"] + " " + p["reason"]).lower() for w in words):
            results.append({"kind": "proposal", "title": "#%d %s" % (p["id"], p["title"]), "detail": p["status"]})
    return {"query": query, "words": words, "results": results}


# --- Ask TIDOS -----------------------------------------------------------------------------------------
def digest(conn, query, days=30):
    """Facts for the question: per project/type success over `days`, recent failures, matching items."""
    from tidos_learn import distill  # same classification + sub-repo attribution as the playbooks
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    tasks = [t for t in distill.load_tasks(conn) if (t["started_at"] or "") >= since]
    lines = ["Period: last %d days (UTC now %s), %d tasks." % (
        days, datetime.now(timezone.utc).strftime("%Y-%m-%d"), len(tasks))]
    groups = {}
    for t in tasks:
        key = (t["project"], t["type"], "+".join(t["stacks"]) or "?", "strong" if t["strong"] else "weak/medium")
        g = groups.setdefault(key, [0, 0, 0, 0, 0])
        g[0] += 1
        g[1] += t["outcome"] == "success"
        g[2] += t["outcome"] == "failure"
        g[3] += bool(t["corrected"])
        g[4] += t["verify_passed"] == 1
    lines.append("project | task type | stack | model tier | tasks | success | failure | corrected | check passed")
    for key, g in sorted(groups.items(), key=lambda kv: -kv[1][0])[:40]:
        lines.append("%s | %s | %s | %s | %d | %d | %d | %d | %d" % (key[0], key[1], key[2][:30], key[3], *g))
    fails = sorted((t for t in tasks if t["outcome"] == "failure" or t["corrected"]),
                   key=lambda t: t["started_at"] or "", reverse=True)[:15]
    if fails:
        lines.append("\nRecent failed or corrected tasks:")
        lines += ["- %s %s [%s, %s, %s]: %s" % ((f["started_at"] or "")[:10], f["project"], f["type"],
                                                "+".join(f["stacks"])[:20], f["model"],
                                                re.sub(r"\s+", " ", (f["prompt"] or ""))[:160]) for f in fails]
    hits = search(conn, query)["results"][:15]
    if hits:
        lines.append("\nItems matching the question:")
        lines += ["- [%s] %s %s" % (h["kind"], h["title"][:120], h.get("detail", "")[:100]) for h in hits]
    return "\n".join(lines)[:9000]


ASK_PROMPT = """You are TIDOS's analyst. Answer the owner's question using ONLY the data below (traces of their
coding sessions). Be concrete: name projects, task types, numbers. If the data cannot answer it, say what is
missing. At most 8 short lines, plain text.

QUESTION: {question}

DATA:
{data}"""


def ask(conn, question, llm=None):
    """Returns {answer, source: llm|local, digest}. llm(prompt) -> (text, error)."""
    data = digest(conn, question)
    if control.is_on("ask_llm"):
        if llm is None:
            from tidos_learn.summarize import ask_strong_model as llm  # noqa: N813  (tools disabled below)
        text, err = llm(ASK_PROMPT.format(question=question[:500], data=data))
        if text:
            return {"answer": text.strip(), "source": "llm", "digest": data}
        note = "(Model unavailable: %s. Showing the local facts.)" % err
    else:
        note = "(ask_llm is off: local facts only.)"
    return {"answer": note, "source": "local", "digest": data}


# --- settings editor (config/framework.md) -------------------------------------------------------------
FRAMEWORK = os.path.join(detect.REPO_ROOT, "config", "framework.md")
SETTINGS = {  # dotted key -> (type, constraint, help). Only these are editable; everything else stays manual.
    "persona_factory.enabled": (bool, None, "Persona factory may generate new personas"),
    "persona_factory.auto_sync": (bool, None, "Factory commits personas on a review branch and opens a PR"),
    "persona_factory.depth_threshold": (int, (1, 10), "Sessions/sources needed before generating a persona"),
    "persona_factory.one_run_per_boot": (bool, None, "At most one factory run per START TIDOS"),
    "gptid.enabled": (bool, None, "ChatGPT browser relay (also needs the gptid kill switch)"),
    "gptid.browser": (str, ("auto", "manual"), "Relay mode"),
    "gptid.timeout_seconds": (int, (5, 300), "Relay connect timeout"),
    "gptid.response_timeout_seconds": (int, (30, 900), "Max wait for a ChatGPT answer"),
    "gptid.limits.max_context_chars": (int, (500, 50000), "Max context sent to ChatGPT"),
    "gptid.limits.max_files": (int, (0, 50), "Max files attached per request"),
}
_LINE = re.compile(r"^(\s*)([A-Za-z_]+):(\s*)([^#\n]*?)(\s*#.*)?$")


def _scan(text):
    """{dotted key: (line index, raw value)} for scalar lines inside ```yaml blocks."""
    found, stack, in_yaml = {}, [], False
    for i, line in enumerate(text.split("\n")):
        if line.strip().startswith("```"):
            in_yaml, stack = line.strip() == "```yaml" and not in_yaml, []
            continue
        m = _LINE.match(line) if in_yaml else None
        if not m:
            continue
        indent = len(m.group(1))
        while stack and stack[-1][0] >= indent:
            stack.pop()
        key = ".".join([k for _, k in stack] + [m.group(2)])
        if m.group(4).strip():
            found[key] = (i, m.group(4).strip())
        else:
            stack.append((indent, m.group(2)))
    return found


def _parse(kind, raw):
    if kind is bool:
        return raw.lower() == "true"
    if kind is int:
        return int(raw)
    return raw.strip("'\"")


def settings():
    with open(FRAMEWORK, "r", encoding="utf-8") as f:
        found = _scan(f.read())
    out = []
    for key, (kind, constraint, help_text) in SETTINGS.items():
        if key in found:
            out.append({"key": key, "type": kind.__name__, "value": _parse(kind, found[key][1]), "help": help_text,
                        "choices": list(constraint) if kind is str else None,
                        "range": list(constraint) if kind is int else None})
    return out


def set_setting(key, value, path=None):
    """Validate and rewrite ONE value in place (comments and layout kept). Returns the new value."""
    if key not in SETTINGS:
        raise KeyError(key)
    kind, constraint, _ = SETTINGS[key]
    if kind is bool:
        if not isinstance(value, bool):
            raise ValueError("%s must be true or false" % key)
        text_value = "true" if value else "false"
    elif kind is int:
        if isinstance(value, bool) or not isinstance(value, int) or not constraint[0] <= value <= constraint[1]:
            raise ValueError("%s must be an integer in %d-%d" % (key, constraint[0], constraint[1]))
        text_value = str(value)
    else:
        if value not in constraint:
            raise ValueError("%s must be one of %s" % (key, ", ".join(constraint)))
        text_value = value
    path = path or FRAMEWORK
    with open(path, "r", encoding="utf-8", newline="") as f:
        text = f.read()
    nl = "\r\n" if "\r\n" in text else "\n"
    lines = text.replace("\r\n", "\n").split("\n")
    found = _scan("\n".join(lines))
    if key not in found:
        raise KeyError(key)
    i = found[key][0]
    m = _LINE.match(lines[i])
    lines[i] = "%s%s:%s%s%s" % (m.group(1), m.group(2), m.group(3) or " ", text_value, m.group(5) or "")
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(nl.join(lines))
    os.replace(tmp, path)
    return _parse(kind, text_value)


# --- backups -------------------------------------------------------------------------------------------
def backups_dir():
    return os.path.join(detect.tidos_home(), "backups")


def backup(conn, keep=10, label=""):
    """Online, consistent copy of brain.db (sqlite backup API). Keeps the newest `keep` backups.
    Never overwrites an existing backup (two in the same second get a counter)."""
    os.makedirs(backups_dir(), exist_ok=True)
    stem = "brain-%s%s" % (label, datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    target, n = os.path.join(backups_dir(), stem + ".db"), 1
    while os.path.exists(target):
        n += 1
        target = os.path.join(backups_dir(), "%s-%d.db" % (stem, n))
    dest = sqlite3.connect(target)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    for old in list_backups()[keep:]:
        os.remove(os.path.join(backups_dir(), old["name"]))
    return target


def list_backups():
    items = []
    for path in sorted(glob.glob(os.path.join(backups_dir(), "brain-*.db")), key=os.path.getmtime, reverse=True):
        items.append({"name": os.path.basename(path), "bytes": os.path.getsize(path)})
    return items


def check_backup(path):
    """(ok, detail): integrity_check passes and it looks like a TIDOS brain."""
    try:
        c = sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)
        try:
            if c.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                return False, "integrity check failed"
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            missing = {"sessions", "tasks", "evals"} - tables
            if missing:
                return False, "not a TIDOS brain (missing %s)" % ", ".join(sorted(missing))
            n = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        finally:
            c.close()
    except sqlite3.Error as e:
        return False, str(e)
    return True, "%d tasks" % n


def restore(name, db_path):
    """Replace brain.db with a backup (CLI only). The current brain is backed up first."""
    src = os.path.join(backups_dir(), os.path.basename(name))
    ok, detail = check_backup(src)
    if not ok:
        raise ValueError("refusing to restore %s: %s" % (name, detail))
    current = sqlite3.connect(db_path)
    try:
        safety = backup(current, keep=50, label="pre-restore-")
        source = sqlite3.connect(src)
        try:
            source.backup(current)  # writes through SQLite, so WAL/journal stay consistent
        finally:
            source.close()
    finally:
        current.close()
    return safety, detail
