"""Center system-health tests: detection from the REAL Center data, dedupe, owner statuses, read-only."""
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import center, cli, db  # noqa: E402
from tidos_dashboard import jobs  # noqa: E402

NOW = datetime.now(timezone.utc)


def iso(**kw):
    return (NOW - timedelta(**kw)).isoformat(timespec="seconds")


def digest(path):
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except OSError:
        return None


class Isolated(unittest.TestCase):
    """Every TIDOS-side file/db lives in a temp home: fixtures, then center.health() truth checks."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        os.makedirs(os.path.join(self.home, ".tidos", "jobs"))
        self.tidos = os.path.join(self.home, ".tidos")
        self.jobs_index = os.path.join(self.tidos, "jobs", "index.json")
        self.patches = [
            mock.patch.dict(os.environ, {
                "TIDOS_HOME_DIR": self.tidos,
                "TIDOS_BRAIN_DB": os.path.join(self.tmp.name, "brain.db"),
                "TIDOS_UPDATE_TEST_URL": "x://forbidden",  # any updater state read stays local
            }),
            mock.patch.object(os.path, "expanduser", lambda p: p.replace("~", self.home, 1)
                              if p.startswith("~") else os.path.expanduser(p)),
        ]
        for p in self.patches:
            p.start()
        self.log_path = self.write_jobs([])  # creates the index file once

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        import time
        for _ in range(10):  # a just-finished thread may hold a temp file a moment
            try:
                self.tmp.cleanup()
                break
            except PermissionError:
                time.sleep(0.2)

    def write_jobs(self, records):
        with open(self.jobs_index, "w", encoding="utf-8") as f:
            json.dump(records, f)
        return os.path.join(self.tidos, "jobs", "w.log")

    def write_journal(self, items):
        with open(os.path.join(self.tidos, "actions.jsonl"), "w", encoding="utf-8") as f:
            for i in items:
                f.write(json.dumps(i) + "\n")

    def issue(self, data, rule_id):
        return next((i for i in data["issues"] if i["id"] == rule_id), None)


class JobFailureTests(Isolated):
    def test_1_single_failure_is_a_reported_issue_with_severity_class(self):
        self.write_jobs([{"id": "j1", "job": "raid", "state": "failed", "exit": 2, "by": "owner",
                          "title": "Weekly raid", "started": iso(hours=2), "ended": iso(hours=1),
                          "log": self.log_path}])
        h = center.health(force=True)
        issue = self.issue(h, "job_failed:raid")
        self.assertIsNotNone(issue)
        self.assertEqual(issue["severity"], "medium")          # generic single failure, classed
        self.assertEqual(issue["component"], "TIDOS Center")
        self.assertIn("exit 2", issue["evidence"][0])
        self.assertEqual(issue["status"], "new")
        self.assertLessEqual(issue["confidence"], 1.0)
        for field in ("description", "root_cause", "recommended", "detected_at", "last_seen", "first_seen"):
            self.assertTrue(field in issue)

    def test_1_high_severity_kinds(self):
        self.write_jobs([{"id": "j2", "job": "backup", "state": "failed", "exit": 3, "by": "owner",
                          "title": "Back up the brain", "started": iso(hours=3), "ended": iso(hours=3),
                          "log": self.log_path}])
        self.assertEqual(self.issue(center.health(force=True), "job_failed:backup")["severity"], "high")

    def test_2_repeated_failures_inside_the_window_are_critical_persistent(self):
        self.write_jobs([
            {"id": "j3a", "job": "daily_quest", "state": "failed", "exit": 1, "by": "autopilot",
             "title": "quest", "started": iso(hours=40), "ended": iso(hours=40), "log": self.log_path},
            {"id": "j3b", "job": "daily_quest", "state": "failed", "exit": 1, "by": "autopilot",
             "title": "quest", "started": iso(hours=6), "ended": iso(hours=6), "log": self.log_path},
        ])
        h = center.health(force=True)
        issue = self.issue(h, "job_repeat_failed:daily_quest")
        self.assertEqual(issue["severity"], "critical")
        self.assertIn("persistent", issue["description"])
        self.assertEqual(len([i for i in h["issues"] if "daily_quest" in i["id"]]), 1)  # no double alert

    def test_repeated_outside_the_window_stays_isolated_severity(self):
        self.write_jobs([
            {"id": "j4a", "job": "raid", "state": "failed", "exit": 1, "by": "owner", "title": "r",
             "started": iso(days=30), "ended": iso(days=30), "log": self.log_path},
            {"id": "j4b", "job": "raid", "state": "failed", "exit": 1, "by": "owner", "title": "r",
             "started": iso(days=29), "ended": iso(days=29), "log": self.log_path},
        ])
        self.assertEqual(self.issue(center.health(force=True), "job_failed:raid")["severity"], "medium")


class InconsistentStateTests(Isolated):
    def test_3_stale_running_record_contradicts_the_dead_process(self):
        self.write_jobs([{"id": "j5", "job": "distill", "state": "running", "by": "owner", "title": "d",
                          "started": iso(hours=2), "ended": None, "exit": None, "log": self.log_path}])
        issue = self.issue(center.health(force=True), "job_stale_running:j5")
        self.assertIsNotNone(issue)
        self.assertEqual(issue["severity"], "medium")
        self.assertIn("inconsistent", issue["description"])

    def test_3_unsettled_journal_after_48h(self):
        self.write_jobs([{"id": "j6", "job": "distill", "state": "done", "exit": 0, "by": "owner",
                          "title": "d", "started": iso(days=4), "ended": iso(days=4), "log": self.log_path}])
        self.write_journal([
            {"id": 1, "at": iso(days=4), "kind": "distill", "title": "d", "by": "owner", "job_id": "j6",
             "state": "open", "undoable": False},
        ])
        issue = self.issue(center.health(force=True), "journal_unsettled")
        self.assertIsNotNone(issue)
        self.assertEqual(issue["severity"], "low")
        self.assertIn("settled", issue["description"])

    def test_agent_activity_rate_is_flagged_not_secreted(self):
        self.write_journal([{"id": k, "at": iso(minutes=10), "kind": "distill", "title": "x", "by": "agent",
                             "state": "open", "undoable": False} for k in range(1, 6)])
        issue = self.issue(center.health(force=True), "agent_activity_rate")
        self.assertEqual(issue["severity"], "medium")

    def test_proposals_waiting_for_weeks_are_reported(self):
        from tidos_learn import evolve
        item = evolve.add("old idea", "why")           # writes the real queue file
        items = []
        path = os.path.join(self.tidos, "proposals.jsonl")
        with open(path, "r", encoding="utf-8") as f:
            items = [json.loads(l) for l in f if l.strip()]
        items[0]["at"] = iso(days=20)
        with open(path, "w", encoding="utf-8") as f:
            for i in items:
                f.write(json.dumps(i) + "\n")
        h = center.health(force=True)
        issue = self.issue(h, "proposals_stale")
        self.assertIsNotNone(issue)
        self.assertIn(str(item["id"]), issue["evidence"][0])


class MissingDataTests(Isolated):
    def test_6_unreadable_job_history_is_high_never_assumed_healthy(self):
        with open(self.jobs_index, "w", encoding="utf-8") as f:
            f.write("{corrupt json")
        h = center.health(force=True)
        issue = self.issue(h, "data_unavailable:job history")
        self.assertEqual(issue["severity"], "high")
        self.assertIn("NOT healthy", issue["description"])

    def test_6_no_backup_with_recorded_work_is_medium(self):
        conn = db.connect()
        try:
            sid = "sess-health"
            conn.execute("INSERT INTO sessions (id, source, title, project, model, started_at) "
                         "VALUES (?, 'api', 's', 'p', 'm', ?)", (sid, iso(hours=5)))
            conn.execute("INSERT INTO tasks (session_id, seq, prompt) VALUES (?, 1, 'work')", (sid,))
            conn.commit()
        finally:
            conn.close()
        self.write_journal([{"id": 1, "at": iso(hours=1), "kind": "distill", "title": "d", "by": "owner",
                             "state": "kept", "undoable": False}])
        issue = self.issue(center.health(force=True), "backup_never")
        self.assertIsNotNone(issue)
        self.assertEqual(issue["severity"], "medium")

    def test_4_security_event_classification(self):
        conn = db.connect()
        try:
            conn.execute("INSERT INTO security_log (ts, event, detail) VALUES (?, 'lockout', 'x')", (iso(hours=2),))
            conn.commit()
        finally:
            conn.close()
        self.write_journal([])
        issue = self.issue(center.health(force=True), "security_events")
        self.assertEqual(issue["severity"], "critical")   # lockout is the worst within 24 h

    def test_6_a_real_backup_file_clears_the_issue_even_without_a_journal_action(self):
        conn = db.connect()
        try:
            sid = "sess-health2"
            conn.execute("INSERT INTO sessions (id, source, title, project, model, started_at) "
                         "VALUES (?, 'api', 's', 'p', 'm', ?)", (sid, iso(hours=5)))
            conn.execute("INSERT INTO tasks (session_id, seq, prompt) VALUES (?, 1, 'work')", (sid,))
            conn.commit()
        finally:
            conn.close()
        self.write_journal([{"id": 1, "at": iso(hours=1), "kind": "distill", "title": "d", "by": "owner",
                             "state": "kept", "undoable": False}])
        os.makedirs(os.path.join(self.tidos, "backups"), exist_ok=True)
        with open(os.path.join(self.tidos, "backups", "brain-1.db"), "w", encoding="utf-8") as f:
            f.write("x")                                     # like the /tideos-backup command's db copy
        self.assertIsNone(self.issue(center.health(force=True), "backup_never"))

    def test_4_update_staged_and_untouched_for_a_week(self):
        from tidos_session import updater
        updater._save(target="v9.9.0", bump="minor", current_tag="v9.8.9",
                      staged={"ok": True, "gates": [], "log": "l", "at": iso(days=10)})
        issue = self.issue(center.health(force=True), "update_staged_week")
        self.assertEqual(issue["severity"], "medium")


class DedupeAndCacheTests(Isolated):
    def test_5_one_stable_id_times_seen_grows_no_duplicates(self):
        self.write_jobs([{"id": "j7", "job": "raid", "state": "failed", "exit": 2, "by": "owner", "title": "x",
                          "started": iso(hours=1), "ended": iso(minutes=50), "log": self.log_path},
                         {"id": "j8", "job": "raid", "state": "failed", "exit": 2, "by": "owner", "title": "x",
                          "started": iso(minutes=40), "ended": iso(minutes=30), "log": self.log_path}])
        first = center.health(force=True)
        again = center.health(force=True)
        ids = [i["id"] for i in again["issues"]]
        self.assertEqual(len(ids), len(set(ids)))               # no duplicate alerts
        rep = self.issue(again, "job_repeat_failed:raid")
        self.assertEqual(rep["times_seen"], 2)                  # same issue re-counted, not re-created
        self.assertEqual(first["generated_at"], again["generated_at"])  # force re-scan keeps the identity

    def test_cache_recompute_only_when_signature_changes(self):
        self.write_jobs([{"id": "j9", "job": "raid", "state": "failed", "exit": 2, "by": "owner", "title": "x",
                          "started": iso(hours=1), "ended": iso(hours=1), "log": self.log_path}])
        first = center.health(force=True)
        cached = center.health()                                # unchanged data -> cached dict returned
        self.assertEqual(cached["generated_at"], first["generated_at"])
        rec = json.load(open(self.jobs_index, encoding="utf-8"))
        rec[0]["state"] = "done"
        rec[0]["id"] = "j9b"
        self.write_jobs(rec)
        fresh = center.health()                                 # signature changed: real re-scan
        self.assertNotEqual(fresh["signature"], first["signature"])
        self.assertEqual(self.issue(fresh, "job_failed:raid")["status"], "resolved")  # scan saw the new state

    def test_auto_resolve_records_that_the_condition_stopped_holding(self):
        self.write_jobs([{"id": "j10", "job": "raid", "state": "failed", "exit": 2, "by": "owner", "title": "x",
                          "started": iso(hours=1), "ended": iso(hours=1), "log": self.log_path}])
        h = center.health(force=True)
        self.assertIsNotNone(self.issue(h, "job_failed:raid"))
        self.write_jobs([])                                     # the failure is gone from the real data
        safe = center.health(force=True)
        issue = self.issue(safe, "job_failed:raid")
        self.assertEqual(issue["status"], "resolved")
        self.assertIn("auto-resolved", issue["root_cause"])


class ReadOnlyAndOwnerTests(Isolated):
    PROD_FILES = ("jobs/index.json", "actions.jsonl", "trust.json", "control.json",
                  "proposals.jsonl", "update.json", "brain.db")

    def test_7_the_health_pass_never_modifies_the_evidence_it_uses(self):
        self.write_jobs([{"id": "j11", "job": "raid", "state": "failed", "exit": 2, "by": "owner", "title": "x",
                          "started": iso(days=1), "ended": iso(days=1), "log": self.log_path}])
        self.write_journal([{"id": 1, "at": iso(days=1), "kind": "raid", "title": "r", "by": "owner",
                             "job_id": "j11", "state": "open", "undoable": False}])
        from tidos_session import updater
        updater._save(target="v1.2.3", bump="patch", current_tag="v1.2.2",
                      staged={"ok": True, "at": iso(days=9)})
        conn = db.connect()
        try:
            conn.execute("INSERT INTO security_log (ts, event, detail) VALUES (?, 'login_fail', 'x')", (iso(hours=1),))
            conn.commit()
        finally:
            conn.close()
        before = {f: digest(os.path.join(self.tidos, f)) for f in self.PROD_FILES}
        h = center.health(force=True)
        after = {f: digest(os.path.join(self.tidos, f)) for f in self.PROD_FILES}
        self.assertEqual(before, after)                    # production/data files untouched, byte for byte
        self.assertTrue(os.path.exists(os.path.join(self.tidos, "diagnostics.json")))  # only its own cache
        ev = self.issue(h, "security_events")["evidence"]
        center.health_set("security_events", "investigating")
        self.assertEqual(self.issue(center._load_health(), "security_events")["evidence"], ev)
        center.health_set("security_events", "resolved")
        final = self.issue(center._load_health(), "security_events")
        self.assertEqual((final["status"], final["evidence"]), ("resolved", ev))

    def test_8_health_set_is_owner_only_and_validated(self):
        self.write_jobs([])
        center.health(force=True)
        with self.assertRaises(KeyError):
            center.health_set("no_such", "resolved")
        with self.assertRaises(ValueError):
            center.health_set("anything", "apply_release")   # production-ish statuses do not exist here

    def test_8_act_gateways_untouched_by_health(self):
        from tidos_dashboard import jobs
        # the health module shares no write path with act(): switching/installs/etc stay owner-only
        with self.assertRaises(ValueError):
            center.act("resolve", title="x")
        with self.assertRaises(ValueError) as cm:
            center.act("run_job", job="resolve")
        self.assertIn("not an autopilot job", str(cm.exception))
        self.assertIsNone(jobs.running())
        self.assertEqual(os.path.join(self.tidos, "diagnostics.json"),
                         center._h_path().replace("/", os.sep) if os.sep == "/" else center._h_path())


class CliAndDashboardTests(Isolated):
    def test_9_cli_center_health(self):
        self.write_jobs([{"id": "j12", "job": "raid", "state": "failed", "exit": 2, "by": "owner", "title": "x",
                          "started": iso(hours=1), "ended": iso(hours=1), "log": self.log_path}])
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = cli.main(["center-health"])
        self.assertEqual(code, 0)
        self.assertIn("TIDOS system health", out.getvalue())
        self.assertIn("job_failed:raid", out.getvalue())
        self.assertIn("medium", out.getvalue())
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = cli.main(["center-health", "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(out.getvalue())
        self.assertTrue(payload["signature"])
        self.assertIn("job_failed:raid", [i["id"] for i in payload["issues"]])

    def test_9_dashboard_route_serves_and_owner_moves_the_status(self):
        import http.client
        import threading
        from tidos_dashboard import firebase, server

        class FB:
            FirebaseError = firebase.FirebaseError

            def __init__(self):
                self.doc = None

            def lookup_user(self, cfg, token):
                if token != "owner-token":
                    raise firebase.FirebaseError("bad", 400)
                return {"localId": "OWN", "email": "owner@example.com"}

            def get_password_doc(self, cfg, token, path="admin/tidos"):
                return self.doc

            def set_password_doc(self, cfg, token, record, path="admin/tidos"):
                self.doc = record

        cfg = {"projectId": "p", "apiKey": "k", "authDomain": "p.firebaseapp.com", "appId": "a", "ownerUid": "OWN"}
        srv = server.ControlServer(port=0, cfg=cfg, db_path=os.path.join(self.tmp.name, "dash.db"), fb=FB())
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        cookies = {}

        def call(method, path, body=None):
            c = http.client.HTTPConnection("127.0.0.1", srv.port, timeout=10)
            headers = {"Host": "localhost:%d" % srv.port, "Origin": "http://localhost:%d" % srv.port}
            if body is not None:
                headers["Content-Type"] = "application/json"
            if cookies:
                headers["Cookie"] = "; ".join("%s=%s" % kv for kv in cookies.items())
            c.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
            r = c.getresponse()
            for h, v in r.getheaders():
                if h.lower() == "set-cookie":
                    cookies[v.split(";", 1)[0].split("=", 1)[0]] = v.split(";", 1)[0].split("=", 1)[1]
            payload = json.loads(r.read())
            c.close()
            return r.status, payload

        self.assertEqual(call("POST", "/api/auth/google", {"idToken": "owner-token"})[1]["stage"], "setup")
        self.assertEqual(call("POST", "/api/auth/setup", {"password": "Str0ng-Passw0rd!"})[0], 200)
        self.write_jobs([{"id": "j13", "job": "raid", "state": "failed", "exit": 2, "by": "owner", "title": "x",
                          "started": iso(hours=1), "ended": iso(hours=1), "log": self.log_path}])
        center.health(force=True, db_path=os.path.join(self.tmp.name, "dash.db"))
        code, data = call("GET", "/api/center")
        self.assertEqual(code, 200)
        self.assertIn("health", data)
        issues = data["health"]["issues"]
        self.assertEqual(issues[0]["id"], "job_failed:raid")     # served on the real tab data
        iid = issues[0]["id"]
        status = dict((i["id"], i["status"]) for i in issues)
        self.assertEqual(status[iid], "new")
        self.assertEqual(call("POST", "/api/center/diag", {"id": iid, "status": "investigating"})[0], 200)
        fresh = call("GET", "/api/center")[1]["health"]["issues"]
        self.assertEqual(next(i["status"] for i in fresh if i["id"] == iid), "investigating")
        self.assertEqual(call("POST", "/api/center/diag", {"id": iid, "status": "apply_release"})[0], 400)
        self.assertEqual(call("POST", "/api/center/diag", {"id": "nope", "status": "new"})[0], 404)
        srv.shutdown()
        srv.server_close()


if __name__ == "__main__":
    unittest.main()
