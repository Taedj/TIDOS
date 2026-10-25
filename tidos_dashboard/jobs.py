"""Jobs: the control center runs TIDOS commands for you (buttons instead of copy-paste).

Only the jobs in JOBS can run. Every parameter is checked against a list of known values (agents, suites,
units, proposals, projects): nothing typed in the browser ever reaches a command line unchecked, and there is
no shell. One job at a time; each has a log in ~/.tidos/jobs/ and can be cancelled (process tree killed).
Paid jobs (Claude calls) carry a cost estimate from your own past runs and a hard per-attempt budget.
"""
import json
import os
import re
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

from tidos_brain import db
from tidos_session.detect import REPO_ROOT, tidos_home

PY = sys.executable
DIFFICULTIES = ["E", "D", "C", "B", "A", "S"]
MODES = ["off", "guide", "compare", "both"]
CLAUDE_AGENTS = ["claude:haiku", "claude:sonnet"]
FALLBACK_ATTEMPT_USD = {"claude:haiku": 0.02, "claude:sonnet": 0.10}
ATTEMPT_BUDGET_USD = 0.25          # hard cap per Claude attempt in jobs started from the dashboard
SELF_IMPROVE_BUDGET_USD = 0.5
KEEP = 100
_LOCK = threading.Lock()


# --- the values a job may receive ---------------------------------------------------------------------
def allowed_agents(conn):
    """Claude models + the free OpenCode models you have actually used."""
    free = [r[0] for r in conn.execute("SELECT DISTINCT model FROM sessions WHERE source = 'opencode' AND model IS NOT NULL")
            if r[0] and ("free" in r[0] or r[0] == "opencode/big-pickle")]
    return CLAUDE_AGENTS + ["opencode:" + m for m in sorted(free)] + ["reference"]


def suites():
    from tidos_evals import dungeon
    return sorted({t.suite for t in dungeon.load_tasks(None, None)})


def projects(conn):
    from tidos_brain.claude_code import is_synthetic
    out = {}
    for project, cwd in conn.execute("SELECT project, cwd FROM sessions WHERE cwd IS NOT NULL GROUP BY cwd"):
        if cwd and not is_synthetic(cwd) and os.path.isdir(cwd) and project not in ("~", None):
            out.setdefault(_key(cwd), (cwd, project))  # D:/x and d:/x are one project on Windows
    return dict(out.values())


def _key(path):
    return os.path.normcase(os.path.normpath(path))


def count_tasks(suite=None, min_difficulty="E"):
    from tidos_evals import dungeon
    return sum(1 for t in dungeon.load_tasks(suite, None) if t.tool_available()
               and DIFFICULTIES.index(t.difficulty) >= DIFFICULTIES.index(min_difficulty))


def attempt_cost(conn, agent):
    if not agent.startswith("claude:"):
        return 0.0
    row = conn.execute("SELECT AVG(cost_usd) FROM evals WHERE model = ? AND cost_usd IS NOT NULL", (agent,)).fetchone()
    return float(row[0]) if row and row[0] else FALLBACK_ATTEMPT_USD.get(agent, 0.10)


def unit_suite(name):
    """The dungeon suite that tests a unit's specialty (None: no dungeon covers it)."""
    words = name.lower()
    for suite, keys in (("python", ("python", "tester", "reviewer", "architect", "security")),
                        ("javascript", ("javascript", "node", "web", "uiux")), ("dart", ("flutter", "dart", "mobile")),
                        ("sql", ("sql", "database", "db")), ("powershell", ("powershell", "windows")),
                        ("teaching", ("teaching", "exam", "tp"))):
        if any(k in words for k in keys):
            return suite
    return None


def default_free_agent(agents):
    return next((a for a in agents if a.startswith("opencode:")), "claude:haiku")


def measurable():
    """Implemented proposals whose branch still exists (merged and deleted branches cannot be measured)."""
    from tidos_learn import evolve
    out = set()
    for item in evolve.load():
        if item.get("branch") and subprocess.run(["git", "rev-parse", "--verify", "--quiet", item["branch"]],
                                                 cwd=REPO_ROOT, capture_output=True).returncode == 0:
            out.add(item["id"])
    return out


class JobError(ValueError):
    pass


def _need(value, allowed, what):
    if value not in allowed:
        raise JobError("unknown %s: %r" % (what, value))
    return value


