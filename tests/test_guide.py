"""Tests for GUIDE mode just-in-time guidance, the Claude Code hook (inject + stuck), and guided-vs-unguided effect."""
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_session import effect, guide, pbstate  # noqa: E402
from test_learn import add_session  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class GuideTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "tidos")
        self.project = os.path.join(self.tmp.name, "APP")
        write(os.path.join(self.project, "pubspec.yaml"), "name: app\n")
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.home})
        self.env.start()
        pb = os.path.join(self.home, "playbooks", "app")
        write(os.path.join(pb, "bugfix.md"), "---\ntype: bugfix\nstack: flutter/dart\nproject: APP\n---\n"
              "# bugfix: APP\n## How it was done\n1. Screens live in lib/screens/.\n\n## Pitfalls\n- run flutter analyze\n")
        write(os.path.join(pb, "deploy.md"), "---\ntype: deploy\nstack: flutter/dart\nproject: APP\n---\n# deploy: APP\n"
              "1. Version lives in pubspec.yaml.\n")
        write(os.path.join(pb, "notes.md"), "---\ntype: notes\n---\n- (2026-10-24, session-summary) Logout helper: lib/utils/logout.dart\n")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_guidance_matches_the_request(self):
        ttype, text = guide.guidance("the logout button does not work", self.project)
        self.assertEqual(ttype, "bugfix")
        self.assertIn("Reproduce first", text)
        self.assertIn("lib/screens/", text)
        self.assertIn("run flutter analyze", text)
        self.assertIn("Logout helper: lib/utils/logout.dart", text)
        self.assertNotIn("pubspec.yaml", text)            # the deploy playbook is not relevant here
        self.assertLessEqual(len(text.encode("utf-8")), guide.GUIDE_LIMIT)
        ttype, text = guide.guidance("deploy the web version to hosting", self.project)
        self.assertEqual(ttype, "deploy")
        self.assertIn("explicit OK", text)
        self.assertIn("pubspec.yaml", text)

    def test_disabled_playbook_and_usage(self):
        pbstate.set_disabled("app/bugfix.md", True)
        _, text = guide.guidance("fix the logout crash", self.project)
        self.assertNotIn("lib/screens/", text)
        guide.guidance("deploy now", self.project)
        self.assertEqual(pbstate.load()["served"]["app/deploy.md"]["n"], 1)
        guide.guidance("deploy now", self.project, record=False)
        self.assertEqual(pbstate.load()["served"]["app/deploy.md"]["n"], 1)

    def _session(self, mode):
        write(os.path.join(self.home, "session.json"), json.dumps({"mode": mode, "project": self.project}))

    def test_hook_injects_guidance_only_in_guide_mode_and_project(self):
        conn = db.connect(":memory:")
        payload = {"hook_event_name": "UserPromptSubmit", "prompt": "fix the logout bug", "cwd": self.project}
        self._session("learn")
        self.assertEqual(guide.hook_feedback(payload, conn), ("", "", 0))
        self._session("guide")
        out, err, code = guide.hook_feedback(payload, conn)
        self.assertIn("Reproduce first", out)
        self.assertEqual((err, code), ("", 0))
        other = dict(payload, cwd=os.path.join(self.tmp.name, "OTHER"))
        self.assertEqual(guide.hook_feedback(other, conn), ("", "", 0))

    def test_hook_stuck_after_three_identical_failures(self):
        conn = db.connect(":memory:")
        self._session("guide")

        def fail(summary="flutter test", err=1):
            conn.execute("INSERT INTO live_events (ts, session_id, event, tool, summary, is_error) VALUES "
                         "('t','s1','PostToolUse','Bash',?,?)", (summary, err))
            return guide.hook_feedback({"hook_event_name": "PostToolUse", "session_id": "s1", "cwd": self.project}, conn)

        self.assertEqual(fail()[2], 0)
        self.assertEqual(fail()[2], 0)
        out, err, code = fail()
        self.assertEqual(code, 2)
        self.assertIn("STOP changing code", err)
        self.assertEqual(fail("flutter analyze")[2], 0)   # a different command breaks the streak


