"""Tests for graduated trust and the action journal (tidos_brain.trust) and how the autopilot uses them."""
import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import control, db, trust  # noqa: E402

PY = sys.executable
OLD = (datetime.now(timezone.utc) - timedelta(days=trust.SETTLE_DAYS + 1)).isoformat(timespec="seconds")


class TrustTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": os.path.join(self.tmp.name, "home"),
                                                "TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")})
        self.env.start()
        self.undone = []
        self.undo = mock.patch.dict(trust.UNDO, {"activate_unit": lambda a: self.undone.append(a["target"]) or "ok"})
        self.undo.start()

    def tearDown(self):
        self.undo.stop()
        self.env.stop()
        self.tmp.cleanup()

    def kept(self, kind, target="u"):
        item = trust.record(kind, "x", target=target)
        trust._set(item["id"], at=OLD)               # kept long enough
        return item

    def test_defaults(self):
        self.assertTrue(trust.allows_auto("distill"))
        self.assertFalse(trust.allows_auto("activate_unit"))   # changing your agents starts at 'propose'
        self.assertEqual(trust.level("self_improve"), "act_undo")

    def test_good_actions_raise_trust_up_to_the_ceiling(self):
        for _ in range(trust.PROMOTE_AFTER - 1):
            self.kept("activate_unit")
        trust.settle(job_state=lambda j: None)
        self.assertEqual(trust.level("activate_unit"), "propose")
        young = trust.record("activate_unit", "too recent")
        self.kept("activate_unit")
        trust.settle(job_state=lambda j: None)
        self.assertEqual(trust.level("activate_unit"), "act_undo")     # three kept in a row
        self.assertEqual(next(i for i in trust.journal() if i["id"] == young["id"])["state"], "open")
        for _ in range(trust.PROMOTE_AFTER):
            self.kept("activate_unit")
        trust.settle(job_state=lambda j: None)
        self.assertEqual(trust.level("activate_unit"), "act_undo")     # never above its ceiling

    def test_jobs_settle_on_their_outcome(self):
        trust.set_level("trial", None)
        states = {"a": "failed", "b": "running", "c": "done"}
        for job_id in states:
            trust.record("trial", job_id, job_id=job_id)
        settled = trust.settle(job_state=states.get)
        self.assertEqual([(a["job_id"], a["state"]) for a in settled], [("a", "failed"), ("c", "kept")])
        self.assertEqual(next(x for x in trust.levels() if x["kind"] == "trial")["streak"], 1)

    def test_undo_reverses_and_lowers_trust(self):
        trust.set_level("activate_unit", "act_undo")
        trust.set_level("activate_unit", None)
        for _ in range(trust.PROMOTE_AFTER):
            self.kept("activate_unit")
        trust.settle(job_state=lambda j: None)
        self.assertEqual(trust.level("activate_unit"), "act_undo")
        item = trust.record("activate_unit", "Activate python-x", target="python-x")
        done = trust.undo(item["id"])
        self.assertEqual((done["state"], self.undone), ("undone", ["python-x"]))
        self.assertEqual(trust.level("activate_unit"), "propose")
        with self.assertRaises(ValueError):
            trust.undo(item["id"])                                     # once
        with self.assertRaises(ValueError):
            trust.undo(trust.record("backup", "Back up")["id"])        # nothing to undo
        with self.assertRaises(KeyError):
            trust.undo(999)

    def test_your_own_reversal_counts_as_an_undo(self):
        trust.set_level("activate_unit", "act_undo")
        trust.set_level("activate_unit", None)
        trust.record("activate_unit", "Activate y", by="autopilot", target="y")
        self.assertEqual(trust.reversed_by_you("activate_unit", "y")["state"], "undone")
        self.assertIsNone(trust.reversed_by_you("activate_unit", "nobody"))

    def test_your_level_is_pinned(self):
        trust.set_level("activate_unit", "observe")
        for _ in range(trust.PROMOTE_AFTER):
            self.kept("activate_unit")
        trust.settle(job_state=lambda j: None)
        self.assertEqual(trust.level("activate_unit"), "observe")     # TIDOS never raises your choice
        self.assertEqual(trust.set_level("activate_unit", None), "propose")
        for bad in (("nope", "act"), ("trial", "god")):
            with self.assertRaises(ValueError):
                trust.set_level(*bad)

    def test_undo_self_improve_without_a_branch(self):
        from tidos_learn import evolve
        item = evolve.add("x", "y")
        evolve.set_status(item["id"], "accepted")
        action = trust.record("self_improve", "Implement #1", target=item["id"])
        with mock.patch.dict(trust.UNDO, {"self_improve": trust._undo_self_improve}):
            self.assertEqual(trust.undo(action["id"])["undo_detail"], "nothing was committed")
        self.assertEqual(evolve.load()[0]["status"], "new")              # not re-implemented by the autopilot

    def test_autopilot_activates_only_trial_winners_and_follows_trust(self):
        from tidos_dashboard import autopilot
        from tidos_learn import army
        conn = db.connect(":memory:")
        units = {"win": {"state": "draft"}, "tie": {"state": "draft"}}
        trials = {"win": {"unit": 80, "plain": 60, "tasks": 5, "passed": True},
                  "tie": {"unit": 60, "plain": 60, "tasks": 5, "passed": True}}
        control.set_switch("autopilot", True)
        with mock.patch.object(army, "units", lambda: units), \
                mock.patch.object(army, "load_state", lambda: {"trials": trials}):
            recs = {r["key"]: r for r in autopilot.decide(conn)}
            self.assertNotIn("activate:tie", recs)                       # a tie is not a win
            self.assertFalse(recs["activate:win"]["auto"])               # 'propose': you click
            self.assertIn("after 3 good runs", recs["activate:win"]["verdict"])
            trust.set_level("activate_unit", "act_undo")
            self.assertTrue({r["key"]: r for r in autopilot.decide(conn)}["activate:win"]["auto"])
        conn.close()

    def test_every_job_is_journaled(self):
        from tidos_dashboard import jobs
        conn = db.connect(":memory:")
        fake = mock.patch.object(jobs, "build", lambda c, job, p: ([PY, "-c", "print(1)"], {}, "fake " + job, None))
        with fake:
            record = jobs.start(conn, "backup", {}, by="autopilot")
        deadline = time.time() + 30
        while (jobs.get(record["id"]) or {}).get("state") == "running" and time.time() < deadline:
            time.sleep(0.1)
        action = trust.journal()[-1]
        self.assertEqual((action["kind"], action["job_id"], action["by"]), ("backup", record["id"], "autopilot"))
        self.assertEqual(trust.settle()[0]["state"], "kept")
        conn.close()


if __name__ == "__main__":
    unittest.main()
