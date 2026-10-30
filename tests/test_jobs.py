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
        argv, env, title, model = jobs.build(self.conn, "raid", {"agent": "opencode:opencode/big-pickle",
                                                                 "mode": "compare", "min_difficulty": "A"})
        self.assertEqual(argv[0], PY)
        self.assertEqual(model, "opencode:opencode/big-pickle")
        self.assertNotIn("--budget", argv)                          # free model: no money anywhere
        with mock.patch("tidos_session.helper.shutil.which", lambda exe: "opencode"):
            _, _, _, model = jobs.build(self.conn, "trial", {"unit": "tidos-tester", "suite": "python"})
        self.assertEqual(model, "opencode:opencode/big-pickle")     # default = the free helper model
        argv, _, _, _ = jobs.build(self.conn, "trial", {"unit": "tidos-tester", "agent": "claude:haiku", "suite": "python"})
        self.assertIn("--budget", argv)                             # Claude only if you choose it, capped internally
        with mock.patch("tidos_brain.claude_code.is_synthetic", lambda cwd: False):  # temp dirs count as test runs
            self.assertEqual(jobs.build(self.conn, "scout_needs", {"project": self.tmp.name})[0][-2], self.tmp.name)
        item = evolve.add("x", "y")
        evolve.set_status(item["id"], "accepted")
        self.assertIn("--id", jobs.build(self.conn, "self_improve", {"id": item["id"]})[0])

    def fake(self, code):
        return mock.patch.object(jobs, "build", lambda conn, job, p: ([PY, "-c", code], {}, "fake " + job, None))

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
        item = evolve.add("an accepted one", "r")
        evolve.set_status(item["id"], "accepted")
        with mock.patch("tidos_session.helper.shutil.which", lambda exe: None):
            no_free = {r["key"] for r in autopilot.decide(self.conn)}
        self.assertNotIn("self_improve:%d" % item["id"], no_free)    # no free model here: model jobs wait
        with mock.patch("tidos_session.helper.shutil.which", lambda exe: "opencode"):  # a free model is available
            recs = {r["key"]: r for r in autopilot.decide(self.conn)}
        self.assertTrue(recs["self_improve:%d" % item["id"]]["auto"])  # no budget: every due job is no-cost
        self.assertEqual(recs["distill"]["verdict"], "autopilot will run it")
        self.assertNotIn("estimate", recs["distill"])
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

    def test_autopilot_uses_a_free_model_and_skips_trials_that_cannot_count(self):
        import json
        from tidos_learn import army
        home = os.environ["TIDOS_HOME_DIR"]
        os.makedirs(home, exist_ok=True)
        with open(os.path.join(home, "session.json"), "w", encoding="utf-8") as f:
            json.dump({"tool": "claude-code", "model": "claude-opus-5-5"}, f)   # you work with a frontier model
        drafts = {"python-x": {"state": "draft"}, "node-javascript-x": {"state": "draft"}}
        with mock.patch("tidos_session.helper.shutil.which", lambda exe: exe), \
                mock.patch.object(army, "units", lambda: drafts), mock.patch.object(army, "load_state", lambda: {}), \
                mock.patch.object(jobs, "trial_ready", lambda suite: suite == "python"):
            self.assertEqual(jobs.default_agent(self.conn), "claude:claude-opus-5-5")  # your own jobs: your model
            recs = {r["key"]: r for r in autopilot.decide(self.conn)}
            self.assertEqual(recs["trial:python-x"]["model"], "opencode:opencode/big-pickle")  # background: free
            self.assertNotIn("trial:node-javascript-x", recs)                  # 3 dungeons: a trial never counts
        with mock.patch("tidos_session.helper.shutil.which", lambda exe: None), \
                mock.patch.object(army, "units", lambda: drafts), mock.patch.object(army, "load_state", lambda: {}):
            recs = {r["key"]: r for r in autopilot.decide(self.conn)}
        self.assertFalse([k for k in recs if k.startswith(("trial:", "weak_check"))])  # no free model: no model job
        self.assertFalse(jobs.trial_ready("javascript"))                       # the real suite is too small today

    def test_autopilot_runs_a_job_at_most_once_a_day(self):
        control.set_switch("autopilot", True)
        with self.fake("print('nothing to do')"):
            wait_done(jobs.start(self.conn, "backup", {}, by="autopilot")["id"])
        rec = next(r for r in autopilot.decide(self.conn) if r["key"] == "backup")  # still due: no backup file
        self.assertFalse(rec["auto"])
        self.assertIn("already ran", rec["verdict"])
        self.assertTrue(next(r for r in autopilot.decide(self.conn) if r["key"] == "distill")["auto"])  # other jobs run

    def test_helper_model_setting(self):
        from tidos_session import helper
        self.assertEqual(control.text("helper_model"), "auto")
        for bad in ("rm -rf /", "claude:haiku; x", "opencode:noslash", 5):
            with self.assertRaises(ValueError):
                control.set_text("helper_model", bad)
        control.set_text("helper_model", "opencode:google/gemini-2.5-flash")   # any model you have
        control.set_switch("tracing", False)                        # switches keep the texts and vice versa
        self.assertEqual(control.text("helper_model"), "opencode:google/gemini-2.5-flash")
        self.assertFalse(control.is_on("tracing"))
        self.assertEqual(helper.resolve(), "opencode:google/gemini-2.5-flash")
        control.set_text("helper_model", "auto")
        with mock.patch("tidos_session.helper.shutil.which", lambda exe: None):
            self.assertIsNone(helper.resolve())                     # no free model -> local only, never paid
        with mock.patch("tidos_session.helper.shutil.which", lambda exe: "opencode"):
            self.assertEqual(helper.resolve(conn=self.conn), "opencode:opencode/big-pickle")  # the free one you use
        control.set_text("helper_model", "none")
        self.assertEqual(helper.ask("hi")[0], None)                 # 'none': no model is ever called

    def test_helper_follows_start_tidos(self):
        import json
        from tidos_session import helper
        home = os.environ["TIDOS_HOME_DIR"]
        os.makedirs(home, exist_ok=True)

        def started(tool, model):
            with open(os.path.join(home, "session.json"), "w", encoding="utf-8") as f:
                json.dump({"tool": tool, "model": model}, f)
        every_cli = mock.patch("tidos_session.helper.shutil.which", lambda exe: exe)
        with every_cli:
            started("gemini-cli", "gemini-2.5-pro")
            self.assertEqual(helper.resolve(conn=self.conn), "gemini:gemini-2.5-pro")      # the model you work with
            started("opencode", "google/gemini-2.5-flash")
            self.assertEqual(helper.resolve(conn=self.conn), "opencode:google/gemini-2.5-flash")
            started("claude-code", "claude-opus-5-5")
            self.assertEqual(helper.describe(self.conn)["note"], "from your last START TIDOS")
            started("antigravity", "gemini-3-pro")                                       # an IDE, no command line
            self.assertEqual(helper.resolve(conn=self.conn), "opencode:opencode/big-pickle")
            self.assertIn("antigravity has no command line", helper.describe(self.conn)["note"])
        with mock.patch("tidos_session.helper.shutil.which", lambda exe: None):
            started("gemini-cli", "gemini-2.5-pro")
            self.assertIsNone(helper.resolve(conn=self.conn))      # CLI missing, no free model: local only


if __name__ == "__main__":
    unittest.main()
