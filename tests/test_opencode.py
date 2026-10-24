"""Tests for the OpenCode collector (fake opencode.db with the real table layout)."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db, opencode  # noqa: E402

T0 = 1792800000000


def make_db(path):
    c = sqlite3.connect(path)
    c.executescript("""
        CREATE TABLE session (id TEXT PRIMARY KEY, parent_id TEXT, directory TEXT, title TEXT,
                              time_created INTEGER, time_updated INTEGER);
        CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, time_created INTEGER, data TEXT);
        CREATE TABLE part (id TEXT PRIMARY KEY, message_id TEXT, session_id TEXT, time_created INTEGER, data TEXT);
        CREATE TABLE credential (id TEXT, value TEXT);
        INSERT INTO credential VALUES ('c1', 'must-never-be-read');
    """)
    return c


def add(c, sid, directory, turns, parent=None):
    c.execute("INSERT INTO session VALUES (?,?,?,?,?,?)", (sid, parent, directory, "t", T0, T0 + 999))
    n = 0
    for role, parts in turns:
        n += 1
        mid = "%s-m%d" % (sid, n)
        data = {"role": role}
        if role == "assistant":
            data.update({"modelID": "big-pickle", "providerID": "opencode"})
        c.execute("INSERT INTO message VALUES (?,?,?,?)", (mid, sid, T0 + n, json.dumps(data)))
        for k, part in enumerate(parts):
            c.execute("INSERT INTO part VALUES (?,?,?,?,?)", ("%s-p%d" % (mid, k), mid, sid, T0 + n, json.dumps(part)))
    c.commit()


def tool(name, status="completed", output="", **inp):
    return {"type": "tool", "tool": name, "state": {"status": status, "input": inp, "output": output}}


class OpenCodeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "opencode.db")
        c = make_db(self.path)
        add(c, "s1", "D:/work/Dev/APP", [
            ("user", [{"type": "text", "text": "fix the login crash"}]),
            ("assistant", [tool("read", filePath="D:/work/Dev/APP/lib/login.dart"),
                           tool("edit", filePath="D:/work/Dev/APP/lib/login.dart"),
                           tool("bash", output="2 errors found", command="flutter analyze"),
                           {"type": "step-finish", "tokens": {"input": 100, "output": 20, "cache": {"read": 50}}}]),
            ("assistant", [tool("bash", output="No issues found!", command="flutter analyze")]),
            ("user", [{"type": "text", "text": "no, it still crashes on android"}]),
            ("assistant", [tool("bash", status="error", output="boom", command="flutter test")]),
        ])
        add(c, "sub", "D:/work/Dev/APP", [("user", [{"type": "text", "text": "subagent work"}])], parent="s1")
        add(c, "tmp", "C:/Users/x/AppData/Local/Temp/probe", [("user", [{"type": "text", "text": "probe"}])])
        c.close()
        self.conn = db.connect(":memory:")

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_import(self):
        results = opencode.import_all(self.conn, self.path)
        self.assertEqual([s["id"] for s, _ in results], ["oc:s1"])        # sub-agent + temp session skipped
        session, tasks = results[0]
        self.assertEqual((session["project"], session["model"], session["source"]), ("APP", "opencode/big-pickle", "opencode"))
        first, second = tasks
        self.assertEqual(first["prompt"], "fix the login crash")
        self.assertEqual([c["kind"] for c in first["calls"]], ["read", "edit", "exec", "exec"])
        self.assertEqual([v["passed"] for v in first["verifications"]], [0, 1])
        self.assertEqual((first["verify_passed"], first["corrected"], first["input_tokens"]), (1, 1, 150))
        self.assertEqual((second["verify_passed"], second["tool_errors"]), (0, 1))
        rows = self.conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        self.assertEqual(rows, 2)

    def test_incremental_and_read_only(self):
        opencode.import_all(self.conn, self.path)
        self.assertEqual(opencode.import_all(self.conn, self.path), [])   # unchanged -> skipped
        c = sqlite3.connect(self.path)
        c.execute("UPDATE session SET time_updated = ? WHERE id = 's1'", (T0 + 5000,))
        c.commit()
        c.close()
        self.assertEqual(len(opencode.import_all(self.conn, self.path)), 1)  # changed -> re-imported
        dump = "\n".join(str(tuple(r)) for t in ("sessions", "tasks", "tool_calls")
                         for r in self.conn.execute("SELECT * FROM %s" % t))
        self.assertNotIn("must-never-be-read", dump)

    def test_missing_database(self):
        self.assertEqual(opencode.import_all(self.conn, os.path.join(self.tmp.name, "none.db")), [])


if __name__ == "__main__":
    unittest.main()
