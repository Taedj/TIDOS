"""Autopilot: TIDOS decides what to run next, and runs it when the `autopilot` switch is on.

decide() looks at the brain and the files and returns recommendations, each with its reason and the model it uses (if any):
  - refresh learning        when the last refresh is older than 6 h                      auto
  - daily quest             when today has no report                                     auto
  - back up the brain       when the newest backup is older than 7 days                  auto
  - diagnose                once a day: read the evidence, file improvement proposals    auto (you accept them)
  - trial a draft unit      when a draft has no trial and its suite has enough dungeons  auto
  - activate a unit         when a draft WON its trial (better than plain, not a tie)   trust: propose at first
  - implement a proposal    when you accepted it and it has no branch yet                auto
  - measure a proposal      when its branch exists and its effect was never measured    auto
  - weekly weak-model check GUIDE vs plain with a free model (plan 6.8)                 auto, weekly
  - tool needs              per active project (installing still needs your approval)    shown only
Jobs that need a model use a FREE model (tidos_session.helper.background), never the model of your last START
TIDOS; with no free model they are skipped. TIDOS never costs anything.
Rules: one job at a time; a job that failed in the last 24 h is not retried automatically; each job runs at most
DAILY_CAP times in 24 h, so a job that achieves nothing cannot loop; nothing here installs, pushes, merges,
changes a switch or connects a tool: those stay yours.
Graduated trust (tidos_brain.trust): each kind of job has a level (observe < propose < act_undo < act). Below
act_undo the autopilot only suggests it; every job is written to the action journal, good outcomes raise the
level after a streak, your undo lowers it. Unit activation starts at 'propose' and can earn act_undo (never more).

  python -I tidos_dashboard/autopilot.py --once      run every due job, one after another (START TIDOS calls this
                                                      in the background when the autopilot switch is on)
"""
import glob
import os
import sys
import threading
import time
from datetime import datetime, timedelta, timezone

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidos_brain import control, db, trust  # noqa: E402
from tidos_dashboard import jobs  # noqa: E402
from tidos_session.detect import tidos_home  # noqa: E402

LEARN_EVERY = timedelta(hours=6)
BACKUP_EVERY = timedelta(days=7)
DIAGNOSE_EVERY = timedelta(hours=24)
WEAK_CHECK_EVERY = timedelta(days=7)
RETRY_AFTER = timedelta(hours=24)
DAILY_CAP = {"distill": 5}  # runs per job + params in 24 h; every other job: 1
TICK_SECONDS = 300
MAX_JOBS_PER_RUN = 6


def _now():
    return datetime.now(timezone.utc)


def _ts(iso):
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def _last(job, params=None, states=("done",)):
    best = None
    for j in jobs.history():
        if j["job"] == job and j["state"] in states and (params is None or j.get("params") == params):
            t = _ts(j.get("ended") or j.get("started"))
            best = t if t and (best is None or t > best) else best
    return best


def _recently_failed(job, params):
    t = _last(job, params, states=("failed", "interrupted"))
    return t is not None and _now() - t < RETRY_AFTER


def _runs_today(job, params):
    since = _now() - timedelta(hours=24)
    n = 0
    for j in jobs.history():
        t = _ts(j.get("started"))
        if j["job"] == job and j.get("by") == "autopilot" and j.get("params") == params and t and t > since:
            n += 1
    return n


def decide(conn):
    recs = []

    def add(key, job, params, title, reason, auto=True):
        try:
            _, _, _, model = jobs.build(conn, job, params)
        except jobs.JobError:
            return
        recs.append({"key": key, "job": job, "params": params, "title": title, "reason": reason,
                     "model": model, "auto": auto})

    last = _last("distill")
    row = conn.execute("SELECT MAX(updated_at) FROM playbooks").fetchone()  # START TIDOS refreshes learning too
    learned = _ts(row[0]) if row and row[0] else None
    last = max([t for t in (last, learned) if t], default=None)
    if last is None or _now() - last > LEARN_EVERY:
        add("distill", "distill", {}, "Refresh learning", "last refresh: %s" % (last.isoformat()[:16] if last else "never"))
    today = _now().date().isoformat()
    if not os.path.exists(os.path.join(tidos_home(), "reports", today + ".md")):
        add("daily_quest", "daily_quest", {}, "Run the daily quest", "no health report for today yet")
    backups = glob.glob(os.path.join(tidos_home(), "backups", "*.db"))
    newest = max((os.path.getmtime(b) for b in backups), default=0)
    if _now().timestamp() - newest > BACKUP_EVERY.total_seconds():
        add("backup", "backup", {}, "Back up the brain", "newest backup is older than 7 days" if backups else "no backup yet")

    lastd = _last("diagnose")
    if lastd is None or _now() - lastd > DIAGNOSE_EVERY:
        add("diagnose", "diagnose", {}, "Diagnose: propose improvements",
            "read the evidence (checks, corrections, stuck models, failing jobs, guidance effect) once a day")

    agent = jobs.background_agent(conn)  # free; None: no free model, so no model job runs by itself
    from tidos_learn import army, evolve
    trials = army.load_state().get("trials", {})
    for name, u in sorted(army.units().items()):
        suite = jobs.unit_suite(name)
        if agent and u["state"] == "draft" and name not in trials and suite and jobs.trial_ready(suite):
            add("trial:" + name, "trial", {"unit": name, "suite": suite, "agent": agent},
                "Trial %s" % name, "draft unit, never tested: %s dungeons with and without it" % suite)
        trial = trials.get(name)
        if u["state"] == "draft" and trial and trial.get("unit", 0) > trial.get("plain", 0):  # a win, not a tie
            add("activate:" + name, "activate_unit", {"unit": name}, "Activate %s" % name,
                "won its trial: %(unit)d%% with it vs %(plain)d%% plain on %(tasks)d dungeons" % trial)
    for item in evolve.load():
        if agent and item["status"] == "accepted" and not item.get("branch"):
            add("self_improve:%d" % item["id"], "self_improve", {"id": item["id"], "agent": agent},
                "Implement proposal #%d" % item["id"], "you accepted it: %s" % item["title"][:80])

    measured = {i["id"] for i in evolve.load() if i.get("measure")}
    for pid in sorted(jobs.measurable() - measured) if agent else ():
        add("measure:%d" % pid, "measure", {"id": pid, "agent": agent}, "Measure proposal #%d" % pid,
            "implemented on a branch, effect never measured: GUIDE dungeons before vs after")

    weak = [a for a in jobs.allowed_agents(conn) if a.startswith("opencode:")]
    if weak and agent:
        agent = agent if agent in weak else weak[0]
        lastw = _last("raid", {"agent": agent, "mode": "compare", "min_difficulty": "A"})
        if lastw is None or _now() - lastw > WEAK_CHECK_EVERY:
            add("weak_check", "raid", {"agent": agent, "mode": "compare", "min_difficulty": "A"},
                "Weekly GUIDE check with %s" % agent.split("/")[-1],
                "does TIDOS's guidance still help a free model? (plain vs GUIDE, hard dungeons)")

    since = (_now() - timedelta(days=14)).isoformat()
    active = {jobs._key(r[0]) for r in conn.execute("SELECT DISTINCT s.cwd FROM sessions s JOIN tasks t ON t.session_id = s.id "
                                         "WHERE t.started_at >= ?", (since,))}
    for cwd, name in sorted(jobs.projects(conn).items(), key=lambda kv: kv[1]):
        if jobs._key(cwd) in active:
            add("scout:" + cwd, "scout_needs", {"project": cwd}, "Tool needs for %s" % name,
                "active in the last 14 days: which checks is it missing?", auto=False)
    return _with_verdicts(recs)


