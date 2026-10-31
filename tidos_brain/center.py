"""TIDOS Center Link: the Control Center as data for the agent model in your session.

Read needs NO password and NO dashboard: every switch, job, proposal and trust score lives in ~/.tidos,
outside any repository, and pure functions over files/db read it (the orb does exactly that). What the
agent gets from center.overview() is the same data the dashboard tabs show.

center.act() is the ONLY write path an agent has, and everything else is refused:
  propose       an idea for TIDOS itself -> the evolution queue, YOU review it (dashboard / tideos center)
  run_job       one whitelisted autopilot job, only when its trust level allows running by itself
                (act_undo/act), never when the kind is paused, a job is running, or the owner is needed.
Switches, tool installs, MCP connections, community sharing, trust levels, passwords, updates apply:
OWNER ONLY, in the browser at /TIDOSZIT. This module refuses them by design - code, not prompts.

center.health() detects errors, anomalies and inconsistent states across TIDOS and the Center from the
ACTUAL Center data (read-only; it writes only its own diagnostics.json, cached by a data signature:
recomputed when the underlying data changes or once a day, never on every dashboard refresh). Diagnostic
reports carry issue id, component, description, severity, evidence, detection time, root cause,
recommended action, confidence and a status the OWNER moves (new / investigating / confirmed / resolved)
- the agent never flips production state from a diagnosis (center.act() gateways unchanged).

  python -I tidos_brain/__main__.py center           the review as text (what /tides-center shows)
  python -I tidos_brain/__main__.py center --json    machine-readable overview
  python -I tidos_brain/__main__.py center-health    diagnostic reports as text
  python -I tidos_brain/__main__.py center-act propose "title" --reason "..."
  python -I tidos_brain/__main__.py center-act run_job distill
"""
import glob
import json
import os
import sys
from datetime import datetime, timezone

if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tidos_brain import control, db, trust  # noqa: E402

VERSION = "Center Link"  # informational only; TIDOS version comes from VERSION.md


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scout_state():
    try:
        from tidos_scout import scout
        return {name: (s or {}).get("status", "") for name, s in scout.state().items()}
    except Exception:  # noqa: BLE001 - scout must never break a center read
        return {}


def _update():
    try:
        from tidos_session import updater
        return updater.status()
    except Exception:  # noqa: BLE001
        return {}


def pending(conn):
    """Everything waiting on a DECISION, grouped by who decides: owner -> the browser, agent -> here
    (the trust ladder decides which job the agent may run by itself)."""
    items = []
    s = _update()
    if s.get("target") and (s.get("staged") or {}).get("ok"):
        items.append({"what": "release update", "who": "owner",
                      "detail": "%s release %s PASSED staging here - apply (or roll back) in the control "
                                "center Jobs tab." % (s.get("bump", "release"), s.get("target"))})
    from tidos_learn import evolve
    new = [p for p in evolve.load() if p.get("status") == "new"]
    if new:
        items.append({"what": "evolution proposals", "who": "owner",
                      "detail": "%d new proposal(s): #%s (review in the Evolution tab)"
                                % (len(new), ", ".join(str(p["id"]) for p in new[:6]))})
    if control.text("share_learning") == "unasked":
        items.append({"what": "community-learning consent", "who": "owner",
                      "detail": "never answered: the Security tab asks it once (agree = share anonymous lessons)"})
    tools_proposed = [n for n, st in _scout_state().items() if st == "proposed"]
    if tools_proposed:
        items.append({"what": "tool approvals", "who": "owner",
                      "detail": "%d tool(s) proposed, not approved: %s (Tool Scout tab)" % (len(tools_proposed), ", ".join(tools_proposed[:5]))})
    # job-level recommendations ("your call", paused, failed...) are already in overview()["recommendations"]
    return items


