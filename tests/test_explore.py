"""Tests for the control-center tools: search, Ask TIDOS, settings editor, backups."""
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_dashboard import explore  # noqa: E402
from test_learn import add_session  # noqa: E402

CWD = r"D:\work\Dev\APP"
CALLS = [("read", CWD + r"\lib\a.dart"), ("edit", CWD + r"\lib\a.dart")]


class ExploreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tmp.name,
                                                "TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")})
        self.env.start()
        self.conn = db.connect(":memory:")
        add_session(self.conn, "s", CWD, "APP", "claude-opus-5-5", [
            ("fix the login crash on android", "failure", 0, 0, CALLS, [("flutter test", 0)]),
            ("add a dark theme toggle", "success", 1, 0, CALLS, [("flutter test", 1)])])
        os.makedirs(os.path.join(self.tmp.name, "memory"))
        with open(os.path.join(self.tmp.name, "memory", "LESSONS.md"), "w", encoding="utf-8") as f:
            f.write("# Lessons\nThe login crash came from a null token.\n")

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()

    def test_search_all_words_across_kinds(self):
        kinds = {r["kind"] for r in explore.search(self.conn, "login crash")["results"]}
        self.assertEqual(kinds, {"task", "memory"})
        self.assertEqual(explore.search(self.conn, "login banana")["results"], [])
        self.assertEqual(explore.search(self.conn, "why did the")["words"], [])   # stopwords only

    def test_ask_uses_digest_and_respects_switch(self):
        seen = []

        def llm(prompt):
            seen.append(prompt)
            return "APP: 1 failure (login crash).", None
        result = explore.ask(self.conn, "why did APP tasks fail?", llm=llm)
        self.assertEqual(result["source"], "llm")
        self.assertIn("fix the login crash", seen[0])
        self.assertIn("APP |", seen[0])
        from tidos_brain import control
        control.set_switch("ask_llm", False)
        result = explore.ask(self.conn, "why?", llm=lambda p: self.fail("model called while switch is off"))
        self.assertEqual(result["source"], "local")
        self.assertIn("local facts only", result["answer"])

    def test_ask_answer_language(self):
        seen = []
        explore.ask(self.conn, "why?", llm=lambda p: (seen.append(p), ("ok", None))[1], lang="ar")
        explore.ask(self.conn, "why?", llm=lambda p: (seen.append(p), ("ok", None))[1], lang="xx")
        self.assertIn("Write the answer in Arabic", seen[0])
        self.assertNotIn("Write the answer in", seen[1])  # unknown language -> English, nothing injected

    def test_ask_falls_back_when_model_fails(self):
        result = explore.ask(self.conn, "anything", llm=lambda p: (None, "claude CLI not found"))
        self.assertEqual(result["source"], "local")
        self.assertIn("claude CLI not found", result["answer"])

    def test_settings_edit_keeps_comments_and_validates(self):
        path = os.path.join(self.tmp.name, "framework.md")
        shutil.copy(explore.FRAMEWORK, path)
        with mock.patch.object(explore, "FRAMEWORK", path):
            values = {s["key"]: s["value"] for s in explore.settings()}
            self.assertEqual(set(values), set(explore.SETTINGS))
            explore.set_setting("persona_factory.depth_threshold", 4)
            explore.set_setting("gptid.limits.max_files", 3)
            explore.set_setting("gptid.browser", "manual")
            values = {s["key"]: s["value"] for s in explore.settings()}
            self.assertEqual((values["persona_factory.depth_threshold"], values["gptid.limits.max_files"],
                              values["gptid.browser"]), (4, 3, "manual"))
            for key, bad in (("persona_factory.depth_threshold", 99), ("persona_factory.enabled", "yes"),
                             ("gptid.browser", "chrome"), ("gptid.limits.max_files", True)):
                with self.assertRaises(ValueError, msg=key):
                    explore.set_setting(key, bad)
            with self.assertRaises(KeyError):
                explore.set_setting("gptid.relay_host", "0.0.0.0")  # not editable from the dashboard
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("depth_threshold: 4             # sessions/sources needed", text)
        self.assertIn("relay_host: 127.0.0.1", text)
        with open(explore.FRAMEWORK, encoding="utf-8") as f:
            original = f.read()
        self.assertEqual(len(text.splitlines()), len(original.splitlines()))

    def test_backup_check_and_restore(self):
        path = os.path.join(self.tmp.name, "brain.db")
        live = db.connect(path)
        add_session(live, "s1", CWD, "APP", "claude-opus-5-5", [("first task here", "success", 1, 0, CALLS, [])])
        name = os.path.basename(explore.backup(live))
        self.assertTrue(explore.check_backup(os.path.join(explore.backups_dir(), name))[0])
        add_session(live, "s2", CWD, "APP", "claude-opus-5-5", [("second task here", "success", 1, 0, CALLS, [])])
        live.close()
        safety, detail = explore.restore(name, path)
        self.assertEqual(detail, "1 tasks")
        check = sqlite3.connect(path)
        self.assertEqual(check.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 1)
        check.close()
        self.assertTrue(os.path.isfile(safety))                    # the replaced brain is kept
        bogus = os.path.join(explore.backups_dir(), "brain-bogus.db")
        sqlite3.connect(bogus).close()
        with self.assertRaises(ValueError):
            explore.restore("brain-bogus.db", path)

    def test_backup_rotation(self):
        os.makedirs(explore.backups_dir())
        for i in range(12):
            old = os.path.join(explore.backups_dir(), "brain-%s20260101-0000%02d.db" % ("pre-restore-" * (i == 0), i))
            open(old, "w").close()
            os.utime(old, (1e9 + i, 1e9 + i))
        newest = os.path.basename(explore.backup(self.conn, keep=10))
        names = [b["name"] for b in explore.list_backups()]
        self.assertEqual(len(names), 10)
        self.assertEqual(names[0], newest)
        self.assertNotIn("brain-pre-restore-20260101-000000.db", names)  # oldest goes first, whatever its name


if __name__ == "__main__":
    unittest.main()
