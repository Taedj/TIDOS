"""Tests for the tool scout: need sensing, trust scoring, status, vetting, usage XP, brief integration."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_scout import scout  # noqa: E402
from tidos_session import brief, detect  # noqa: E402

NOW = datetime(2026, 10, 24, tzinfo=timezone.utc)


def repo(stars=20000, pushed="2026-10-20T00:00:00Z", lic="MIT", archived=False):
    return {"stargazers_count": stars, "pushed_at": pushed, "license": {"spdx_id": lic}, "archived": archived}


class ScoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.project = os.path.join(self.tmp.name, "proj")
        os.makedirs(os.path.join(self.project, "scripts"))
        for name in ("requirements.txt", os.path.join("scripts", "run.sh")):
            open(os.path.join(self.project, name), "w").close()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.home})
        self.env.start()
        # nothing installed, no MCP servers: deterministic on any machine
        self.patches = [mock.patch.object(scout, "installed", lambda t, p=None, _mcp=None: t["name"] == "pytest"),
                        mock.patch.object(scout, "_mcp_servers", lambda p=None: set())]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_catalog_is_complete(self):
        names = [t["name"] for t in scout.catalog()]
        self.assertEqual(len(names), len(set(names)))
        for t in scout.catalog():
            for key in ("capability", "stacks", "repo", "detect", "install", "why"):
                self.assertIn(key, t, t["name"])
            self.assertEqual(set(t["install"]), {"windows", "unix"}, t["name"])

    def test_needs_follow_stack_and_files(self):
        facts, missing = scout.needs(self.project)
        self.assertIn("python", facts["stack"])
        self.assertIn("python linter", missing)
        self.assertIn("shell script linter", missing)            # scripts/*.sh present
        self.assertNotIn("python test runner", missing)           # pytest installed
        self.assertNotIn("javascript linter", missing)            # not a node project
        scout.set_status("ruff", "blacklisted")
        self.assertNotIn("python linter", scout.needs(self.project)[1])

    def test_status_lifecycle(self):
        scout.set_status("gitleaks", "approved")
        self.assertEqual(scout.state()["gitleaks"]["status"], "approved")
        scout.set_status("gitleaks", "none")
        self.assertNotIn("gitleaks", scout.state())
        with self.assertRaises(KeyError):
            scout.set_status("not-a-tool", "approved")
        with self.assertRaises(ValueError):
            scout.set_status("gitleaks", "installed")

    def test_trust_score(self):
        top, _ = scout.score(repo(), scorecard=8.0, now=NOW)
        capped, reasons = scout.score(repo(), now=NOW)
        self.assertGreater(top, 90)
        self.assertEqual(capped, scout.NO_SCORECARD_CAP)
        self.assertTrue(any("capped" in r for r in reasons))
        self.assertEqual(scout.score(repo(archived=True), now=NOW)[0], 0)
        stale, _ = scout.score(repo(stars=50, pushed="2023-01-01T00:00:00Z", lic=None), now=NOW)
        self.assertLess(stale, 30)
        gpl = scout.score(repo(lic="GPL-3.0"), now=NOW)[1]
        self.assertTrue(any("copyleft" in r for r in gpl))

    def test_trust_cache_and_offline(self):
        tool = next(t for t in scout.catalog() if t["name"] == "ruff")
        calls = []

        def fake(url, timeout=15):
            calls.append(url)
            if "securityscorecards" in url:
                return {"score": 7.0}
            return repo()
        with mock.patch.object(scout, "_get_json", fake):
            first = scout.trust(tool)
            scout.trust(tool)
        self.assertEqual(len(calls), 2)                          # second call served from cache
        self.assertIsNotNone(first["score"])
        with mock.patch.object(scout, "_get_json", side_effect=OSError("offline")):
            self.assertEqual(scout.trust(tool, refresh=True)["score"], first["score"])  # keeps cached value

    def test_vet_runs_in_empty_dir(self):
        tool = {"name": "py", "version": ["python", "--version"]}
        result = scout.vet(tool)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["wrote"], [])
        self.assertIn("Python", result["version"])
        self.assertFalse(scout.vet({"name": "x", "version": ["definitely-not-installed-tool"]})["ok"])

    def test_usage_xp_from_verifications(self):
        conn = db.connect(":memory:")
        with conn:
            conn.execute("INSERT INTO sessions (id, source, project) VALUES ('s', 'claude-code', 'p')")
            conn.execute("INSERT INTO tasks (id, session_id, seq) VALUES (1, 's', 1)")
            for cmd, passed in (("python -m pytest -q", 1), ("pytest tests", 0), ("ruff check .", 1)):
                conn.execute("INSERT INTO verifications (task_id, command, passed) VALUES (1, ?, ?)", (cmd, passed))
        xp = scout.usage_xp(conn)
        self.assertEqual(xp["pytest"], {"runs": 2, "passed": 1, "xp": 3})
        self.assertEqual(xp["ruff"]["runs"], 1)
        conn.close()

    def test_brief_lists_installed_extra_checks(self):
        with mock.patch.object(scout, "installed", lambda t, p=None, _mcp=None: t["name"] == "ruff"):
            facts = detect.project_facts(self.project)
            text = brief.guide_brief({"model": "m", "tier": "weak", "tool": "opencode"}, facts, record=False)
        self.assertIn("(also available) `ruff check .`", text)


if __name__ == "__main__":
    unittest.main()
