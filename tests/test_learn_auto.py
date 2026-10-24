"""Tests for automatic learning: session summaries by a strong model (faked) and learned preferences."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_learn import prefs, summarize  # noqa: E402
from tidos_session import brief  # noqa: E402
from test_learn import add_session  # noqa: E402

CWD = r"D:\work\Dev\APP"
CALLS = [("read", CWD + r"\lib\login.dart"), ("edit", CWD + r"\lib\login.dart")]


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tmp.name,
                                                "TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")})
        self.env.start()
        self.conn = db.connect(":memory:")

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()


class SummarizeTests(Isolated):
    def setUp(self):
        super().setUp()
        add_session(self.conn, "strong", CWD, "APP", "claude-opus-5-5", [
            ("fix the login crash on android", "success", 1, 0, CALLS, [("flutter analyze", 1)]),
            ("now add remember-me to login", "success", 1, 0, CALLS, [("flutter analyze", 1)])])
        add_session(self.conn, "weak", CWD, "APP", "opencode/big-pickle", [
            ("fix x", "success", 1, 0, CALLS, []), ("fix y", "success", 1, 0, CALLS, [])])
        self.conn.execute("UPDATE sessions SET ended_at = '2026-10-24' WHERE id = 'strong'")

    def test_only_strong_unsummarized_sessions_are_pending(self):
        self.assertEqual(summarize.pending_sessions(self.conn), ["strong"])

    def test_digest_is_compact_and_relative(self):
        project, text = summarize.digest(self.conn, "strong")
        self.assertEqual(project, "APP")
        self.assertIn("changed: lib/login.dart", text)
        self.assertIn("check: flutter analyze -> passed", text)
        self.assertNotIn(CWD, text)

    def test_summary_becomes_notes_once(self):
        calls = []

        def fake_ask(prompt):
            calls.append(prompt)
            return "Here you go:\n- Login lives in lib/login.dart; verify with `flutter analyze`.\n- short\n", None

        results = summarize.summarize_pending(self.conn, ask=fake_ask)
        self.assertEqual(results[0][1], ["Login lives in lib/login.dart; verify with `flutter analyze`."])
        with open(os.path.join(self.tmp.name, "playbooks", "app", "notes.md"), encoding="utf-8") as f:
            self.assertIn("session-summary", f.read())
        self.assertEqual(summarize.summarize_pending(self.conn, ask=fake_ask), [])   # never twice
        self.assertEqual(len(calls), 1)

    def test_kill_switch(self):
        from tidos_brain import control
        control.set_switch("auto_summarize", False)
        self.assertEqual(summarize.summarize_pending(self.conn, ask=lambda p: ("- x", None)), [])


class PrefsTests(Isolated):
    def setUp(self):
        super().setUp()
        add_session(self.conn, "s1", r"D:\work\Dev\TRADE", "TRADE", "claude-opus-5-5", [
            ("Audit the gates. Do not change trading thresholds or strategy parameters.", "success", 1, 0, [], []),
            ("Investigate the delay.\nDO NOT change trading thresholds and strategy parameters!", "success", 1, 0, [], []),
            ("Do NOT modify code.", "success", 1, 0, [], []),
            ("Do NOT modify code.", "success", 1, 0, [], []),
            ("Never deploy hosting without asking me first.", "success", 1, 0, [], [])])
        add_session(self.conn, "s2", r"D:\work\Dev\APP", "APP", "claude-opus-5-5", [
            ("Never deploy to hosting without asking me first please.", "success", 1, 0, [], [])])

    def test_recurring_specific_directives_only(self):
        learned = prefs.learn(self.conn)
        trade = [e["text"] for e in learned["projects"]["TRADE"]]
        self.assertEqual(len(trade), 2)
        self.assertTrue(any("thresholds" in t for t in trade))
        self.assertTrue(any("deploy" in t for t in trade))
        self.assertFalse(any(t == "Do NOT modify code." for t in trade))      # too generic, never a rule
        self.assertEqual([e["projects"] for e in learned["all"]], [["APP", "TRADE"]])

    def test_brief_includes_rules(self):
        prefs.write(prefs.learn(self.conn))
        rules = brief._user_rules("TRADE")
        self.assertEqual(len(rules), 2)
        text = brief.guide_brief({"model": "m", "tier": "weak"},
                                 {"name": "TRADE", "stack": ["python"], "checks": [], "notes": []})
        self.assertIn("standing rules", text)


if __name__ == "__main__":
    unittest.main()
