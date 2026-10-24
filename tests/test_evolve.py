"""Tests for the evolution queue (proposals, statuses, issue drafts) and dashboard notifications."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_dashboard import stats  # noqa: E402
from tidos_learn import evolve  # noqa: E402
from tidos_mcp import server  # noqa: E402


class EvolveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_queue_lifecycle_and_ranking(self):
        a = evolve.add("low idea", "why", "low")
        b = evolve.add("urgent fix", "why", "high")
        server.tool_propose({"title": "from an agent", "reason": "seen in a session"})
        # high, then the agent's default medium, then low
        self.assertEqual([i["title"] for i in evolve.ranked()], ["urgent fix", "from an agent", "low idea"])
        evolve.set_status(b["id"], "accepted")
        self.assertEqual([i["id"] for i in evolve.ranked("accepted")], [b["id"]])
        with self.assertRaises(ValueError):
            evolve.set_status(a["id"], "merged")
        with self.assertRaises(KeyError):
            evolve.set_status(99, "accepted")

    def test_issue_draft_is_local_and_command_only(self):
        item = evolve.add('Add "x" flag', "Because.", "high")
        path, command = evolve.issue_draft(item)
        self.assertTrue(path.startswith(self.tmp.name) and os.path.isfile(path))
        self.assertIn("gh issue create --repo Taedj/TIDOS", command)
        self.assertNotIn('"x"', command.split("--body-file")[0].split("--title", 1)[1][2:-2])  # quotes neutralized

    def test_notifications(self):
        conn = db.connect(":memory:")
        self.assertTrue(any("No daily quest" in n["text"] for n in stats.notifications(conn)))
        item = evolve.add("idea", "why")
        evolve.set_status(item["id"], "implemented", branch="auto/1-idea")
        evolve.add("another", "why")
        reports = os.path.join(self.tmp.name, "reports")
        os.makedirs(reports)
        with open(os.path.join(reports, "2026-10-24.md"), "w", encoding="utf-8") as f:
            f.write("# TIDOS daily quest\n\n**Result:** REGRESSION in tests\n")
        texts = [n["text"] for n in stats.notifications(conn)]
        self.assertTrue(any("1 new proposal" in t for t in texts))
        self.assertTrue(any("auto/1-idea" in t for t in texts))
        self.assertTrue(any("REGRESSION in tests" in t for t in texts))


class AblationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tmp.name})
        self.env.start()
        self.conn = db.connect(":memory:")

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()

    def add(self, model, passed_list):
        with self.conn:
            for i, passed in enumerate(passed_list):
                self.conn.execute("INSERT INTO evals (suite, task_name, model, with_tidos, passed, run_at) "
                                  "VALUES ('s', ?, ?, 2, ?, 'x')", ("t%d" % i, model, passed))

    def test_weak_rules_ablation_renumbers(self):
        from tidos_session import brief
        text = brief.weak_rules(1)
        self.assertTrue(text.startswith("1. Read before you edit"))
        self.assertNotIn("SMALL steps", text)
        self.assertEqual(brief.weak_rules(None), brief.WEAK_RULES)
        with self.assertRaises(ValueError):
            brief.weak_rules(99)

    def test_verdict_files_proposal_only_when_rule_earns_nothing(self):
        from tidos_evals import cli
        self.add("a", [1] * 6 + [0] * 4)
        self.add("a [no rule 3]", [1] * 3 + [0] * 7)
        self.assertIn("earns its place", cli.ablation_verdict(self.conn, "a", 3))
        self.assertEqual(evolve.load(), [])
        self.add("a [no rule 5]", [1] * 7 + [0] * 3)
        self.assertIn("proposal #1", cli.ablation_verdict(self.conn, "a", 5))
        self.assertIn("GUIDE rule 5", evolve.load()[0]["title"])

    def test_verdict_needs_enough_shared_tasks(self):
        from tidos_evals import cli
        self.add("a", [1] * 3)
        self.add("a [no rule 2]", [1] * 3)
        self.assertIn("need 10", cli.ablation_verdict(self.conn, "a", 2))


if __name__ == "__main__":
    unittest.main()
