"""Autopilot: TIDOS decides what to run next, and runs it when the `autopilot` switch is on.

decide() looks at the brain and the files and returns recommendations, each with its reason and cost:
  - refresh learning        when the last refresh is older than 6 h                      free, auto
  - daily quest             when today has no report                                     free, auto
  - back up the brain       when the newest backup is older than 7 days                  free, auto
  - trial a draft unit      when a draft has no trial and a dungeon suite tests it       paid, auto within budget
  - implement a proposal    when you accepted it and it has no branch yet                paid, auto within budget
  - weekly weak-model check GUIDE vs plain with a free OpenCode model (plan 6.8)         free, auto, weekly
  - tool needs              per active project (installing still needs your approval)    free, shown only
Rules: one job at a time; paid jobs only while today's autopilot spend + the estimate stays within
autopilot_budget_usd; a job that failed in the last 24 h is not retried automatically; nothing here installs,
pushes, merges, activates a unit or changes a switch: those stay yours.

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

from tidos_brain import control, db  # noqa: E402
from tidos_dashboard import jobs  # noqa: E402
from tidos_session.detect import tidos_home  # noqa: E402

LEARN_EVERY = timedelta(hours=6)
BACKUP_EVERY = timedelta(days=7)
WEAK_CHECK_EVERY = timedelta(days=7)
RETRY_AFTER = timedelta(hours=24)
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


def decide(conn):
    recs = []

    def add(key, job, params, title, reason, auto=True):
        try:
            _, _, estimate, _ = jobs.build(conn, job, params)
        except jobs.JobError:
            return
        recs.append({"key": key, "job": job, "params": params, "title": title, "reason": reason,
                     "estimate": estimate, "auto": auto})

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

    from tidos_learn import army, evolve
    trials = army.load_state().get("trials", {})
    for name, u in sorted(army.units().items()):
        suite = jobs.unit_suite(name)
        if u["state"] == "draft" and name not in trials and suite:
            add("trial:" + name, "trial", {"unit": name, "agent": "claude:haiku", "suite": suite},
                "Trial %s" % name, "draft unit, never tested: %s dungeons with and without it" % suite)
    for item in evolve.load():
        if item["status"] == "accepted" and not item.get("branch"):
            add("self_improve:%d" % item["id"], "self_improve", {"id": item["id"]}, "Implement proposal #%d" % item["id"],
                "you accepted it: %s" % item["title"][:80])

    weak = [a for a in jobs.allowed_agents(conn) if a.startswith("opencode:")]
    if weak:
        agent = weak[0]
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
    budget = control.values()["autopilot_budget_usd"]
    left = round(budget - jobs.spent_today(), 2)
    for r in recs:
        if not r["auto"]:
            r["verdict"] = "your call"
        elif _recently_failed(r["job"], r["params"]):
            r["auto"], r["verdict"] = False, "failed in the last 24 h: run it yourself after a look at its log"
        elif r["estimate"] > left:
            r["auto"], r["verdict"] = False, "over today's budget (%.2f left of %.2f USD)" % (max(left, 0), budget)
        else:
            r["verdict"] = "autopilot will run it" if on else "autopilot is off"
    return recs


def tick(conn, db_path=None, log=None):
    """One autopilot step: start the first due auto job. Returns the job record or None."""
    if not control.is_on("autopilot") or jobs.running():
        return None
    for r in decide(conn):
        if r["auto"]:
            record = jobs.start(conn, r["job"], r["params"], by="autopilot", db_path=db_path)
            if log:
                log("autopilot", "%s (%s, est. %.2f USD)" % (record["title"], r["reason"][:80], r["estimate"]))
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
            print("%-40s %-6s %-28s %s" % (r["title"][:40], "$%.2f" % r["estimate"] if r["estimate"] else "free",
                                          r["verdict"][:28], r["reason"]))
        conn.close()
