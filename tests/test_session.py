"""Tests for tidos_session: tool/model detection, tiers, project facts, LEARN/GUIDE briefs."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_session import brief, cli, detect, memory  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.tidos = os.path.join(self.home, ".tidos")
        self.project = os.path.join(self.tmp.name, "My Project")
        os.makedirs(self.project)
        real_expanduser = os.path.expanduser
        self.patches = [
            mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tidos}),
            mock.patch("os.path.expanduser",
                       side_effect=lambda p: p.replace("~", self.home, 1) if p.startswith("~") else real_expanduser(p)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()


class TierTests(Isolated):
    def test_default_registry(self):
        cases = {"claude-opus-5-5": "frontier", "claude-sonnet-5-5": "frontier", "claude-haiku-4-5": "medium",
                 "google/gemini-3.1-pro-preview": "frontier", "google/gemini-2.5-flash": "medium",
                 "google/gemini-3.1-flash-lite": "weak", "opencode/glm-5.3-flash-free": "weak",
                 "opencode/big-pickle": "weak", "ollama/qwen3:8b": "weak", "unknown": "weak", "": "weak"}
        for model, tier in cases.items():
            with self.subTest(model=model):
                self.assertEqual(detect.tier_for(model)[0], tier)

    def test_user_override_wins(self):
        write(os.path.join(self.tidos, "models.json"), json.dumps({"rules": [["opencode/big-pickle", "frontier"]]}))
        self.assertEqual(detect.tier_for("opencode/big-pickle"), ("frontier", "opencode/big-pickle"))
        self.assertEqual(detect.tier_for("claude-haiku-4-5")[0], "medium")  # defaults still apply


class DetectionTests(Isolated):
    def test_tool_from_env(self):
        self.assertEqual(detect.detect_tool(env={"CLAUDECODE": "1"}), "claude-code")
        self.assertEqual(detect.detect_tool(env={}), "unknown")
        self.assertEqual(detect.detect_tool("OpenCode", env={"CLAUDECODE": "1"}), "opencode")

    def test_explicit_model_wins(self):
        self.assertEqual(detect.detect_model("opencode", "zai/glm-5.3", self.project), ("zai/glm-5.3", "given"))

    def test_opencode_state(self):
        write(os.path.join(self.home, ".local", "state", "opencode", "model.json"),
              json.dumps({"recent": [{"providerID": "opencode", "modelID": "big-pickle"},
                                     {"providerID": "google", "modelID": "gemini-2.5-flash"}]}))
        self.assertEqual(detect.detect_model("opencode", "auto", self.project), ("opencode/big-pickle", "opencode state"))

    def test_claude_transcript(self):
        encoded = "".join(c if c.isalnum() else "-" for c in os.path.abspath(self.project))
        lines = [{"type": "user", "message": {"content": "hi"}},
                 {"type": "assistant", "message": {"model": "claude-haiku-4-5", "content": []}},
                 {"type": "assistant", "message": {"model": "claude-opus-5-5", "content": []}}]
        write(os.path.join(self.home, ".claude", "projects", encoded, "s.jsonl"),
              "\n".join(json.dumps(l) for l in lines) + "\n")
        self.assertEqual(detect.detect_model("claude-code", None, self.project), ("claude-opus-5-5", "claude transcript"))

    def test_undetectable(self):
        self.assertEqual(detect.detect_model("unknown", "unknown", self.project), ("unknown", "not detected"))

    def test_project_facts(self):
        write(os.path.join(self.project, "pubspec.yaml"), "name: app\n")
        write(os.path.join(self.project, "firebase.json"), "{}")
        write(os.path.join(self.project, "package.json"), json.dumps({"scripts": {"test": "jest", "build": "x"}}))
        facts = detect.project_facts(self.project)
        self.assertEqual(facts["name"], "My Project")
        self.assertEqual(facts["stack"], ["flutter/dart", "node/javascript", "firebase"])
        self.assertEqual(facts["checks"], ["flutter analyze", "flutter test", "npm run test", "npm run build"])
        self.assertTrue(any("deploy" in n for n in facts["notes"]))


class BriefTests(Isolated):
    def facts(self, stack=("python",)):
        return {"name": "p", "stack": list(stack), "checks": ["python -m pytest -q"], "notes": []}

    def test_guide_brief_matching_playbooks_and_size_cap(self):
        write(os.path.join(self.tidos, "playbooks", "bugfix", "python.md"),
              "---\nstack: python\n---\nRead the failing test first.\n" + "x" * 5000)
        write(os.path.join(self.tidos, "playbooks", "deploy", "flutter.md"), "---\nstack: flutter/dart\n---\nFlutter only\n")
        text = brief.guide_brief({"model": "opencode/big-pickle", "tier": "weak"}, self.facts())
        self.assertLessEqual(len(text.encode("utf-8")), brief.GUIDE_LIMIT)
        self.assertIn("TIDOS GUIDE MODE", text)
        self.assertIn("Read the failing test first.", text)
        self.assertNotIn("Flutter only", text)
        self.assertIn("python -m pytest -q", text)

    def test_guide_brief_without_playbooks(self):
        text = brief.guide_brief({"model": "m", "tier": "weak"}, dict(self.facts(), checks=[]))
        self.assertIn("None yet", text)
        self.assertIn("No test command detected", text)

    def test_start_learn_vs_guide(self):
        session, _, text = cli.start("claude-code", "claude-opus-5-5", self.project)
        self.assertEqual((session["tier"], session["mode"]), ("frontier", "learn"))
        self.assertIn("TIDOS LEARN MODE", text)
        session, _, text = cli.start("opencode", "opencode/glm-5.3-flash-free", self.project)
        self.assertEqual(session["mode"], "guide")
        with open(os.path.join(self.tidos, "session.json"), encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["model"], "opencode/glm-5.3-flash-free")
        with open(os.path.join(self.tidos, "brief.md"), encoding="utf-8") as f:
            self.assertEqual(f.read(), text)
        # every tool (Antigravity, OpenCode, Gemini CLI...) learns /TIDOSZIT from the brief itself
        self.assertIn("If the user types `/TIDOSZIT`", text)
        self.assertIn("tidoszit.", text)
        self.assertTrue(os.path.isfile(os.path.join(self.home, ".claude", "commands", "TIDOSZIT.md")))  # Claude Code


class AgentsMdTests(Isolated):
    def test_block_is_inserted_then_replaced_and_keeps_user_content(self):
        write(os.path.join(self.project, "pubspec.yaml"), "name: app")
        write(os.path.join(self.project, "AGENTS.md"), "# My rules\n\nUse tabs.\n")
        path = cli.write_agents_md(self.project, "opencode")
        cli.write_agents_md(self.project, "opencode")                  # idempotent
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith("# My rules"))
        self.assertEqual(text.count(cli.AGENTS_BEGIN), 1)
        self.assertIn("START TIDOS", text)
        self.assertIn("`flutter analyze`", text)
        self.assertIn("tidos_guide", text)

    def test_block_never_contains_private_learning(self):
        write(os.path.join(self.tidos, "playbooks", "my-project", "notes.md"), "- SECRET NOTE about the project")
        write(os.path.join(self.tidos, "memory", "LEARNED_PREFERENCES.md"), "## My Project\n- PRIVATE RULE")
        block = cli.agents_md_block(self.project)
        self.assertNotIn("SECRET NOTE", block)
        self.assertNotIn("PRIVATE RULE", block)


class MemoryMigrationTests(Isolated):
    def test_personal_memory_leaves_the_repo(self):
        repo_mem = os.path.join(self.tmp.name, "repo-memory")
        write(os.path.join(repo_mem, "LESSONS.md"), "# Lessons\n- my private lesson\n")
        write(os.path.join(repo_mem, "SECRET_persona.md"), "password 1234\n")
        write(os.path.join(repo_mem, "README.md"), "readme\n")
        write(os.path.join(repo_mem, "PATTERNS.md"), memory.template_text("PATTERNS.md"))
        write(os.path.join(self.tidos, "memory", "LESSONS.md"), "# existing private lessons\n")
        moved, kept = memory.migrate(repo_mem)
        self.assertEqual((moved, kept), (["LESSONS.md", "SECRET_persona.md"], ["LESSONS.md"]))
        private = os.path.join(self.tidos, "memory")
        with open(os.path.join(private, "LESSONS.md"), encoding="utf-8") as f:
            self.assertIn("existing private lessons", f.read())          # never overwritten
        with open(os.path.join(private, "LESSONS.from-repo.md"), encoding="utf-8") as f:
            self.assertIn("my private lesson", f.read())                  # repo version kept too
        self.assertTrue(memory.is_template(os.path.join(repo_mem, "LESSONS.md")))
        self.assertFalse(os.path.exists(os.path.join(repo_mem, "SECRET_persona.md")))
        self.assertTrue(os.path.exists(os.path.join(private, "SECRET_persona.md")))
        self.assertTrue(os.path.exists(os.path.join(private, "USER_PROFILE.md")))  # created privately
        self.assertEqual(memory.migrate(repo_mem), ([], []))               # idempotent


class VersionFlagTests(Isolated):
    def test_version_comes_from_version_md(self):
        write(os.path.join(self.tmp.name, "VERSION.md"), "# Version\n\n**Current Version**: 9.8.7\n")
        with mock.patch.object(cli.detect, "REPO_ROOT", self.tmp.name):
            self.assertEqual(cli.version(), "9.8.7")
            out = io.StringIO()
            with mock.patch("sys.stdout", out), self.assertRaises(SystemExit) as exit_:
                cli.main(["--version"])
        self.assertEqual(exit_.exception.code, 0)
        self.assertEqual(out.getvalue(), "9.8.7\n")

    def test_version_unknown_without_version_md(self):
        with mock.patch.object(cli.detect, "REPO_ROOT", self.tmp.name):
            self.assertEqual(cli.version(), "unknown")


class UserCommandTests(Isolated):
    def test_start_tidos_installs_tidoszit_for_the_whole_machine(self):
        from tidos_session import commands
        target = os.path.join(self.tmp.name, "claude-commands")
        written = commands.install(target)
        path = os.path.join(target, "TIDOSZIT.md")
        self.assertEqual(written, [path])
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn(detect.REPO_ROOT.replace("\\", "/"), text)       # this machine's TIDOS folder
        self.assertIn(commands.MARK, text)
        self.assertEqual(commands.install(target), [])                   # already current: untouched
        write(path, "my own version of the command")                     # edited by the user (no marker)
        self.assertEqual(commands.install(target), [])
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "my own version of the command")


if __name__ == "__main__":
    unittest.main()
