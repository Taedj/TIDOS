"""Tests for the trace -> dataset export (workflow records, privacy, selection)."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_learn import dataset  # noqa: E402
from test_learn import add_session  # noqa: E402

CWD = r"D:\work\Dev\APP"
CALLS = [("read", CWD + r"\lib\a.dart"), ("read", r"C:\Users\someone\notes.md"),
         ("exec", 'cd "D:/work/Dev/APP" && SP="C:\\Users\\someone\\tmp" && flutter test'), ("edit", CWD + r"\lib\a.dart")]


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tmp.name})
        self.env.start()
        self.conn = db.connect(":memory:")
        add_session(self.conn, "strong", CWD, "APP", "claude-opus-5-5", [
            ("fix the login crash, token is null", "success", 1, 0, CALLS, [("flutter test", 0), ("flutter test", 1)]),
            ("this one was corrected", "success", 1, 1, CALLS, [("flutter test", 1)]),
            ("this one failed", "failure", 0, 0, CALLS, [("flutter test", 0)])])
        add_session(self.conn, "weak", CWD, "APP", "opencode/big-pickle", [
            ("weak model task", "success", 1, 0, CALLS, [("flutter test", 1)])])

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()

    def test_command_normalization(self):
        self.assertEqual(dataset.command('cd "D:/x" && flutter test'), "flutter test")
        self.assertEqual(dataset.command('SP="C:\\Users\\u\\tmp" && python "C:\\a\\b.py" --x'), "python <path> --x")
        self.assertEqual(dataset.command("cd /tmp; ls"), "ls")
        self.assertEqual(dataset.command(""), "")

    def test_export_selects_good_strong_examples_without_private_data(self):
        path, stats = dataset.export(self.conn)
        with open(path, encoding="utf-8") as f:
            recs = [json.loads(line) for line in f]
        self.assertEqual([r["request"] for r in recs], ["fix the login crash, token is null"])
        rec = recs[0]
        self.assertEqual(rec["schema"], dataset.SCHEMA)
        self.assertEqual([s["kind"] for s in rec["steps"]], ["read", "exec", "edit"])  # outside-project read dropped
        self.assertEqual(rec["steps"][0]["target"], "lib/a.dart")
        self.assertEqual(rec["steps"][1]["target"], "flutter test")
        self.assertEqual(rec["checks"], [{"command": "flutter test", "passed": False},
                                         {"command": "flutter test", "passed": True}])
        self.assertTrue(rec["verified"])
        self.assertFalse(rec["first_check_passed"])
        self.assertNotIn("someone", json.dumps(recs))
        self.assertTrue(os.path.isfile(path[:-6] + ".md"))
        self.assertEqual(stats["records"], 1)

    def test_all_tiers_and_project_filter(self):
        _, stats = dataset.export(self.conn, strong_only=False)
        self.assertEqual(stats["records"], 2)
        _, stats = dataset.export(self.conn, strong_only=False, include_projects={"OTHER"})
        self.assertEqual(stats.get("records", 0), 0)


if __name__ == "__main__":
    unittest.main()