# --- the jobs -----------------------------------------------------------------------------------------
def build(conn, job, p):
    """(argv, env, estimate_usd, title) for a job + params, or JobError. Never a shell, never free text."""
    p = p or {}
    if job == "distill":
        return [PY, "-I", "tidos_learn/__main__.py", "distill", "--quiet"], {}, 0.0, "Refresh learning"
    if job == "daily_quest":
        return [PY, "scripts/daily_quest.py"], {"TIDOS_E2E": "1"}, 0.0, "Daily quest (health check)"
    if job == "validate_dungeons":
        return [PY, "-I", "tidos_evals/__main__.py", "validate"], {}, 0.0, "Validate dungeons"
    if job == "backup":
        return [PY, "-I", "tidos_brain/__main__.py", "backup"], {}, 0.0, "Back up the brain"
    if job in ("raid", "trial"):
        agent = _need(p.get("agent", "claude:haiku"), allowed_agents(conn), "agent")
        suite = p.get("suite") or None
        if suite is not None:
            _need(suite, suites(), "suite")
        argv = [PY, "-I", "tidos_evals/__main__.py", "run", "--agent", agent, "--budget", str(ATTEMPT_BUDGET_USD)]
        if suite:
            argv += ["--suite", suite]
        if job == "raid":
            mode = _need(p.get("mode", "compare"), MODES, "mode")
            diff = _need(p.get("min_difficulty", "E"), DIFFICULTIES, "difficulty")
            argv += ["--tidos", mode, "--min-difficulty", diff]
            attempts = count_tasks(suite, diff) * (2 if mode in ("compare", "both") else 1)
            title = "Raid: %s (%s%s)" % (agent, mode, ", " + suite if suite else "")
        else:
            from tidos_learn import army
            unit = _need(p.get("unit"), set(army.units()), "unit")
            argv += ["--unit", unit]
            attempts = count_tasks(suite) * 2
            title = "Trial: %s with %s%s" % (unit, agent, " (" + suite + ")" if suite else "")
        return argv, {}, round(attempts * attempt_cost(conn, agent), 2), title
    if job == "self_improve":
        from tidos_learn import evolve
        accepted = {i["id"] for i in evolve.load() if i["status"] == "accepted"}
        pid = _need(int(p.get("id", -1)), accepted, "accepted proposal")
        return ([PY, "scripts/self_improve.py", "--id", str(pid), "--model", "haiku", "--budget",
                 str(SELF_IMPROVE_BUDGET_USD)], {}, SELF_IMPROVE_BUDGET_USD, "Implement proposal #%d (branch auto/...)" % pid)
    if job == "measure":
        pid = _need(int(p.get("id", -1)), measurable(), "implemented proposal with a branch")
        agents = allowed_agents(conn)
        agent = _need(p.get("agent") or default_free_agent(agents), agents, "agent")
        diff = _need(p.get("min_difficulty", "B"), DIFFICULTIES, "difficulty")
        attempts = count_tasks(None, diff) * 2
        return ([PY, "scripts/measure_proposal.py", "--id", str(pid), "--agent", agent, "--min-difficulty", diff,
                 "--budget", str(ATTEMPT_BUDGET_USD)], {}, round(attempts * attempt_cost(conn, agent), 2),
                "Measure proposal #%d with %s" % (pid, agent))
    if job == "scout_needs":
        cwd = _need(p.get("project"), projects(conn), "project")
        return ([PY, "-I", "tidos_scout/__main__.py", "needs", "--project", cwd, "--trust"], {}, 0.0,
                "Tool needs: %s" % projects(conn)[cwd])
    if job == "summarize":
        return [PY, "-I", "tidos_learn/__main__.py", "summarize", "--pending"], {}, 0.10, "Strong-model advice notes"
    raise JobError("unknown job %r" % job)


# --- state ------------------------------------------------------------------------------------------
def _dir():
    return os.path.join(tidos_home(), "jobs")


def _index_path():
    return os.path.join(_dir(), "index.json")


