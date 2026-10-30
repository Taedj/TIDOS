"""Tests for Tool Scout recipes: detect, install, configure, verify, roll back, undo (temporary projects only)."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import control, db, trust  # noqa: E402
from tidos_scout import recipes, scout  # noqa: E402


def runner(code):
    calls = []

    def run(argv, **kw):
        calls.append((argv, kw["cwd"]))
        return SimpleNamespace(returncode=code, stdout="checked\n", stderr="")
    run.calls = calls
    return run


class RecipeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": os.path.join(self.tmp.name, "home"),
                                                "TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")})
        self.env.start()
        self.patches = [mock.patch.object(recipes.scout, "installed", lambda *a, **k: True),
                        mock.patch.object(recipes.shutil, "which", lambda exe: exe)]
        for p in self.patches:
            p.start()
        self.project = os.path.join(self.tmp.name, "proj")
        os.makedirs(os.path.join(self.project, "tests"))
        self.write("pyproject.toml", "[project]\nname = 'x'\n")
        self.write("app.py", "print(1)\n")

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.env.stop()
        self.tmp.cleanup()

    def write(self, rel, text):
        path = os.path.join(self.project, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def path(self, rel):
        return os.path.join(self.project, rel)

    def test_ruff_setup_verify_and_undo(self):
        plan = recipes.plan("ruff", self.project)
        self.assertTrue(plan["applies"], plan)
        run = runner(1)                                           # ruff ran and found issues: set up fine
        result = recipes.apply("ruff", self.project, runner=run)
        self.assertTrue(result["ok"], result)
        self.assertEqual([s[0] for s in result["steps"]], ["detect", "configure", "verify"])
        self.assertEqual(run.calls[0][1], self.project)           # verified inside the project
        self.assertTrue(os.path.isfile(self.path("ruff.toml")))
        self.assertEqual(recipes.configured(self.project)[0]["tool"], "ruff")
        self.assertFalse(recipes.plan("ruff", self.project)["applies"])  # configured now: not needed again
        self.assertEqual(recipes.unconfigure("ruff", self.project), ["ruff.toml: removed"])
        self.assertFalse(os.path.exists(self.path("ruff.toml")))
        with self.assertRaises(ValueError):
            recipes.unconfigure("ruff", self.project)

    def test_failed_verify_rolls_back(self):
        result = recipes.apply("pytest", self.project, runner=runner(4))   # 4 = pytest usage error
        self.assertFalse(result["ok"])
        self.assertEqual(result["steps"][-1][0], "rollback")
        self.assertFalse(os.path.exists(self.path("pytest.ini")))
        self.assertEqual(recipes.configured(), [])

    def test_existing_config_and_your_edits_are_never_touched(self):
        self.write("ruff.toml", "line-length = 99\n")
        result = recipes.apply("ruff", self.project, runner=runner(0))
        self.assertEqual(result["steps"][0][:2], ["detect", "stop"])
        with open(self.path("ruff.toml"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "line-length = 99\n")
        os.remove(self.path("ruff.toml"))
        recipes.apply("ruff", self.project, runner=runner(0))
        self.write("ruff.toml", "line-length = 100\n")             # you edited it afterwards
        self.assertEqual(recipes.unconfigure("ruff", self.project), ["ruff.toml: changed since, left alone"])
        self.assertTrue(os.path.exists(self.path("ruff.toml")))

    def test_gitleaks_hook_and_your_own_hook(self):
        self.assertIn("not a git repository", recipes.plan("gitleaks", self.project)["reason"])
        os.makedirs(self.path(".git/hooks"))
        self.assertTrue(recipes.apply("gitleaks", self.project, runner=runner(0))["ok"])
        with open(self.path(".git/hooks/pre-commit"), encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith(recipes.HOOK_HEAD))
        self.assertIn("gitleaks git --pre-commit --staged", text)
        self.assertIn("already set up", recipes.plan("gitleaks", self.project)["reason"])
        recipes.unconfigure("gitleaks", self.project)
        self.assertFalse(os.path.exists(self.path(".git/hooks/pre-commit")))
        self.write(".git/hooks/pre-commit", "#!/bin/sh\nnpm test\n")
        self.assertIn("its own pre-commit hook", recipes.plan("gitleaks", self.project)["reason"])

    def test_install_only_through_the_approved_path(self):
        with mock.patch.object(recipes.scout, "installed", lambda *a, **k: False):
            refused = lambda name: (_ for _ in ()).throw(scout.InstallRefused("the tool_install switch is off"))
            result = recipes.apply("ruff", self.project, runner=runner(0), install=refused)
            self.assertEqual(result["steps"][-1], ["install", "stop", "the tool_install switch is off"])
            self.assertFalse(os.path.exists(self.path("ruff.toml")))
            ok = recipes.apply("ruff", self.project, runner=runner(0),
                               install=lambda name: {"ok": True, "detail": "installed"})
            self.assertEqual([s[0] for s in ok["steps"]], ["detect", "install", "configure", "verify"])
        with self.assertRaises(ValueError):
            recipes.plan("semgrep", self.project)                 # no recipe
        recipes.unconfigure("ruff", self.project)
        with mock.patch.object(recipes.shutil, "which", lambda exe: None):   # the tool does not start
            result = recipes.apply("ruff", self.project, runner=runner(0))
        self.assertEqual(result["steps"][-2], ["verify", "failed", "ruff not found"])
        self.assertFalse(os.path.exists(self.path("ruff.toml")))

    def test_undo_through_the_action_journal(self):
        recipes.apply("ruff", self.project, runner=runner(0))
        action = trust.record("configure_tool", "Set up ruff", target={"tool": "ruff", "project": self.project})
        self.assertIn("ruff.toml: removed", trust.undo(action["id"])["undo_detail"])
        self.assertFalse(os.path.exists(self.path("ruff.toml")))

    def test_autopilot_proposes_setups_for_active_projects(self):
        from tidos_dashboard import autopilot
        conn = db.connect(":memory:")
        conn.execute("INSERT INTO sessions (id, source, model, cwd, project) VALUES ('s', 'claude-code', 'm', ?, 'proj')",
                     (self.project,))
        conn.execute("INSERT INTO tasks (session_id, seq, started_at) VALUES ('s', 0, ?)",
                     (datetime.now(timezone.utc).isoformat(),))
        conn.commit()
        control.set_switch("autopilot", True)
        with mock.patch("tidos_brain.claude_code.is_synthetic", lambda cwd: False):
            recs = {r["key"]: r for r in autopilot.decide(conn)}
        setup = recs["setup:ruff:%s" % self.project]
        self.assertEqual((setup["job"], setup["auto"]), ("configure_tool", False))   # trust: propose first
        self.assertIn("setup:pytest:%s" % self.project, recs)
        self.assertNotIn("setup:gitleaks:%s" % self.project, recs)  # not a git repository
        conn.close()


if __name__ == "__main__":
    unittest.main()
