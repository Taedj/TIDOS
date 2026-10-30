"""Tests for connecting TIDOS to AI tools (tidos_session.wire) and the MCP server's client detection."""
import json
import os
import sys
import tempfile
import tomllib
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_mcp import server  # noqa: E402
from tidos_session import wire  # noqa: E402


class WireTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = self.tmp.name
        self.oc = os.path.join(self.home, ".config", "opencode")
        os.makedirs(self.oc)
        self.config = os.path.join(self.oc, "opencode.json")
        self.original = {"$schema": "https://opencode.ai/config.json", "provider": {"x": {"npm": "y"}}}
        self.write(self.config, json.dumps(self.original))
        self.agents = os.path.join(self.oc, "AGENTS.md")
        self.write(self.agents, "# My rules\nAlways answer in English.\n")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    def read(self, path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    def row(self, tool_id):
        return next(r for r in wire.tools(self.home) if r["id"] == tool_id)

    def test_connect_adds_only_tidos_and_disconnect_restores(self):
        self.assertFalse(self.row("opencode")["connected"])
        wire.connect("opencode", self.home)
        data = json.loads(self.read(self.config))
        self.assertEqual(data["provider"], self.original["provider"])                  # the rest is kept
        self.assertEqual(data["mcp"]["tidos"]["type"], "local")
        self.assertTrue(data["mcp"]["tidos"]["command"][-1].endswith("__main__.py"))
        text = self.read(self.agents)
        self.assertTrue(text.startswith("# My rules\nAlways answer in English.\n"))
        self.assertIn("tidos_guide", text)
        self.assertTrue(os.path.exists(self.config + ".tidos-backup"))
        self.assertTrue(self.row("opencode")["connected"])
        self.assertEqual({s for _, s in wire.connect("opencode", self.home)}, {"current"})  # idempotent
        self.assertEqual(self.read(self.agents).count(wire.BEGIN), 1)
        wire.disconnect("opencode", self.home)
        self.assertEqual(json.loads(self.read(self.config)), self.original)
        self.assertEqual(self.read(self.agents), "# My rules\nAlways answer in English.\n")
        self.assertFalse(self.row("opencode")["connected"])

    def test_created_instructions_file_is_removed_on_disconnect(self):
        os.remove(self.agents)
        wire.connect("opencode", self.home)
        self.assertIn(wire.BEGIN, self.read(self.agents))
        wire.disconnect("opencode", self.home)
        self.assertFalse(os.path.exists(self.agents))

    def test_config_with_comments_is_left_alone(self):
        self.write(self.config, '{\n  // my comment\n  "provider": {}\n}\n')
        status = dict(wire.connect("opencode", self.home))
        self.assertIn("skipped", status[self.config])
        self.assertIn("// my comment", self.read(self.config))

    def test_gemini_cli_and_antigravity_share_their_rules_file(self):
        gem = os.path.join(self.home, ".gemini")
        self.write(os.path.join(gem, "settings.json"), json.dumps({"theme": "dark"}))
        os.makedirs(os.path.join(gem, "config"))
        rules = os.path.join(gem, "GEMINI.md")
        wire.connect("gemini-cli", self.home)
        wire.connect("antigravity", self.home)
        self.assertEqual(json.loads(self.read(os.path.join(gem, "settings.json")))["theme"], "dark")
        self.assertIn("args", json.loads(self.read(os.path.join(gem, "config", "mcp_config.json")))["mcpServers"]["tidos"])
        self.assertEqual(self.read(rules).count(wire.BEGIN), 1)
        self.assertIn("kept", dict(wire.disconnect("gemini-cli", self.home))[rules])  # Antigravity still uses it
        self.assertIn(wire.BEGIN, self.read(rules))
        self.assertTrue(self.row("antigravity")["connected"])
        self.assertFalse(self.row("gemini-cli")["connected"])
        wire.disconnect("antigravity", self.home)
        self.assertFalse(os.path.exists(rules))

    def test_codex_toml_and_cline_rules_file(self):
        toml = os.path.join(self.home, ".codex", "config.toml")
        self.write(toml, 'model = "o4"\n')
        wire.connect("codex", self.home)
        parsed = tomllib.loads(self.read(toml))
        self.assertEqual(parsed["model"], "o4")
        self.assertTrue(parsed["mcp_servers"]["tidos"]["args"][-1].endswith("__main__.py"))
        wire.disconnect("codex", self.home)
        self.assertEqual(self.read(toml), 'model = "o4"\n')
        cline_rules = os.path.join(self.home, "Documents", "Cline", "Rules", "tidos.md")
        os.makedirs(os.path.join(self.home, ".cline"))
        wire.connect("cline", self.home)
        self.assertIn("tidos_verify", self.read(cline_rules))
        self.assertTrue(self.row("cline")["connected"])
        wire.disconnect("cline", self.home)
        self.assertFalse(os.path.exists(cline_rules))

    def test_unknown_manual_and_plugin_tools(self):
        with tempfile.TemporaryDirectory() as empty:
            self.assertFalse([r for r in wire.tools(empty) if r["installed"]])   # nothing found, nothing written
            self.assertEqual(os.listdir(empty), [])
        rows = {r["id"]: r for r in wire.tools(self.home)}
        self.assertEqual((rows["claude-code"]["how"], rows["cursor"]["how"]), ("plugin", "manual"))
        for tool in ("cursor", "claude-code", "nope"):
            with self.assertRaises(ValueError):
                wire.connect(tool, self.home)
        self.assertIn('"mcpServers"', wire.manual_snippet())

    def test_start_hint_only_for_an_installed_unconnected_tool(self):
        self.assertIn("not connected to OpenCode", wire.hint("opencode", self.home))
        wire.connect("opencode", self.home)
        self.assertEqual(wire.hint("opencode", self.home), "")
        self.assertEqual(wire.hint("codex", self.home), "")                    # not installed
        self.assertEqual(wire.hint("claude-code", self.home), "")              # plugin


class McpClientTests(unittest.TestCase):
    def setUp(self):
        server.CLIENT["tool"] = "auto"
        server.STARTED.clear()

    def test_client_name_sets_the_tool(self):
        self.assertEqual(server.client_tool("opencode"), "opencode")
        self.assertEqual(server.client_tool("claude-code"), "claude-code")
        self.assertEqual(server.client_tool("gemini-cli-mcp-client"), "gemini-cli")
        self.assertEqual(server.client_tool(None), "auto")
        server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2025-06-18", "clientInfo": {"name": "opencode", "version": "1"}}})
        self.assertEqual(server.CLIENT["tool"], "opencode")

    def test_guide_starts_the_session_when_the_model_skipped_it(self):
        server.CLIENT["tool"] = "opencode"
        calls = []
        started = {"tool": "opencode", "model": "m", "model_source": "s", "tier": "weak", "tier_rule": "r",
                   "mode": "guide"}
        with tempfile.TemporaryDirectory() as project, \
                mock.patch.object(server.session_cli, "start",
                                  lambda tool, model, project, learn: calls.append(tool) or (started, {}, "BRIEF")), \
                mock.patch.object(server.session_cli, "report", lambda s, f: "REPORT"), \
                mock.patch.object(server.guide, "guidance", lambda request, project: (None, "GUIDANCE")):
            first = server.tool_guide({"request": "fix the login", "project_dir": project})["content"][0]["text"]
            second = server.tool_guide({"request": "add a test", "project_dir": project})["content"][0]["text"]
        self.assertEqual(calls, ["opencode"])                       # started once, as the client tool
        self.assertIn("BRIEF", first)
        self.assertTrue(first.endswith("GUIDANCE"))
        self.assertEqual(second, "GUIDANCE")


if __name__ == "__main__":
    unittest.main()