def overview(db_path=None):
    """The control center as one dict (the dashboard tabs, data only, no secrets, no passwords)."""
    from tidos_dashboard import autopilot, jobs
    from tidos_dashboard import stats
    conn = db.connect(db_path)
    try:
        recs = autopilot.decide(conn)
        running = jobs.running()
        history = jobs.history()[-8:]
        notes = stats.notifications(conn)
        on_your_plate = [i for i in pending(conn) if i["who"] == "owner"]
        on_agent_plate = [i for i in pending(conn) if i["who"] == "agent"]
    finally:
        conn.close()
    return {"generated_at": _now(), "module": VERSION,
            "switches": {"switches": control.load(), "texts": control.texts()},
            "pending": {"owner": on_your_plate, "agent": on_agent_plate},
            "recommendations": recs,
            "jobs": {"running": running, "recent": history},
            "trust": {"levels": trust.levels(), "journal": trust.journal(limit=12)},
            "update": _update(),
            "scout_status": _scout_state(),
            "notices": notes}


# --- the only agent write path ---------------------------------------------------------------------------

REFUSED = ("switch changes", "tool installs/approvals", "MCP connections",
           "community sharing", "trust levels", "passwords", "update apply/rollback", "anything not on this list")


def act(kind, title=None, reason=None, priority="medium", job=None, params=None, _popen=None):
    """Run one agent action and return {ok, detail}. Bad kinds or wrong trust raise ValueError."""
    from tidos_dashboard import jobs

    def refuse(what):
        raise ValueError("refused (%s is owner-only, in the /TIDOSZIT browser): %s" % (what, ", ".join(REFUSED[:3])))

    if kind == "propose":
        from tidos_learn import evolve
        if not title:
            raise ValueError("propose needs a title")
        item = evolve.add(title, reason or title, priority=priority)
        try:
            trust.record("propose", "agent proposal #%d: %s" % (item["id"], title[:120]), by="agent")
        except (OSError, ValueError):
            pass
        return {"ok": True, "id": item["id"],
                "detail": "Proposal #%d is in the evolution queue for YOUR review (never applied by itself)." % item["id"]}
    if kind == "run_job":
        if job not in trust.DEFAULTS:
            raise ValueError("refused: job %r is not an autopilot job. Agent-runnable jobs: %s."
                             % (job, ", ".join(sorted(trust.DEFAULTS))))
        if jobs.running() or any(j["state"] in ("running", "cancelling") for j in jobs.history()):
            raise RuntimeError("busy: a job is already running (one at a time).")
        level, target = trust.level(job), trust.target_of(job, params or {})
        if not trust.allows_auto(job):
            raise ValueError("trust level for %s is %s (max here: propose): ask the user to run it in "
                             "the control center Jobs tab, then it earns more trust on good runs." % (job, level))
        why = trust.paused(job, target)
        if why:
            raise ValueError("autopilot pauses %s right now: %s" % (job, why))
        conn = db.connect()
        try:
            jobs.build(conn, job, params or {})  # validates job AND params before anything starts
            started = jobs.start(conn, job, params or {}, by="agent", _popen=_popen or _popen_default())
        finally:
            conn.close()
        return {"ok": True, "job_id": started["id"],
                "detail": "job %s started by the agent (by=agent, journaled #%s); log: %s"
                          % (job, started["id"], started["log"])}
    refuse("action kind %r" % kind)


def _popen_default():
    import subprocess
    return subprocess.Popen


# --- system health: read-only diagnostics over the ACTUAL Center data --------------------------------------

HEALTH_SEVERITIES = ("critical", "high", "medium", "low")
HEALTH_STATUSES = ("new", "investigating", "confirmed", "resolved")
_REPEAT_WINDOW_H = 72        # two failures of the same job inside this window: persistent, not a one-off
_STALE_RUNNING_S = 90        # grace for the pid write race between jobs.start() and its _update()
_UNSETTLED_H = 48            # open journal entries older than this: the settle loop has not run
_PROPOSAL_STALE_DAYS = 14    # a "new" proposal untouched this long is worth one low-severity ping
_HIGH_SEVERITY_JOBS = ("backup", "daily_quest", "self_update")
_LOG_HINTS = (               # needle in a job log tail -> likely root cause
    ("ModuleNotFoundError", "a dependency is missing where the job ran (check its tool/checks setup)"),
    ("SyntaxError", "broken code is what the job ran (bad edit or bad proposal)"),
    ("KeyError", "a data format the job reads changed: incompatible new/old record"),
    ("AssertionError", "a check or assertion failed: which one is visible in the log"),
    ("No space left", "the disk is full or nearly full"),
    ("Access is denied", "a Windows permission problem blocked the job"),
)


