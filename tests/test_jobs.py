"""Tests for dashboard jobs (buttons instead of commands) and the autopilot (TIDOS decides what to run)."""
import os
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import control, db  # noqa: E402
from tidos_dashboard import autopilot, jobs  # noqa: E402
from tidos_learn import evolve  # noqa: E402
from test_learn import add_session  # noqa: E402

PY = sys.executable


def wait_done(job_id, timeout=30):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = jobs.get(job_id)
        if job and job["state"] not in ("running", "cancelling"):
            return job
        time.sleep(0.1)
    raise AssertionError("job did not finish")


class JobsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [mock.patch.dict(os.environ, {
            "TIDOS_HOME_DIR": os.path.join(self.tmp.name, "home"),
            "TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")})]
        for p in self.patches:
            p.start()
        self.conn = db.connect(":memory:")
        add_session(self.conn, "s", self.tmp.name, "APP", "claude-opus-5-5", [("fix it", "success", 1, 0, [], [])])
        self.conn.execute("INSERT INTO sessions (id, source, model, cwd, project) VALUES "
                          "('oc', 'opencode', 'opencode/big-pickle', ?, 'APP')", (self.tmp.name,))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_only_known_jobs_and_values(self):
        for job, params in (("rm", {}), ("raid", {"agent": "claude:opus; rm -rf /"}), ("raid", {"suite": "../x"}),
                            ("raid", {"mode": "evil"}), ("trial", {"unit": "nobody"}), ("self_improve", {"id": 99}),
                            ("scout_needs", {"project": "C:/Windows"})):
            with self.assertRaises(jobs.JobError, msg=(job, params)):
                jobs.build(self.conn, job, params)
        argv, env, estimate, title = jobs.build(self.conn, "raid", {"agent": "opencode:opencode/big-pickle",
                                                                    "mode": "compare", "min_difficulty": "A"})
        self.assertEqual(argv[0], PY)
        self.assertIn("opencode:opencode/big-pickle", argv)
        self.assertEqual(estimate, 0.0)                             # free model
        argv, _, estimate, _ = jobs.build(self.conn, "trial", {"unit": "tidos-tester", "agent": "claude:haiku",
                                                               "suite": "python"})
        self.assertEqual(argv[argv.index("--budget") + 1], str(jobs.ATTEMPT_BUDGET_USD))  # hard cap per attempt
        self.assertGreater(estimate, 0)
        with mock.patch("tidos_brain.claude_code.is_synthetic", lambda cwd: False):  # temp dirs count as test runs
            self.assertEqual(jobs.build(self.conn, "scout_needs", {"project": self.tmp.name})[0][-2], self.tmp.name)
        item = evolve.add("x", "y")
        evolve.set_status(item["id"], "accepted")
        self.assertIn("--id", jobs.build(self.conn, "self_improve", {"id": item["id"]})[0])

    def fake(self, code):
        return mock.patch.object(jobs, "build", lambda conn, job, p: ([PY, "-c", code], {}, 0.0, "fake " + job))

    def test_run_log_busy_and_cancel(self):
        with self.fake("print('hello from the job')"):
            record = jobs.start(self.conn, "distill")
        done = wait_done(record["id"])
        self.assertEqual((done["state"], done["exit"]), ("done", 0))
        self.assertIn("hello from the job", jobs.log_text(record["id"])["text"])
        with self.fake("import time; time.sleep(30)"):
            slow = jobs.start(self.conn, "distill")
            with self.assertRaises(RuntimeError):                   # one job at a time
                jobs.start(self.conn, "distill")
        self.assertTrue(jobs.cancel(slow["id"]))
        self.assertEqual(wait_done(slow["id"])["state"], "cancelled")
        with self.assertRaises(jobs.JobError):
            jobs.cancel(slow["id"])

    def test_autopilot_rules(self):
        recs = {r["key"]: r for r in autopilot.decide(self.conn)}
        self.assertIn("distill", recs)                              # never refreshed
        self.assertIn("backup", recs)                               # no backup yet
        self.assertEqual(recs["distill"]["verdict"], "autopilot is off")
        self.assertIsNone(autopilot.tick(self.conn))                # switch off: nothing runs
        control.set_switch("autopilot", True)
        control.set_value("autopilot_budget_usd", 0)
        item = evolve.add("paid one", "r")
        evolve.set_status(item["id"], "accepted")
        recs = {r["key"]: r for r in autopilot.decide(self.conn)}
        paid = recs["self_improve:%d" % item["id"]]
        self.assertFalse(paid["auto"])
        self.assertIn("over today's budget", paid["verdict"])
        self.assertTrue(recs["distill"]["auto"])
        with self.fake("print('ok')"):
            record = autopilot.tick(self.conn)
        self.assertEqual((record["by"], record["job"]), ("autopilot", recs[next(k for k in recs if recs[k]["auto"])]["job"]))
        wait_done(record["id"])

    def test_failed_job_is_not_retried_automatically(self):
        control.set_switch("autopilot", True)
        with self.fake("raise SystemExit(3)"):
            record = jobs.start(self.conn, "distill", {}, by="autopilot")
        self.assertEqual(wait_done(record["id"])["state"], "failed")
        rec = next(r for r in autopilot.decide(self.conn) if r["key"] == "distill")
        self.assertFalse(rec["auto"])
        self.assertIn("failed in the last 24 h", rec["verdict"])

    def test_values_are_validated(self):
        self.assertEqual(control.values()["autopilot_budget_usd"], 0.5)
        with self.assertRaises(ValueError):
            control.set_value("autopilot_budget_usd", 500)
        control.set_value("autopilot_budget_usd", 1.5)
        control.set_switch("tracing", False)                        # switches keep the values and vice versa
        self.assertEqual(control.values()["autopilot_budget_usd"], 1.5)
        self.assertFalse(control.is_on("tracing"))


if __name__ == "__main__":
    unittest.main()
