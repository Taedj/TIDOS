"""Tests for the TIDOS MCP server: JSON-RPC protocol, tools, and the verify allowlist."""
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_mcp import server  # noqa: E402


def rpc(*messages):
    out = io.StringIO()
    server.serve(io.StringIO("".join(json.dumps(m) + "\n" for m in messages) + "not json\n"), out)
    return [json.loads(line) for line in out.getvalue().splitlines()]


class ProtocolTests(unittest.TestCase):
    def test_handshake_list_and_errors(self):
        replies = rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                      {"jsonrpc": "2.0", "method": "notifications/initialized"},
                      {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                      {"jsonrpc": "2.0", "id": 3, "method": "nope"},
                      {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "missing"}})
        self.assertEqual(replies[0]["result"]["protocolVersion"], "2024-11-05")
        self.assertEqual({t["name"] for t in replies[1]["result"]["tools"]},
                         {"tidos_start", "tidos_guide", "tidos_verify", "tidos_recall", "tidos_note", "tidos_propose"})
        self.assertEqual(replies[2]["error"]["code"], -32601)
        self.assertEqual(replies[3]["error"]["code"], -32602)
        self.assertEqual(replies[4]["error"]["code"], -32700)      # parse error, server keeps running
        self.assertEqual(len(replies), 5)                          # the notification got no reply

    def test_unknown_protocol_version_falls_back(self):
        reply = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "1999"}})
        self.assertIn(reply["result"]["protocolVersion"], server.PROTOCOL_VERSIONS)


class VerifyTests(unittest.TestCase):
    def test_allowlist(self):
        ok = [["python", "-m", "pytest", "-q"], ["node", "--test"], ["flutter", "analyze"], ["npm", "test"],
              ["cargo", "test"], [r"C:\Python\python.exe", "-m", "unittest"]]
        bad = [["python", "-c", "x"], ["python", "evil.py"], ["node", "-e", "x"], ["npm", "install", "x"],
               ["bash", "-c", "x"], ["rm", "-rf", "/"], ["flutter", "pub", "publish"], []]
        for argv in ok:
            self.assertTrue(server.allowed_check(argv), argv)
        for argv in bad:
            self.assertFalse(server.allowed_check(argv), argv)

    def test_verify_runs_real_checks_and_reports_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "test_x.py"), "w") as f:
                f.write("def test_ok():\n    assert 1 + 1 == 2\n")
            result = server.tool_verify({"project_dir": tmp, "command": "python -m pytest -q -p no:cacheprovider"})
            self.assertFalse(result["isError"], result)
            self.assertIn("ALL CHECKS PASSED", result["content"][0]["text"])
            with open(os.path.join(tmp, "test_x.py"), "w") as f:
                f.write("def test_ko():\n    assert 1 == 2\n")
            result = server.tool_verify({"project_dir": tmp, "command": "python -m pytest -q -p no:cacheprovider"})
            self.assertTrue(result["isError"])
            self.assertIn("exit code 1", result["content"][0]["text"])
            refused = server.tool_verify({"project_dir": tmp, "command": "python -c \"print(1)\""})
            self.assertIn("REFUSED", refused["content"][0]["text"])


class KnowledgeTests(unittest.TestCase):
    def test_note_recall_propose(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": tmp}):
            server.tool_note({"project": "APP", "advice": "Login code lives in lib/auth/login.dart"})
            hit = server.tool_recall({"query": "login code", "project": "APP"})["content"][0]["text"]
            self.assertIn("lib/auth/login.dart", hit)
            self.assertIn("Nothing learned", server.tool_recall({"query": "zzzz"})["content"][0]["text"])
            server.tool_propose({"title": "t", "reason": "r"})
            with open(os.path.join(tmp, "proposals.jsonl"), encoding="utf-8") as f:
                self.assertEqual(json.loads(f.readline())["status"], "new")


if __name__ == "__main__":
    unittest.main()
