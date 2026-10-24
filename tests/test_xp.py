"""Tests for the XP engine and growth drafts (skill drafts, job change)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_learn import distill, xp  # noqa: E402
from test_learn import add_session  # noqa: E402

CWD = r"D:\work\Dev\APP"
CALLS = [("read", CWD + r"\lib\a.dart"), ("edit", CWD + r"\lib\a.dart")]


class XpTests(unittest.TestCase):
    def test_task_xp_rewards_evidence(self):
        base = {"outcome": "success", "verify_passed": 1, "corrected": 0}
        self.assertEqual(xp.task_xp(dict(base, checks=[{"passed": 1}]))[0], 30)       # right first time
        self.assertEqual(xp.task_xp(dict(base, checks=[{"passed": 0}, {"passed": 1}]))[0], 25)
        self.assertEqual(xp.task_xp(dict(base, verify_passed=None, outcome="unknown"))[0], 5)
        self.assertEqual(xp.task_xp({"outcome": "failure", "verify_passed": 0, "corrected": 1})[0], -20)

    def test_levels_and_ranks(self):
        self.assertEqual(xp.level_for(0), (1, 0, 100))
        self.assertEqual(xp.level_for(100)[0], 2)
        self.assertEqual([xp.rank_for(n) for n in (1, 5, 10, 20, 35, 50)], list("EDCBAS"))


class GrowthTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tmp.name})
        self.env.start()
        self.conn = db.connect(":memory:")
        tasks = [("fix the login crash number %d" % i, "success", 1, 0, CALLS, [("flutter analyze", 1)])
                 for i in range(12)]
        add_session(self.conn, "s", CWD, "APP", "claude-opus-5-5", tasks)

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()

    def test_compute_writes_events_and_domains(self):
        summary = xp.compute(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM xp_events").fetchone()[0], 12)
        self.assertEqual(summary["domains"]["APP"]["xp"], 12 * 30)
        self.assertEqual(summary["domains"]["APP"]["tasks"], 12)
        xp.compute(self.conn)                                                     # recompute replaces
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM xp_events").fetchone()[0], 12)

    def test_skill_draft_from_a_proven_playbook(self):
        distill.distill(self.conn)       # also runs xp.level_up
        drafts = os.path.join(self.tmp.name, "drafts", "skills")
        self.assertEqual(sorted(os.listdir(drafts)), ["app-bugfix", "flutter-dart-bugfix"])  # project + general
        with open(os.path.join(drafts, "app-bugfix", "SKILL.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("name: app-bugfix", text)
        self.assertIn("DRAFT by TIDOS", text)
        self.assertEqual(xp.draft_skills(self.conn), [])                         # never overwritten

    def test_job_change_includes_standing_rules(self):
        distill.distill(self.conn)
        rules = os.path.join(self.tmp.name, "memory", "LEARNED_PREFERENCES.md")
        with open(rules, "w", encoding="utf-8") as f:
            f.write("## APP\n- Never deploy hosting without asking the user first _(x3)_\n")
        made = xp.job_change({"domains": {"APP": {"level": 15, "rank": "C"}, "small": {"level": 3, "rank": "E"}}})
        self.assertEqual([os.path.basename(m) for m in made], ["app-specialist.md"])
        with open(made[0], encoding="utf-8") as f:
            text = f.read()
        self.assertIn("name: app-specialist", text)
        self.assertIn("Never deploy hosting without asking", text)
        self.assertIn("unless the user explicitly asks otherwise", text)


if __name__ == "__main__":
    unittest.main()
