"""Tests for the Shadow Army: mission attribution, evidence XP, lessons, ARISE, rework proposals, activation."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import claude_code, db, opencode  # noqa: E402
from tidos_learn import army, evolve  # noqa: E402
from test_learn import add_session  # noqa: E402

CWD = r"D:\work\Dev\APP"


def delegate(conn, sid, seq, summary):
    task_id = conn.execute("SELECT id FROM tasks WHERE session_id = ? AND seq = ?", (sid, seq)).fetchone()[0]
    conn.execute("INSERT INTO tool_calls (task_id, tool, kind, summary) VALUES (?, 'Agent', 'delegate', ?)",
                 (task_id, summary))
    conn.commit()


class ArmyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.personal = os.path.join(self.tmp.name, "claude-agents")
        self.patches = [mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": os.path.join(self.tmp.name, "home")}),
                        mock.patch.object(army, "personal_agents_dir", lambda: self.personal)]
        for p in self.patches:
            p.start()
        self.conn = db.connect(":memory:")
        add_session(self.conn, "s", CWD, "APP", "claude-opus-5-5", [
            ("review my login fix", "success", 1, 0, [], [("flutter test", 1)]),
            ("review the payment change", "success", 1, 1, [], [("flutter test", 1)]),
            ("no, you missed the null check in pay()", "failure", 0, 0, [], [("flutter test", 0)]),
            ("explore the settings code", "unknown", None, 0, [], [])])
        delegate(self.conn, "s", 0, "tidos-reviewer: Review login fix")
        delegate(self.conn, "s", 1, "tidos-reviewer: Review payment change")
        delegate(self.conn, "s", 2, "tidos-reviewer: Review payment again")
        delegate(self.conn, "s", 3, "Explore: Map settings")

    def tearDown(self):
        self.conn.close()
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def test_importers_record_the_subagent(self):
        self.assertEqual(claude_code._summary("Agent", {"description": "map code"}), "general-purpose: map code")
        self.assertEqual(claude_code._summary("Agent", {"subagent_type": "tidos-tester", "description": "x"}),
                         "tidos-tester: x")
        self.assertEqual(opencode._summary("task", {"subagent_type": "explore", "description": "audit"}), "explore: audit")
        self.assertEqual(army.unit_name("Explore: x"), "explore")
        self.assertEqual(army.unit_name("general: x"), "general-purpose")  # OpenCode and Claude merged
        conn = db.connect(":memory:")
        self.assertTrue(claude_code.importer_stale(conn, "claude-code", 2))
        claude_code.importer_done(conn, "claude-code", 2)
        self.assertFalse(claude_code.importer_stale(conn, "claude-code", 2))
        self.assertTrue(claude_code.importer_stale(conn, "claude-code", 3))  # a newer parser re-reads everything
        conn.close()

    def test_rank_comes_from_evidence(self):
        roster = {u["name"]: u for u in army.compute(self.conn)}
        rev = roster["tidos-reviewer"]
        # success+check+first try (30), success+check+first try-corrected (20), failure (-10)
        self.assertEqual((rev["missions"], rev["xp"], rev["corrected"]), (3, 40, 1))
        self.assertEqual(rev["success"], 0.67)
        self.assertEqual(rev["projects"], ["APP"])
        self.assertEqual(roster["explore"]["state"], "native")
        self.assertEqual(roster["tidos-architect"]["rank"], "-")   # no missions, no rank

    def test_lessons_hold_checks_failures_and_corrections(self):
        army.write_lessons(self.conn)
        text = army.lessons("tidos-reviewer")
        self.assertIn("`flutter test`", text)
        self.assertIn("corrected: Review payment change", text)
        self.assertIn("missed the null check", text)              # the user's correcting message
        self.assertIn("failed: Review payment again", text)
        self.assertIsNone(army.lessons("tidos-architect"))

    def test_retire_proposal_once(self):
        roster = [{"name": "bad-unit", "state": "active", "missions": 6, "success": 0.2, "xp": -40, "corrected": 3}]
        self.assertEqual(len(army.retire_proposals(roster)), 1)
        self.assertEqual(army.retire_proposals(roster), [])       # no duplicate
        self.assertIn("bad-unit", evolve.load()[0]["title"])

    def test_arise_drafts_uncovered_stack_only(self):
        home = os.environ["TIDOS_HOME_DIR"]
        os.makedirs(os.path.join(home, "playbooks", "_general"))
        for stack in ("firebase", "flutter-dart"):
            with open(os.path.join(home, "playbooks", "_general", "feature--%s.md" % stack), "w", encoding="utf-8") as f:
                f.write("---\nx: y\n---\n# feature\nVerify with `firebase emulators:exec`.\n## Example requests\n- private\n")
        tasks = [{"strong": True, "verify_passed": 1, "corrected": 0, "outcome": "success", "stacks": [s],
                  "prompt": "p", "type": "feature", "calls": [], "checks": []}
                 for s in ["firebase"] * 12 + ["flutter/dart"] * 12 + ["python"] * 3]
        made = army.arise(self.conn, tasks)
        self.assertEqual([os.path.basename(p) for p in made], ["firebase-specialist.md"])  # flutter: tidos-mobile
        with open(made[0], encoding="utf-8") as f:
            text = f.read()
        self.assertIn("name: firebase-specialist", text)
        self.assertIn("firebase emulators:exec", text)
        self.assertNotIn("private", text)                         # example requests never copied
        self.assertEqual(army.arise(self.conn, tasks), [])        # once

    def test_activate_and_undo(self):
        drafts = os.path.join(os.environ["TIDOS_HOME_DIR"], "drafts", "agents")
        os.makedirs(drafts)
        with open(os.path.join(drafts, "x-specialist.md"), "w", encoding="utf-8") as f:
            f.write("---\nname: x-specialist\ndescription: d\n---\nbody\n<!-- DRAFT by TIDOS (ARISE): review -->\n")
        with self.assertRaises(ValueError):
            army.activate("tidos-reviewer")                       # already active, not a draft
        path = army.activate("x-specialist")
        self.assertEqual(os.path.dirname(path), self.personal)
        with open(path, encoding="utf-8") as f:
            self.assertNotIn("DRAFT by TIDOS", f.read())
        self.assertEqual(army.units()["x-specialist"]["state"], "active")
        with self.assertRaises(ValueError):
            army.activate("x-specialist")
        army.deactivate("x-specialist")
        self.assertFalse(os.path.exists(path))
        self.assertEqual(army.units()["x-specialist"]["state"], "draft")
        with self.assertRaises(ValueError):
            army.deactivate("tidos-reviewer")                     # never removes what TIDOS did not activate

    def test_trial_is_recorded(self):
        trial = army.record_trial("x", "claude:haiku", 6, 50.0, 66.7)
        self.assertTrue(trial["passed"])
        self.assertEqual(army.load_state()["trials"]["x"]["unit"], 67)
        self.assertIn("TIDOS reviewer", army.unit_prompt("tidos-reviewer"))
        self.assertNotIn("name: tidos-reviewer", army.unit_prompt("tidos-reviewer"))


if __name__ == "__main__":
    unittest.main()