def _with_verdicts(recs):
    on = control.is_on("autopilot")
    for r in recs:
        r["trust"] = trust.level(r["job"]) if r["job"] in trust.DEFAULTS else None
        if r["auto"] and r["trust"] == "observe":
            r["auto"], r["verdict"] = False, "trust: observe only"
            continue
        if r["auto"] and r["trust"] == "propose":
            r["auto"], r["verdict"] = False, "your call: runs by itself after %d good runs" % trust.PROMOTE_AFTER
            continue
        if not r["auto"]:
            r["verdict"] = "your call"
        elif _recently_failed(r["job"], r["params"]):
            r["auto"], r["verdict"] = False, "failed in the last 24 h: run it yourself after a look at its log"
        elif _runs_today(r["job"], r["params"]) >= DAILY_CAP.get(r["job"], 1):
            r["auto"], r["verdict"] = False, "already ran in the last 24 h: next run tomorrow"
        else:
            r["verdict"] = "autopilot will run it" if on else "autopilot is off"
    return recs


def _settle(log=None):
    try:
        for a in trust.settle():
            if log:
                log("autopilot", "action #%d %s: %s" % (a["id"], a["state"], a["title"][:80]))
    except (OSError, ValueError) as e:
        if log:
            log("autopilot", "action journal: %s" % e)


def tick(conn, db_path=None, log=None):
    """One autopilot step: settle finished actions, start the first due auto job. Returns the job record or None."""
    _settle(log)
    if not control.is_on("autopilot") or jobs.running():
        return None
    for r in decide(conn):
        if r["auto"]:
            record = jobs.start(conn, r["job"], r["params"], by="autopilot", db_path=db_path)
            if log:
                log("autopilot", "%s (%s)" % (record["title"], r["reason"][:80]))
            return record
    return None


def loop(db_path=None, log=None, interval=TICK_SECONDS):
    """Background thread for the control center: tick every few minutes while it runs."""
    def run():
        time.sleep(20)  # let the server come up first
        while True:
            try:
                conn = db.connect(db_path)
                try:
                    tick(conn, db_path, log)
                finally:
                    conn.close()
            except Exception as e:  # noqa: BLE001 - the autopilot must never take the server down
                if log:
                    log("autopilot", "error: %s" % e)
            time.sleep(interval)
    threading.Thread(target=run, daemon=True, name="tidos-autopilot").start()


def run_once(db_path=None):
    """Run every due auto job, one after another (START TIDOS / schedulers). Returns the records run."""
    done, seen = [], set()
    _settle()
    for _ in range(MAX_JOBS_PER_RUN):
        conn = db.connect(db_path)
        try:
            if not control.is_on("autopilot") or jobs.running():
                break
            due = [r for r in decide(conn) if r["auto"] and r["key"] not in seen]
            if not due:
                break
            seen.add(due[0]["key"])
            record = jobs.start(conn, due[0]["job"], due[0]["params"], by="autopilot", db_path=db_path)
        finally:
            conn.close()
        while (jobs.get(record["id"]) or {}).get("state") in ("running", "cancelling"):
            time.sleep(2)
        done.append(jobs.get(record["id"]))
    return done


if __name__ == "__main__":
    if "--once" in sys.argv:
        for job in run_once():
            print("%s: %s" % (job["title"], job["state"]))
    else:
        conn = db.connect()
        for r in decide(conn):
            print("%-40s %-28s %-28s %s" % (r["title"][:40], (r["model"] or "no model")[:28], r["verdict"][:28],
                                           r["reason"]))
        conn.close()
