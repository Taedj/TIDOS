"""Tests for tidos_evals (dungeon loading, verification, agents sandbox, CLI recording)."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_dashboard import stats  # noqa: E402
from tidos_evals import agents, cli, dungeon  # noqa: E402


class DungeonTests(unittest.TestCase):
    def test_tasks_load_with_required_fields(self):
        tasks = dungeon.load_tasks()
        self.assertGreaterEqual(len(tasks), 17)
        for t in tasks:
            self.assertIn(t.difficulty, list("EDCBAS"), t.id)
            self.assertTrue(t.prompt.strip(), t.id)
            for part in ("fixture", "hidden", "solution"):
                self.assertTrue(os.path.isdir(os.path.join(t.path, part)), "%s missing %s" % (t.id, part))

    def test_python_task_fails_untouched_and_passes_with_solution(self):
        task = dungeon.load_tasks(task="paginate-off-by-one")[0]
        with tempfile.TemporaryDirectory() as tmp:
            work = os.path.join(tmp, "w")
            task.prepare(work, with_tidos=True)
            self.assertTrue(os.path.exists(os.path.join(work, "TASK.md")))
            self.assertTrue(os.path.exists(os.path.join(work, "TIDOS_PROTOCOL.md")))
            self.assertFalse(os.path.exists(os.path.join(work, "hidden_tests")))  # agent never sees them
            self.assertFalse(task.run_verify(work)[0])
            task.prepare(work)
            task.overlay("solution", work)
            self.assertTrue(task.run_verify(work)[0])

    def test_hidden_tests_overwrite_agent_tampering(self):
        task = dungeon.load_tasks(task="paginate-off-by-one")[0]
        with tempfile.TemporaryDirectory() as tmp:
            work = os.path.join(tmp, "w")
            task.prepare(work)
            os.makedirs(os.path.join(work, "hidden_tests"))
            with open(os.path.join(work, "hidden_tests", "test_fake.py"), "w") as f:
                f.write("def test_ok():\n    assert True\n")
            self.assertFalse(task.run_verify(work)[0])  # the fake passing test is wiped first


class AgentTests(unittest.TestCase):
    def test_env_pins_pwd_and_drops_nested_session(self):
        with mock.patch.dict(os.environ, {"PWD": "/caller/repo", "CLAUDECODE": "1"}):
            env = agents._env("/run/dir")
        self.assertEqual(env["PWD"], "/run/dir")
        self.assertNotIn("CLAUDECODE", env)

    def test_opencode_sandbox_denies_by_default(self):
        perm = agents.OPENCODE_SANDBOX["permission"]
        self.assertEqual(perm["bash"]["*"], "deny")
        self.assertEqual(perm["webfetch"], "deny")
        self.assertNotIn("git *", perm["bash"])
        self.assertEqual(perm["bash"]["python *"], "allow")

    def test_claude_tools_are_restricted(self):
        self.assertNotIn("Bash,", agents.CLAUDE_TOOLS + ",")  # never unrestricted Bash
        self.assertNotIn("WebFetch", agents.CLAUDE_TOOLS)

    def test_unknown_agent(self):
        task = dungeon.load_tasks(task="paginate-off-by-one")[0]
        self.assertFalse(agents.attempt("gpt9:x", task, tempfile.gettempdir(), False).ok)


class CliTests(unittest.TestCase):
    def test_run_records_results_and_report_shows_lift(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(cli, "RUNS_DIR", os.path.join(tmp, "runs")), \
                mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            dbp = os.path.join(tmp, "b.db")
            cli.main(["--db", dbp, "run", "--agent", "reference", "--tidos", "on", "--task", "mutable-default"])
            cli.main(["--db", dbp, "run", "--agent", "noop", "--tidos", "both", "--task", "mutable-default"])
            conn = db.connect(dbp)
            rows = conn.execute("SELECT agent, with_tidos, passed FROM evals ORDER BY id").fetchall()
            self.assertEqual([tuple(r) for r in rows], [("reference", 1, 1), ("noop", 0, 0), ("noop", 1, 0)])
            self.assertIn("TIDOS lift for noop: +0 points", out.getvalue())
            # the dashboard board ignores reference/noop sanity agents
            board = stats.dungeons(conn)
            self.assertEqual(board["leaderboard"], [])
            self.assertGreaterEqual(len(board["tasks"]), 17)
            conn.close()

    def test_new_scaffold(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(dungeon, "DUNGEONS", tmp), \
                mock.patch("sys.stdout", new_callable=io.StringIO):
            src = os.path.join(tmp, "buggy")
            os.makedirs(os.path.join(src, ".git"))
            with open(os.path.join(src, "app.py"), "w") as f:
                f.write("x = 1\n")
            self.assertEqual(cli.main(["new", "--suite", "python", "--name", "real-bug", "--source", src]), 0)
            base = os.path.join(tmp, "python", "real-bug")
            self.assertTrue(os.path.exists(os.path.join(base, "fixture", "app.py")))
            self.assertFalse(os.path.exists(os.path.join(base, "fixture", ".git")))
            with open(os.path.join(base, "task.json")) as f:
                self.assertEqual(json.load(f)["suite"], "python")
            self.assertEqual(cli.main(["new", "--suite", "python", "--name", "real-bug"]), 1)


if __name__ == "__main__":
    unittest.main()