def _h_path():
    from tidos_session.detect import tidos_home
    return os.path.join(tidos_home(), "diagnostics.json")


def _load_health():
    try:
        with open(_h_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_health(data):
    os.makedirs(os.path.dirname(_h_path()), exist_ok=True)
    tmp = _h_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, _h_path())


def _age_h(iso, now=None):
    """Hours since an ISO stamp; None when missing or unparsable (never guess zero)."""
    if not iso:
        return None
    try:
        t = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return ((now or datetime.now(timezone.utc)) - t).total_seconds() / 3600.0


def _health_signature():
    """One hash over everything the rules read: the cache is valid exactly while the state is unchanged."""
    import hashlib
    from tidos_dashboard import jobs
    from tidos_session import updater
    try:
        from tidos_learn import evolve
        new_proposals = sorted(str(p["id"]) for p in evolve.load() if p.get("status") == "new")
    except Exception:  # noqa: BLE001 - an unreadable source must not invalidate the whole signature
        new_proposals = None
    blob = json.dumps({
        "jobs": [(j.get("id"), j.get("job"), j.get("state"), j.get("exit"), j.get("ended")) for j in jobs.history()[-40:]],
        "journal": len(trust.journal()),
        "proposals": new_proposals,
        "update": [updater.status().get("target"), updater.status().get("current"),
                   (updater.status().get("staged") or {}).get("at")],
        "scout": sorted(_scout_state().items()),
        "day": _now()[:10],   # time-based rules re-check at least daily
    }, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _newest_backup():
    """(path, age_hours) of the newest backup file, or None when there is none (folder state is truth:
    the backup command journals no action, so the journal alone proves nothing)."""
    try:
        from tidos_session.detect import tidos_home
        files = [f for f in glob.glob(os.path.join(tidos_home(), "backups", "*.db"))]
        if not files:
            return None
        path = max(files, key=os.path.getmtime)
        return path, (datetime.now(timezone.utc) -
                      datetime.fromtimestamp(os.path.getmtime(path), timezone.utc)).total_seconds() / 3600.0
    except OSError:
        return None


def _log_tail(log, chars=500):
    try:
        size = os.path.getsize(log) if log else 0
        if not log:
            return ""
        with open(log, "r", encoding="utf-8", errors="replace") as f:
            f.seek(max(0, size - chars))
            return f.read()
    except OSError:
        return ""


def health(force=False, db_path=None):
    """{generated_at, signature, issues: [...]} straight from the real Center data.

    READ-ONLY scan: no production file, db row, trust level or switch is touched - the only write is this
    module's own diagnostics.json. Unresolved issues keep ONE stable issue id (no duplicate alerts); an
    issue whose condition stops holding is auto-resolved on the next scan with that noted as evidence.
    """
    from tidos_dashboard import jobs
    from tidos_session import updater

    data = _load_health()
    sig = _health_signature()
    if not force and sig and data.get("signature") == sig and isinstance(data.get("issues"), list):
        return data
    now = datetime.now(timezone.utc)
    stamp = _now()
    found = {}

    def add(rule, component, description, severity, evidence, root_cause, recommended, confidence=0.85):
        found[rule] = {"id": rule, "component": component, "description": description,
                       "severity": severity, "evidence": [str(e) for e in evidence if e][:6],
                       "root_cause": root_cause, "recommended": recommended,
                       "confidence": round(float(confidence), 2), "detected_at": None,
                       "last_seen": stamp}

    def broken(name, component, exc):
        add("data_unavailable:%s" % name, component,
            "%s could not be read: a component with missing data is NOT healthy by definition, "
            "so this is reported, never assumed away." % name, "high",
            ["%s: %s" % (type(exc).__name__, str(exc)[:140])],
            "the data source is unreachable, corrupt or unreadable",
            "inspect where %s lives, fix the access problem, then re-scan "
            "(tidos_brain center-health)" % name, 0.95)

    # 1. job executions (TIDOS Center runner)
    hist = []
    try:
        with open(jobs._index_path(), "r", encoding="utf-8") as f:  # noqa: SLF001 - raw read: a corrupt
            hist = json.load(f)                                     # file must raise, history() hides it
    except FileNotFoundError:
        hist = []          # fresh install: genuinely no jobs yet (not missing data)
    except (OSError, ValueError) as e:
        broken("job history", "TIDOS Center", e)

    if isinstance(hist, list) and hist:
        single, per_job = [], {}
        for j in hist:
            if j.get("state") == "failed":
                per_job.setdefault(j.get("job"), []).append(j)
        persistent = {name for name, items in per_job.items()
                      if len(items) >= 2 and min(_age_h(i.get("ended") or i.get("started"), now) or 0
                                                 for i in items) <= _REPEAT_WINDOW_H}
        for name, items in sorted(per_job.items()):
            tail = _log_tail(items[-1].get("log"))
            hint = next((why for needle, why in _LOG_HINTS if needle in tail), "")
            ev = ["%s failed: exit %s (%s)" % (i.get("id"), i.get("exit"),
                                               i.get("ended") or i.get("started") or "?") for i in items[-3:]]
            if name in persistent:
                add("job_repeat_failed:%s" % name, "TIDOS Center",
                    "job %r failed %d time(s) inside %d h: persistent, not isolated." % (name, len(items),
                                                                                        _REPEAT_WINDOW_H),
                    "critical", ev + ["log: %s" % (items[-1].get("log") or "?")],
                    hint or "the repeated exit code stops the job the same way every time",
                    "fix the job's cause before further runs; pausing the kind is YOUR call (Jobs tab)", 0.9)
            else:
                i = items[-1]
                add("job_failed:%s" % name, "TIDOS Center",
                    "job %r failed at least once (isolated so far)." % name,
                    "high" if name in _HIGH_SEVERITY_JOBS else "medium",
                    ["%s failed: exit %s (%s)" % (i.get("id"), i.get("exit"),
                                                  i.get("ended") or i.get("started") or "?"),
                     "log: %s" % (i.get("log") or "?")],
                    hint or "not determined from the log tail",
                    "read the job log (Jobs tab), fix, rerun once to verify the fix", 0.8)
        for j in hist:
            if j.get("state") in ("running", "cancelling") and not jobs._alive(j.get("pid")) \
                    and (_age_h(j.get("started"), now) or 0) * 3600 >= _STALE_RUNNING_S:
                add("job_stale_running:%s" % j.get("id"), "TIDOS Center",
                    "job record says %r but its process is gone: inconsistent execution state." % j.get("state"),
                    "medium", ["%s (%s) started %s" % (j.get("id"), j.get("job"), j.get("started"))],
                    "the process died without the record being updated (crash or system restart)",
                    "cancel it (Jobs tab) or let the next start mark it interrupted", 0.9)
        inter = [j for j in hist if j.get("state") == "interrupted"
                 and (_age_h(j.get("started"), now) or 999) <= _REPEAT_WINDOW_H]
        if inter:
            add("jobs_interrupted", "TIDOS Center",
                "%d run(s) recorded as interrupted in the last %d h (TIDOS stopped while they ran)."
                % (len(inter), _REPEAT_WINDOW_H),
                "low" if len(inter) < 2 else "medium",
                ["%s (%s) started %s" % (j.get("id"), j.get("job"), j.get("started")) for j in inter[:3]],
                "a restart or crash without data-corruption evidence",
                "accept or re-run; the trust ladder already marked these runs as not-good", 0.8)

    # 2. the trust journal (TIDOS <-> Center action settlement loop)
    journal = None
    try:
        journal = trust.journal(limit=300)
    except (OSError, ValueError) as e:
        broken("trust journal", "TIDOS Center", e)
    if journal is not None:
        agent_hour = [i for i in journal if i.get("by") == "agent" and (_age_h(i.get("at"), now) or 999) <= 1]
        if len(agent_hour) >= 5:
            add("agent_activity_rate", "TIDOS Center",
                "%d agent actions in the last hour: unusual activity rate." % len(agent_hour),
                "medium", ["%s for %s? %s" % (i.get("kind"), i.get("job_id"), i.get("title", "")[:70])
                           for i in agent_hour[:5]],
                "heavy Center Link use in one session or something else acting as the agent",
                "expected while the agent works heavily; otherwise review the journal (Security tab)", 0.7)
        unsettled = [i for i in journal if i.get("state") == "open" and i.get("job_id")
                     and (_age_h(i.get("at"), now) or 0) >= _UNSETTLED_H]
        if unsettled:
            add("journal_unsettled", "TIDOS Center",
                "%d finished action(s) were never settled after %d h: the settle loop did not run."
                % (len(unsettled), _UNSETTLED_H),
                "low" if len(unsettled) < 5 else "medium",
                ["action #%s (%s) open since %s" % (i.get("id"), i.get("kind"), i.get("at"))
                 for i in unsettled[:4]],
                "TIDOS/START (where trust.settle() runs) has been closed since then",
                "run START TIDOS once, or a daily-quest run which settles at its end; "
                "no trust has moved, nothing else is wrong yet", 0.85)

    # 3. proposals / evolution queue (inconsistencies between proposals and system state)
    proposals = None
    try:
        from tidos_learn import evolve
        proposals = evolve.load()
    except (OSError, ValueError) as e:
        broken("evolution queue", "TIDOS", e)
    if proposals is not None:
        stale = [p for p in proposals if p.get("status") == "new"
                 and (_age_h(p.get("at"), now) or 0) >= _PROPOSAL_STALE_DAYS * 24]
        if stale:
            add("proposals_stale", "TIDOS Center",
                "%d new proposal(s) untouched for %d+ days: they neither got decided nor implemented."
                % (len(stale), _PROPOSAL_STALE_DAYS), "low",
                ["proposal #%s %r from %s" % (p.get("id"), p.get("title", "")[:60], p.get("at"))
                 for p in stale[:4]],
                "a queued idea nobody decided on",
                "accept or reject them (Evolution tab); nobody but you decides content", 0.9)

    # 4. release staging: passed but waiting too long = inconsistent state (staged release vs running one)
    st = updater.status()
    staged = st.get("staged") or {}
    staged_h = _age_h(staged.get("at"), now)
    if st.get("target") and staged.get("ok") and staged_h is not None and staged_h >= 24 * 7:
        add("update_staged_week", "TIDOS",
            "release %s passed the gates %d day(s) ago and is still not applied or rolled back."
            % (st.get("target"), int(staged_h // 24)), "medium",
            ["target: %s" % (st.get("target") or "?"), "staged ok at %s" % staged.get("at"),
             "current: %s" % (st.get("current") or "?")],
            "a safe release passed every gate and nobody made the apply/rollback decision",
            "apply the release or roll back (Jobs / Update tab)", 0.9)

    # 5. safety data that should exist (missing data is NEVER proof of health)
    if journal is not None:
        newest_backup = _newest_backup()  # the backups folder is ground truth; the journal is just one path
        conn = None
        try:
            conn = db.connect(db_path)
            tasks_n = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        except Exception as e:  # noqa: BLE001
            broken("brain database", "TIDOS", e)
        finally:
            if conn is not None:
                conn.close()
        if conn is not None and tasks_n and not any(i.get("kind") == "backup" for i in journal) \
                and not newest_backup:
            add("backup_never", "TIDOS", "%d session task(s) recorded but no backup was ever taken: "
                "safety-critical data has no copy." % tasks_n, "medium",
                ["tasks: %d" % tasks_n, "backup actions in journal: 0", "backup files: 0"],
                "the backup job was never run once",
                "run the backup job once (Jobs tab), then its trust ladder may automate it", 0.9)

    # 6. security events (communication between TIDOS and the Center: logins, sanitizer, updates)
    security_path = db_path or db.default_path()
    if security_path != ":memory:" and os.path.exists(security_path):
        conn = None
        try:
            conn = db.connect(db_path)
            rows = conn.execute("SELECT ts, event, detail FROM security_log ORDER BY id DESC LIMIT 60").fetchall()
        except Exception as e:  # noqa: BLE001
            rows, e2 = None, e
        finally:
            if conn is not None:
                conn.close()
        if rows is not None:
            bad = [r for r in rows if (_age_h(r["ts"], now) or 999) <= 24
                   and r["event"] in ("login_fail", "lockout", "sanitizer_block", "update_refused")]
            if bad:
                add("security_events", "TIDOS Center",
                    "%d security event(s) in the last 24 h: %s." % (len(bad), ", ".join(sorted({r["event"] for r in bad}))),
                    "critical" if any(r["event"] == "lockout" for r in bad) else "high",
                    ["%s %s: %s" % (r["ts"], r["event"], (r["detail"] or "")[:80]) for r in bad[:5]],
                    "failed sign-ins or data the sanitizer refused: real attempts or broken input",
                    "Security tab for the event list; repeated login_fail means real attempts", 0.9)
        else:
            broken("security log", "TIDOS Center", e2)

    # merge with every previously seen issue (stable ids, owner statuses preserved)
    merged = {}
    for old in (data.get("issues") or []):
        if isinstance(old, dict) and old.get("id"):
            merged[old["id"]] = dict(old)
    for key in list(merged):
        old = merged[key]
        if old.get("status") != "resolved" and key not in found:
            old["status"] = "resolved"
            old["resolved_at"] = stamp
            old["root_cause"] = (old.get("root_cause") or "not determined") + \
                                " (auto-resolved: the condition no longer holds at the last scan)"
    # 7. reopen on reappearance: a resolved issue found again is a NEW alert, not a duplicate of the old one
    for key, item in found.items():
        old = merged.get(key)
        if old and old.get("status") != "resolved":
            item.update(first_seen=old.get("first_seen") or old.get("detected_at") or old.get("last_seen") or stamp,
                        status=old.get("status", "new"), times_seen=(old.get("times_seen") or 1) + 1)
        else:
            item.update(first_seen=stamp, status="new", times_seen=(old.get("times_seen") or 0) + 1
                        if old else 1)
        merged[key] = item
    issues = sorted(merged.values(), key=lambda i: (HEALTH_SEVERITIES.index(i.get("severity", "low")),
                                                    str(i.get("id"))))[-200:]
    out = {"generated_at": stamp, "signature": sig, "count": len([i for i in issues if i.get("status") != "resolved"]),
           "issues": issues}
    _save_health(out)
    return out


def health_set(issue_id, status):
    """OWNER action from the browser: move one diagnostic report's status. Evidence is never rewritten."""
    if status not in HEALTH_STATUSES:
        raise ValueError("status must be one of %s" % ", ".join(HEALTH_STATUSES))
    data = _load_health()
    item = next((i for i in (data.get("issues") or [])
                 if isinstance(i, dict) and i.get("id") == issue_id), None)
    if item is None:
        raise KeyError(issue_id)
    item["status"] = status
    if status == "resolved":
        item["resolved_at"] = _now()
    _save_health(data)
    return item


def health_text():
    """The diagnostic reports the agent reports in the session (compact)."""
    h = health()
    open_ = [i for i in h.get("issues", []) if i.get("status") != "resolved"]
    resolved = [i for i in h.get("issues", []) if i.get("status") == "resolved"]
    lines = ["# TIDOS system health (%s), %d open, %d resolved today+"
             % (h["generated_at"][:19].replace("T", " "), len(open_), len(resolved))]
    if not open_:
        lines.append("- no open issue found in the actual Center data (nothing assumed away: unreadable "
                     "sources are reported above as data_unavailable)")
    for i in open_[:8]:
        lines.append("- [%s/%s] %s (%s)" % (i["severity"], i["status"], i["id"], i["component"]))
        lines.extend("    * %s" % w for w in
                     ("what: %s" % i["description"], "cause: %s (confidence %s)" % (i["root_cause"], i["confidence"]),
                      "evidence: %s" % (i["evidence"][0] if i["evidence"] else "none"),
                      "recommend: %s" % i["recommended"],
                      "seen %d x since %s" % (i.get("times_seen", 1), i.get("first_seen", i["last_seen"]))))
    if resolved:
        lines.append("- resolved (last 5): %s" % ", ".join("%s (%s)" % (r["id"], r["status"]) for r in resolved[-5:]))
    lines.append("- a diagnosis never changes production: I may fix code only as a TASK you asked for,"
                 " other corrective actions wait for your click in /TIDOSZIT (Agent Review tab).")
    return "\n".join(lines) + "\n"


# --- the review text ---------------------------------------------------------------------------------------

HOW_TO_ACT = ("Read-only Center Link: switch changes, installs, connections, trust and updates stay in the "
              "browser (/TIDOSZIT). The agent can: tideos center-act propose \"<title>\" --reason \"...\" "
              "or center-act run_job <job> when its trust level allows running by itself.")


def report(project=None):
    """The /tidos-center review text the model shows the user (compact, prioritized, honest)."""
    from tidos_dashboard import stats

    t = overview()
    lines = ["# TIDOS Center review (%s)" % t["generated_at"][:19].replace("T", " ")]

    ver = "(version: %s)" % t["update"].get("current") if t["update"].get("current") else ""
    plates = [t["pending"]["owner"], t["pending"]["agent"]]
    lines.append("- Pending: %d on you, %d on the agent. Switches: %s.%s"
                 % (len(plates[0]), len(plates[1]),
                    ", ".join("%s=%s" % (k, "on" if v else "OFF") for k, v in sorted(t["switches"]["switches"].items())
                              if not v) or "all default switches on", ver))
    for who, plate in (("YOURS (decide in /TIDOSZIT browser)", plates[0]), ("AGENT (I can act, see below)", plates[1])):
        lines.append("- %s:" % who)
        if plate:
            lines.extend("    * %s: %s" % (i["what"], i["detail"]) for i in plate[:6])
        else:
            lines.append("    * none")

    r = t["recommendations"]
    if r:
        lines.append("- Recommended now (%d):" % len(r))
        lines.extend("    * %s [%s] - %s" % (x["title"], x.get("verdict", ""), x["reason"]) for x in r[:6])
    job = t["jobs"]["running"]
    if job:
        lines.append("- Job running: %s (started %s)" % (job["title"], job["started"]))
    on_trust = [l for l in t["trust"]["levels"] if l["level"] != "act" and l["streak"]]
    if on_trust:
        lines.append("- Trust ladder: %s" % ", ".join("%s at %s (streak %d%s)"
                     % (l["kind"], l["level"], l["streak"], ", pinned" if l["pinned"] else "") for l in on_trust[:5]))
    if t["notices"]:
        lines.append("- Notices:")
        lines.extend("    * [%s] %s" % (n.get("level", "?"), n.get("text", "")) for n in t["notices"][:6])
    try:
        hh = health()
        live = [i for i in hh.get("issues", []) if i.get("status") != "resolved"]
        if live:
            lines.append("- System health: %d open issue(s), worst %s [%s]: %s (tideos-brain center-health)"
                         % (len(live), live[0]["severity"], live[0]["id"], live[0]["description"][:110]))
            for i in live[1:4]:
                lines.append("    * [%s] %s: %s" % (i["severity"], i["id"], i["description"][:100]))
    except Exception:  # noqa: BLE001 - health must never break the review
        pass
    lines.append("- %s" % HOW_TO_ACT)
    return "\n".join(lines) + "\n"
