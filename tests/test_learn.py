"""Tests for tidos_learn: classification, check normalization, playbook distillation, notes, brief priority."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import claude_code, db  # noqa: E402
from tidos_learn import classify, distill  # noqa: E402
from tidos_session import brief  # noqa: E402

CWD = r"D:\work\Dev\APP"


class ClassifyTests(unittest.TestCase):
    def test_types_from_words(self):
        self.assertEqual(classify.task_type("deploy web version to hosting", []), "deploy")
        self.assertEqual(classify.task_type("the logout button in setting screen not work", []), "bugfix")
        self.assertEqual(classify.task_type("ça ne marche pas", []), "bugfix")
        self.assertEqual(classify.task_type("add a zoom option to the scanner", []), "feature")
        self.assertEqual(classify.task_type("review the admin screens", []), "review")

    def test_types_from_actions_when_words_say_nothing(self):
        self.assertEqual(classify.task_type("Phase 1", [{"kind": "edit", "summary": "lib/a.dart"}]), "feature")
        self.assertEqual(classify.task_type("go", [{"kind": "read", "summary": "a.py"}]), "question")
        self.assertEqual(classify.task_type("ok", [{"kind": "exec", "summary": "firebase deploy --only hosting"}]), "deploy")

    def test_stacks(self):
        calls = [{"kind": "read", "summary": r"D:\x\lib\main.dart"}, {"kind": "edit", "summary": "firestore.rules"},
                 {"kind": "exec", "summary": "flutter analyze"}, {"kind": "edit", "summary": "README.md"}]
        self.assertEqual(classify.stacks(calls), ["flutter/dart", "firebase"])
        self.assertEqual(classify.stacks([]), ["general"])


class NormalizeTests(unittest.TestCase):
    def test_reusable_checks(self):
        cases = {
            "cd D:/work/Dev/ZTAP && flutter analyze --no-fatal-infos 2>&1 | head -60": "flutter analyze",
            'cd "D:/a b" && flutter analyze lib/screens/x.dart': "flutter analyze",
            "python -m pytest -q tests": "python -m pytest",
            r'"C:\Python314\python.exe" -m pytest -q': "python -m pytest",
            "npm run build": "npm run build",
            "flutter test test/widget_test.dart": "flutter test",
        }
        for cmd, expected in cases.items():
            with self.subTest(cmd=cmd):
                self.assertEqual(distill.normalize_check(cmd), expected)

    def test_one_off_commands_are_not_checks(self):
        for cmd in ("python -I - <<'EOF' import io", r'P="C:\x" && ls', "python report.py data.json",
                    "firebase deploy --only hosting", "git status"):
            with self.subTest(cmd=cmd):
                self.assertIsNone(distill.normalize_check(cmd))

    def test_relpath(self):
        self.assertEqual(distill.relpath(CWD + r"\lib\main.dart", CWD), "lib/main.dart")
        self.assertIsNone(distill.relpath(r"C:\Users\<USER>\AppData\Local\Temp\x.py", CWD))
        self.assertIsNone(distill.relpath(r"D:\other\file.py", CWD))
        self.assertEqual(distill.relpath("lib/**/*.dart", CWD), "lib/**/*.dart")


def add_session(conn, sid, cwd, project, model, tasks):
    """tasks: list of (prompt, outcome, verify_passed, corrected, calls, checks)."""
    conn.execute("INSERT INTO sessions (id, source, model, cwd, project) VALUES (?,?,?,?,?)",
                 (sid, "claude-code", model, cwd, project))
    for seq, (prompt, outcome, vp, corrected, calls, checks) in enumerate(tasks):
        cur = conn.execute(
            "INSERT INTO tasks (session_id, seq, prompt, model, started_at, tool_calls, tool_errors, files_edited,"
            " verify_runs, verify_passed, corrected, score, outcome) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (sid, seq, prompt, model, "2026-10-24T10:%02d:00Z" % seq, len(calls), 0,
             sum(1 for k, _ in calls if k == "edit"), len(checks), vp, corrected, 0.8, outcome))
        for kind, summary in calls:
            conn.execute("INSERT INTO tool_calls (task_id, tool, kind, summary) VALUES (?,?,?,?)",
                         (cur.lastrowid, {"read": "Read", "edit": "Edit", "exec": "Bash"}[kind], kind, summary))
        for cmd, ok in checks:
            conn.execute("INSERT INTO verifications (task_id, command, passed) VALUES (?,?,?)", (cur.lastrowid, cmd, ok))
    conn.commit()


class DistillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": os.path.join(self.tmp.name, "tidos")})
        self.env.start()
        self.conn = db.connect(":memory:")
        fix_calls = [("read", CWD + r"\lib\screens\login.dart"), ("edit", CWD + r"\lib\screens\login.dart"),
                     ("exec", "cd D:/work/Dev/APP && flutter analyze 2>&1 | tail")]
        add_session(self.conn, "s1", CWD, "APP", "claude-opus-5-5", [
            ("fix the login button crash on android", "success", 1, 0, fix_calls,
             [("cd D:/x && flutter analyze", 0), ("flutter analyze lib", 1)]),
            ("the logout button is broken after update", "success", 1, 0, fix_calls, [("flutter analyze", 1)]),
            ("fix the settings screen error please", "failure", 0, 1, fix_calls, [("flutter analyze", 0)]),
            ("no, the error is in the settings service not the screen", "unknown", None, 0, [], []),
        ])
        # a weak model that never verified: not a learning example
        add_session(self.conn, "s2", CWD, "APP", "opencode/big-pickle", [
            ("fix the crash in profile page", "unknown", None, 0, fix_calls, []),
        ])
        # a TIDOS test run: never learned from
        add_session(self.conn, "s3", r"C:\Users\<USER>\dungeon-runs\r1\python\x", "x-1", "claude-opus-5-5", [
            ("fix the bug in pager.py now", "success", 1, 0, [("edit", "pager.py")], [("python -m pytest", 1)]),
            ("fix the bug in cache.py now", "success", 1, 0, [("edit", "cache.py")], [("python -m pytest", 1)]),
        ])

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()

    def test_learning_set(self):
        tasks = distill.load_tasks(self.conn)
        self.assertEqual({t["project"] for t in tasks}, {"APP"})        # synthetic run excluded
        examples = [t["prompt"] for t in tasks if distill.is_learning_example(t)]
        self.assertEqual(examples, ["fix the login button crash on android", "the logout button is broken after update"])
        corrected = next(t for t in tasks if t["corrected"])
        self.assertEqual(corrected["correction"], "no, the error is in the settings service not the screen")

    def test_project_playbook_content(self):
        written = distill.distill(self.conn)
        paths = {os.path.relpath(w[0], distill.playbooks_dir()).replace("\\", "/") for w in written}
        self.assertEqual(paths, {"app/bugfix.md"})
        with open(os.path.join(distill.playbooks_dir(), "app", "bugfix.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("project: APP", text)
        self.assertIn("evidence: 2 tasks (2 verified, 2 by strong models)", text)
        self.assertIn("`lib/screens/`", text)
        self.assertIn("Verify with `flutter analyze`", text)
        self.assertIn("`flutter analyze` failed first in 1 task(s)", text)
        self.assertIn('with: "no, the error is in the settings service not the screen"', text)
        self.assertNotIn("dungeon-runs", text)
        rows = self.conn.execute("SELECT task_type, uses, successes FROM playbooks").fetchall()
        self.assertEqual([tuple(r) for r in rows], [("bugfix", 2, 2)])

    def test_regeneration_removes_stale_but_keeps_notes(self):
        distill.distill(self.conn)
        stale = os.path.join(distill.playbooks_dir(), "old", "deploy.md")
        os.makedirs(os.path.dirname(stale))
        with open(stale, "w", encoding="utf-8") as f:
            f.write("---\n%s\ntype: deploy\n---\nold\n" % distill.GENERATED_MARK)
        notes = distill.add_note("APP", "flutter/dart", "Login logic lives in lib/services/auth_service.dart.")
        distill.distill(self.conn)
        self.assertFalse(os.path.exists(stale))
        self.assertTrue(os.path.exists(notes))

    def test_brief_prefers_this_projects_playbooks_and_notes(self):
        distill.distill(self.conn)
        distill.add_note("APP", "flutter/dart", "Always run flutter gen-l10n after editing lib/l10n/*.arb.")
        other = os.path.join(distill.playbooks_dir(), "_general", "feature--flutter-dart.md")
        os.makedirs(os.path.dirname(other))
        with open(other, "w", encoding="utf-8") as f:
            f.write("---\ntype: feature\nstack: flutter/dart\nproject: any\nconfidence: 0.95\n---\nGENERAL ADVICE\n")
        found = brief._playbooks(["flutter/dart"], "APP", limit=2)
        self.assertEqual([name for _, name, _ in found], ["APP / notes", "APP / bugfix"])
        text = brief.guide_brief({"model": "m", "tier": "weak"},
                                 {"name": "APP", "stack": ["flutter/dart"], "checks": ["flutter analyze"], "notes": []})
        self.assertIn("flutter gen-l10n", text)
        self.assertLessEqual(len(text.encode("utf-8")), brief.GUIDE_LIMIT)


class SyntheticTests(unittest.TestCase):
    def test_is_synthetic(self):
        self.assertTrue(claude_code.is_synthetic(r"C:\Users\<USER>\dungeon-runs\x"))
        self.assertTrue(claude_code.is_synthetic(r"C:\Users\<USER>\.tidos\eval-runs\x"))
        self.assertFalse(claude_code.is_synthetic(r"D:\work\Dev\ZTAP"))


if __name__ == "__main__":
    unittest.main()
