"""Tests for tidos_brain: schema, Claude Code transcript import, scoring, hooks, installer."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import claude_code, cli, db, scoring  # noqa: E402

SID = "sess-1"


def _user(text, **extra):
    return {"type": "user", "sessionId": SID, "cwd": "D:\\work\\Dev\\demo", "gitBranch": "main",
            "timestamp": extra.pop("ts", "2026-10-24T10:00:00Z"),
            "message": {"role": "user", "content": text}, **extra}


def _tool_result(tool_id, output, is_error=False):
    return {"type": "user", "sessionId": SID, "timestamp": "2026-10-24T10:00:05Z",
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": tool_id, "content": output, "is_error": is_error}]}}


def _assistant(blocks, msg_id="m1", ts="2026-10-24T10:00:03Z", **extra):
    return {"type": "assistant", "sessionId": SID, "timestamp": ts,
            "message": {"id": msg_id, "role": "assistant", "model": "claude-opus-5-5", "content": blocks,
                        "usage": {"input_tokens": 100, "output_tokens": 20}}, **extra}


def _tool_use(tool_id, name, **inp):
    return {"type": "tool_use", "id": tool_id, "name": name, "input": inp}


TRANSCRIPT = [
    {"type": "ai-title", "aiTitle": "Fix login bug", "sessionId": SID},
    _user("<system-reminder>context only</system-reminder>"),                     # not a prompt
    _user("fix the login bug, token is sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAA"),    # task 0
    _assistant([_tool_use("t1", "Read", file_path="app/login.py")], msg_id="m1"),
    _assistant([_tool_use("t2", "Edit", file_path="app/login.py")], msg_id="m1"),  # same message, split line
    _tool_result("t1", "file content"),
    _tool_result("t2", "ok"),
    _assistant([_tool_use("t3", "Bash", command="python -m pytest -q")], msg_id="m2"),
    _tool_result("t3", "2 failed, 10 passed"),
    _assistant([{"type": "text", "text": "done"}], msg_id="m3"),
    _user("no, it still fails"),                                                   # task 1 = correction of task 0
    _assistant([_tool_use("t4", "Agent", description="investigate")], msg_id="m4"),
    _assistant([_tool_use("x1", "Bash", command="rm -rf /")], msg_id="sub", isSidechain=True),  # skipped
    _tool_result("t4", "found it"),
    _assistant([_tool_use("t5", "Edit", file_path="app/login.py")], msg_id="m5"),
    _tool_result("t5", "ok"),
    _assistant([_tool_use("t6", "PowerShell", command="pytest -q")], msg_id="m6", ts="2026-10-24T10:05:00Z"),
    _tool_result("t6", "12 passed, 0 failed"),
    _user("<command-name>/review</command-name><command-args>--fast</command-args>"),  # task 2 (command)
    _user("<bash-input>firebase deploy</bash-input>"),                              # "!" shell command: not a task
    _user("<bash-stdout>\x1b[1mDeploying\x1b[22m</bash-stdout><bash-stderr></bash-stderr>"),
    _user('fix this <pasted_content id="17">TypeError: x is undefined</pasted_content>'),  # task 3
]


def write_transcript(lines):
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")
    return path


class ScoringTests(unittest.TestCase):
    def test_verify_detection(self):
        self.assertTrue(scoring.is_verify_command("python -m pytest -q"))
        self.assertTrue(scoring.is_verify_command("flutter analyze"))
        self.assertFalse(scoring.is_verify_command("git status"))

    def test_verify_passed(self):
        self.assertFalse(scoring.verify_passed(False, "2 failed, 10 passed"))
        self.assertTrue(scoring.verify_passed(False, "12 passed, 0 failed"))
        self.assertFalse(scoring.verify_passed(True, ""))
        self.assertFalse(scoring.verify_passed(False, "Traceback (most recent call last):"))
        # checkers that report failures without "failed"/"error:" (Bash gives no exit code)
        for output in ("Analyzing app...\n  error • Undefined name 'x' • lib/a.dart:3:5\n3 issues found.",
                       "FAIL src/app.test.js\n  x renders", "npm ERR! code ELIFECYCLE",
                       "src/a.ts(3,5): error TS2322: Type 'string'", "not ok 1 - adds"):
            self.assertFalse(scoring.verify_passed(False, output), output)
        for output in ("Analyzing app...\nNo issues found! (ran in 2.1s)", "PASS src/app.test.js", "ok 1 - adds",
                       "All tests passed!", "0 issues found", "fail-open mode enabled\n3 passed",
                       "the exit code 1 is handled below\n5 passed"):
            self.assertTrue(scoring.verify_passed(False, output), output)

    def test_correction(self):
        for text in ("no, it still fails", "Wrong file", "ça marche pas", "doesn't work"):
            self.assertTrue(scoring.is_correction(text), text)
        for text in ("now add tests", "nothing else", "yes"):
            self.assertFalse(scoring.is_correction(text), text)

    def test_score_bounds(self):
        self.assertEqual(scoring.score_task(True, False, 0), (0.8, "success"))
        self.assertEqual(scoring.score_task(False, True, 10), (0.0, "failure"))
        self.assertEqual(scoring.score_task(None, False, 0), (0.5, "unknown"))


class TranscriptTests(unittest.TestCase):
    def setUp(self):
        self.path = write_transcript(TRANSCRIPT)
        self.session, self.tasks = claude_code.parse_transcript(self.path)

    def tearDown(self):
        os.remove(self.path)

    def test_session_metadata(self):
        self.assertEqual(self.session["id"], SID)
        self.assertEqual(self.session["title"], "Fix login bug")
        self.assertEqual(self.session["project"], "demo")
        self.assertEqual(self.session["model"], "claude-opus-5-5")

    def test_task_segmentation(self):
        self.assertEqual([t["prompt"] for t in self.tasks][1:],
                         ["no, it still fails", "/review --fast", "fix this TypeError: x is undefined"])
        self.assertEqual(len(self.tasks), 4)

    def test_first_task_failed_and_corrected(self):
        t = self.tasks[0]
        self.assertEqual(t["tool_calls"], 3)
        self.assertEqual(t["files_edited"], 1)
        self.assertEqual(t["verify_passed"], 0)
        self.assertEqual(t["corrected"], 1)
        self.assertEqual(t["outcome"], "failure")
        self.assertEqual(t["input_tokens"], 300)  # m1, m2, m3 — m1 counted once despite two lines

    def test_second_task_success_and_sidechain_skipped(self):
        t = self.tasks[1]
        self.assertEqual([c["tool"] for c in t["calls"]], ["Agent", "Edit", "PowerShell"])
        self.assertEqual(t["verify_passed"], 1)
        self.assertEqual(t["outcome"], "success")

    def test_store_is_idempotent_and_sanitized(self):
        conn = db.connect(":memory:")
        claude_code.store(conn, self.session, self.tasks)
        claude_code.store(conn, self.session, self.tasks)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 4)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM tool_calls").fetchone()[0], 6)
        prompt = conn.execute("SELECT prompt FROM tasks WHERE seq = 0").fetchone()[0]
        self.assertNotIn("sk-ant-", prompt)
        self.assertIn("[REDACTED_SECRET]", prompt)


class HookTests(unittest.TestCase):
    def test_hook_records_event_and_imports_on_stop(self):
        path = write_transcript(TRANSCRIPT)
        try:
            conn = db.connect(":memory:")
            claude_code.handle_hook(conn, {"hook_event_name": "PostToolUse", "session_id": SID,
                                           "tool_name": "Bash", "tool_input": {"command": "pytest"},
                                           "tool_response": {"is_error": True}, "cwd": "/home/alice/x"})
            row = conn.execute("SELECT * FROM live_events").fetchone()
            self.assertEqual((row["tool"], row["summary"], row["is_error"]), ("Bash", "pytest", 1))
            self.assertIn("<USER>", row["cwd"])
            claude_code.handle_hook(conn, {"hook_event_name": "Stop", "session_id": SID,
                                           "transcript_path": path}, background_import=False)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0], 4)
        finally:
            os.remove(path)

    def test_cli_hook_never_fails_or_prints(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"TIDOS_BRAIN_DB": os.path.join(tmp, "b.db")}), \
                mock.patch("sys.stdin", io.StringIO("this is not json")), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            self.assertEqual(cli.main(["hook"]), 0)
            self.assertEqual(out.getvalue(), "")


class InstallerTests(unittest.TestCase):
    def test_install_preserves_user_hooks_and_uninstalls_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings = os.path.join(tmp, "settings.json")
            user_hook = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mine"}]}
            with open(settings, "w") as f:
                json.dump({"model": "opus", "hooks": {"PostToolUse": [user_hook]}}, f)
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                cli.main(["install-hooks", "--settings", settings])
                cli.main(["install-hooks", "--settings", settings])  # idempotent
            data = json.load(open(settings))
            self.assertEqual(data["model"], "opus")
            self.assertEqual(len(data["hooks"]["PostToolUse"]), 2)
            self.assertIn(user_hook, data["hooks"]["PostToolUse"])
            self.assertEqual(set(data["hooks"]), set(cli.HOOK_EVENTS))
            with mock.patch("sys.stdout", new_callable=io.StringIO):
                cli.main(["install-hooks", "--settings", settings, "--uninstall"])
            data = json.load(open(settings))
            self.assertEqual(data["hooks"], {"PostToolUse": [user_hook]})

    @unittest.skipUnless(os.name == "nt", "pythonw.exe exists only on Windows")
    def test_hook_uses_windowless_python_on_windows(self):
        # python.exe would flash a console window on every tool call
        windowless = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.isfile(windowless):
            self.skipTest("no pythonw.exe next to this interpreter")
        self.assertTrue(cli._hook_command().startswith('"%s"' % windowless))


if __name__ == "__main__":
    unittest.main()
