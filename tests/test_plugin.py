"""The Claude Code plugin is in sync with its sources and its launcher works."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "plugin", "bin"))
import build_plugin  # noqa: E402
import tidos_launch  # noqa: E402
from tidos_brain import cli as brain_cli  # noqa: E402


class PluginTests(unittest.TestCase):
    def test_plugin_is_up_to_date(self):
        with mock.patch("sys.argv", ["build_plugin.py", "--check"]), mock.patch("sys.stdout"):
            self.assertEqual(build_plugin.main(), 0, "run: python scripts/build_plugin.py")

    def test_hooks_cover_every_brain_event(self):
        with open(os.path.join(ROOT, "plugin", "hooks", "hooks.json"), encoding="utf-8") as f:
            hooks = json.load(f)["hooks"]
        self.assertEqual(set(hooks), set(brain_cli.HOOK_EVENTS))
        for groups in hooks.values():
            self.assertIn("${CLAUDE_PLUGIN_ROOT}/bin/tidos_launch.py", groups[0]["hooks"][0]["command"])

    def test_manifest_version_matches(self):
        with open(os.path.join(ROOT, "plugin", ".claude-plugin", "plugin.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["version"], build_plugin.version())

    def test_launcher_finds_repo_and_is_silent_without_it(self):
        with mock.patch.dict(os.environ, {"TIDOS_REPO": ROOT}):
            self.assertEqual(os.path.normcase(tidos_launch.find_repo()), os.path.normcase(ROOT))
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, TIDOS_REPO="", USERPROFILE=tmp, HOME=tmp)
            proc = subprocess.run([sys.executable, "-I", os.path.join(ROOT, "plugin", "bin", "tidos_launch.py"), "hook"],
                                  input="{}", capture_output=True, text=True, cwd=tmp, env=env, timeout=60)
            self.assertEqual((proc.returncode, proc.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