def history():
    try:
        with open(_index_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save(items):
    os.makedirs(_dir(), exist_ok=True)
    with open(_index_path() + ".tmp", "w", encoding="utf-8") as f:
        json.dump(items[-KEEP:], f, indent=1)
    os.replace(_index_path() + ".tmp", _index_path())


def _update(job_id, **fields):
    with _LOCK:
        items = history()
        for item in items:
            if item["id"] == job_id:
                item.update(fields)
        _save(items)


def get(job_id):
    return next((j for j in history() if j["id"] == job_id), None)


def _alive(pid):
    """Is this process still running? (never signals it: os.kill(pid, 0) would TERMINATE it on Windows)"""
    if not pid:
        return False
    if os.name == "nt":
        import ctypes
        handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def running():
    """The job that is really running now (in this process or another one: dashboard, START TIDOS autopilot)."""
    return next((j for j in history() if j["state"] in ("running", "cancelling") and _alive(j.get("pid"))), None)


def log_text(job_id, offset=0):
    job = get(job_id)
    if not job:
        return None
    try:
        with open(job["log"], "r", encoding="utf-8", errors="replace") as f:
            f.seek(max(0, int(offset)))
            text = f.read(200000)
            return {"text": text, "offset": f.tell(), "state": get(job_id)["state"]}
    except OSError:
        return {"text": "", "offset": offset, "state": job["state"]}


def spent_today(by="autopilot"):
    today = datetime.now(timezone.utc).date().isoformat()
    return round(sum((j.get("cost") if j.get("cost") is not None else j["estimate"]) for j in history()
                     if j["by"] == by and j["started"].startswith(today)), 2)


_PROCS = {}


def start(conn, job, params=None, by="owner", db_path=None, _popen=subprocess.Popen):
    """Start a job in the background. Raises JobError (bad job/params) or RuntimeError (another job running)."""
    argv, extra_env, estimate, title = build(conn, job, params)
    with _LOCK:
        busy = running()
        if busy:
            raise RuntimeError("busy: %s is running" % busy["title"])
        os.makedirs(_dir(), exist_ok=True)
        job_id = "%s-%s-%s" % (datetime.now().strftime("%Y%m%d-%H%M%S"), job, os.urandom(2).hex())
        log = os.path.join(_dir(), job_id + ".log")
        record = {"id": job_id, "job": job, "params": params or {}, "title": title, "by": by, "estimate": estimate,
                  "argv": " ".join(os.path.basename(a) if a == PY else a for a in argv), "state": "running",
                  "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ended": None, "exit": None,
                  "cost": None, "log": log}
        items = [dict(i, state="interrupted") if i["state"] in ("running", "cancelling") else i for i in history()]
        _save(items + [record])
    out = open(log, "w", encoding="utf-8")
    out.write("$ %s\n\n" % record["argv"])
    out.flush()
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", **extra_env)
    flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
    proc = _popen(argv, cwd=REPO_ROOT, stdout=out, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=env,
                  creationflags=flags)
    _PROCS[job_id] = proc
    _update(job_id, pid=proc.pid)
    threading.Thread(target=_wait, args=(job_id, proc, out, db_path), daemon=True).start()
    return record


def _wait(job_id, proc, out, db_path):
    code = proc.wait()
    out.close()
    _PROCS.pop(job_id, None)
    job = get(job_id) or {}
    state = "cancelled" if job.get("state") == "cancelling" else ("done" if code == 0 else "failed")
    _update(job_id, state=state, exit=code, ended=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            cost=_actual_cost(job, db_path))


def _actual_cost(job, db_path):
    """Real spend of an eval job (sum of its dungeon runs); other paid jobs keep their estimate."""
    if job.get("job") not in ("raid", "trial"):
        return None if job.get("estimate") else 0.0
    try:
        with open(job["log"], "r", encoding="utf-8", errors="replace") as f:
            m = re.search(r"^Run (\S+):", f.read(), re.M)
        if not m:
            return 0.0
        conn = db.connect(db_path)
        try:
            row = conn.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM evals WHERE run_id = ?", (m.group(1),)).fetchone()
        finally:
            conn.close()
        return round(float(row[0]), 3)
    except OSError:
        return None


def cancel(job_id):
    """Stop a running job and everything it started (works for jobs started by another TIDOS process too)."""
    job = get(job_id)
    if not job or job["state"] not in ("running", "cancelling") or not _alive(job.get("pid")):
        raise JobError("not running")
    _update(job_id, state="cancelling")
    proc = _PROCS.get(job_id)
    if proc:
        from tidos_evals.agents import kill_tree
        kill_tree(proc)
    elif os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(job["pid"])], capture_output=True)
    else:
        import signal
        os.kill(int(job["pid"]), signal.SIGTERM)
    deadline = time.time() + 10
    while _alive(job.get("pid")) and time.time() < deadline:
        time.sleep(0.2)
    if not proc:  # no waiting thread here: close the record ourselves
        _update(job_id, state="cancelled", ended=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    return True


def options(conn):
    """What the UI may offer (the same lists build() checks against)."""
    from tidos_learn import army, evolve
    return {"agents": allowed_agents(conn), "suites": suites(), "modes": MODES, "difficulties": DIFFICULTIES,
            "units": sorted(army.units()), "unit_suites": {n: unit_suite(n) for n in army.units()}, "projects": [{"path": k, "name": v} for k, v in sorted(projects(conn).items(),
                                                                                                   key=lambda kv: kv[1])],
            "accepted": [{"id": i["id"], "title": i["title"]} for i in evolve.load() if i["status"] == "accepted"
                         and not i.get("branch")],
            "attempt_usd": {a: round(attempt_cost(conn, a), 4) for a in CLAUDE_AGENTS}}