class EnforcementTests(GuideTests):
    def _ev(self, conn, event, tool=None, summary=None, err=0):
        conn.execute("INSERT INTO live_events (ts, session_id, event, tool, summary, is_error) VALUES "
                     "('t','s1',?,?,?,?)", (event, tool, summary, err))

    def _hook(self, conn, event, **extra):
        return guide.hook_feedback(dict({"hook_event_name": event, "session_id": "s1", "cwd": self.project}, **extra), conn)

    def test_read_before_edit(self):
        conn = db.connect(":memory:")
        self._session("guide")
        self._ev(conn, "UserPromptSubmit", summary="fix the bug")
        self.assertEqual(self._hook(conn, "PreToolUse", tool_name="Edit")[2], 2)
        self.assertEqual(self._hook(conn, "PreToolUse", tool_name="Read")[2], 0)    # only edits are gated
        self._ev(conn, "PostToolUse", "Read", "lib/a.dart")
        self.assertEqual(self._hook(conn, "PreToolUse", tool_name="Edit")[2], 0)
        self._ev(conn, "UserPromptSubmit", summary="next request")                 # new request: read again
        self.assertEqual(self._hook(conn, "PreToolUse", tool_name="Write")[2], 2)

    def test_no_done_without_a_passing_check(self):
        conn = db.connect(":memory:")
        self._session("guide")
        self._ev(conn, "UserPromptSubmit", summary="fix")
        self.assertEqual(self._hook(conn, "Stop")[2], 0)                           # nothing changed: may stop
        self._ev(conn, "PostToolUse", "Read", "lib/a.dart")
        self._ev(conn, "PostToolUse", "Edit", "lib/a.dart")
        out, err, code = self._hook(conn, "Stop")
        self.assertEqual(code, 2)
        self.assertIn("UNVERIFIED", err)
        self.assertEqual(self._hook(conn, "Stop", stop_hook_active=True)[2], 0)    # never loops
        self._ev(conn, "PostToolUse", "Bash", "flutter test", err=1)
        self.assertEqual(self._hook(conn, "Stop")[2], 2)                           # failing check is not enough
        self._ev(conn, "PostToolUse", "Bash", "flutter test", err=0)
        self.assertEqual(self._hook(conn, "Stop")[2], 0)

    def test_learn_mode_is_never_gated(self):
        conn = db.connect(":memory:")
        self._session("learn")
        self._ev(conn, "UserPromptSubmit", summary="fix")
        self._ev(conn, "PostToolUse", "Edit", "lib/a.dart")
        self.assertEqual(self._hook(conn, "PreToolUse", tool_name="Edit")[2], 0)
        self.assertEqual(self._hook(conn, "Stop")[2], 0)


class EffectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tmp.name})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_guided_vs_unguided(self):
        conn = db.connect(":memory:")
        cwd = r"D:\work\Dev\APP"
        add_session(conn, "a", cwd, "APP", "opencode/big-pickle", [
            ("t1", "success", 1, 0, [], []), ("t2", "failure", 0, 0, [], [])])
        add_session(conn, "b", cwd, "APP", "opencode/big-pickle", [("t3", "success", 1, 0, [], [])])
        add_session(conn, "c", cwd, "APP", "claude-opus-5-5", [("t4", "success", 1, 0, [], [])])
        conn.execute("UPDATE sessions SET source = 'opencode'")
        start = datetime(2026, 10, 25, 9, tzinfo=timezone.utc)
        conn.execute("UPDATE tasks SET started_at = ? WHERE session_id = 'b'", ((start + timedelta(hours=1)).isoformat(),))
        conn.execute("UPDATE tasks SET started_at = '2026-10-20T10:00:00+00:00' WHERE session_id = 'a'")
        effect.log_start({"started_at": start.isoformat(), "tool": "opencode", "model": "opencode/big-pickle",
                          "tier": "weak", "mode": "guide", "project": cwd})
        rows = effect.guidance_effect(conn)
        self.assertEqual([r["model"] for r in rows], ["opencode/big-pickle"])   # strong models excluded
        self.assertEqual((rows[0]["guided"]["tasks"], rows[0]["guided"]["pass_rate"]), (1, 100))
        self.assertEqual((rows[0]["unguided"]["tasks"], rows[0]["unguided"]["pass_rate"]), (2, 50))


if __name__ == "__main__":
    unittest.main()
