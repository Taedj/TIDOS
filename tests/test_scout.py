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
            auto = t.get("auto")
            if not auto:
                continue
            self.assertNotIn("mcp", t["detect"], t["name"])          # MCP servers always stay manual
            if auto["method"] == "pip":
                self.assertRegex(auto["package"], r"^[a-z0-9-]+==\d+(\.\d+)+$", t["name"])
            elif auto["method"] == "npm-global":
                self.assertRegex(auto["package"], r"^(@[a-z0-9-]+/)?[a-z0-9-]+@\d+(\.\d+)+$", t["name"])
            else:
                self.assertEqual(auto["method"], "download", t["name"])
                for f in auto["files"].values():
                    self.assertTrue(f["url"].startswith("https://github.com/%s/releases/download/" % t["repo"]), f)
                    self.assertRegex(f["sha256"], r"^[0-9a-f]{64}$")
                    self.assertIn(auto["version"], f["url"])

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


def _zip(name, payload):
    import io
    import zipfile
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("pkg/" + name, payload)
        z.writestr("../evil/" + name + ".txt", b"never extracted")
    return buf.getvalue()


class InstallTests(unittest.TestCase):
    """Install on approval: every refusal rule, verified downloads, pip, uninstall. Nothing real is installed."""

    def setUp(self):
        import hashlib
        self.tmp = tempfile.TemporaryDirectory()
        self.zip = _zip("tool.exe", b"BINARY")
        self.tools = [
            {"name": "dl", "capability": "c", "stacks": [], "repo": "o/dl", "detect": {"bin": "tool"}, "why": "w",
             "install": {"windows": "manual", "unix": "manual"},
             "auto": {"method": "download", "version": "1.0", "files": {scout.platform_key(): {
                 "url": "https://example.invalid/tool.zip", "sha256": hashlib.sha256(self.zip).hexdigest(),
                 "bin": "tool.exe"}}}},
            {"name": "pipper", "capability": "c", "stacks": [], "repo": "o/pipper", "detect": {"module": "pipper"},
             "why": "w", "install": {"windows": "manual", "unix": "manual"},
             "auto": {"method": "pip", "package": "pipper==2.0"}},
            {"name": "mcp-thing", "capability": "c", "stacks": [], "repo": "o/m", "detect": {"mcp": "m"}, "why": "w",
             "install": {"windows": "claude mcp add m", "unix": "claude mcp add m"}},
        ]
        self.present = set()
        self.calls = []
        self.trust = 90
        bindir = os.path.join(self.tmp.name, "bin")
        self.patches = [
            mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": os.path.join(self.tmp.name, "home"),
                                         "TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")}),
            mock.patch.object(scout, "catalog", lambda: self.tools),
            mock.patch.object(scout, "installed", lambda t, p=None, _mcp=None: t["name"] in self.present),
            mock.patch.object(scout, "trust", lambda t, refresh=False: {"score": self.trust, "reasons": []}),
            mock.patch.object(scout, "vet", lambda t: {"ok": True, "version": "1.0"}),
            mock.patch.object(scout, "bin_dir", lambda: bindir),
            mock.patch.object(scout, "_ensure_user_path", lambda path: False),  # never touch the real registry
        ]
        for p in self.patches:
            p.start()
        self.bindir = bindir

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def runner(self, argv, **kw):
        self.calls.append(argv)
        if "--dry-run" in argv:  # pip's resolution report: what WOULD be installed
            return mock.Mock(returncode=0, stderr="", stdout='{"install": [{"metadata": {"name": "pipper", "version": "2.0"}},'
                                                             ' {"metadata": {"name": "dep", "version": "1.1"}}]}')
        if "install" in argv:
            self.present.add("pipper")
        if "uninstall" in argv:
            self.present.discard("pipper")
        return mock.Mock(returncode=0, stdout="Successfully done", stderr="")

    def refused(self, name, why, **kw):
        with self.assertRaises(scout.InstallRefused) as ctx:
            scout.install(name, runner=self.runner, downloader=lambda url: self.zip, **kw)
        self.assertIn(why, str(ctx.exception))

    def test_every_rule_must_pass(self):
        from tidos_brain import control
        self.refused("pipper", "switch is off")                   # off by default
        control.set_switch("tool_install", True)
        self.refused("mcp-thing", "run it yourself")              # no auto spec: always manual
        self.refused("pipper", "approve pipper first")
        scout.set_status("pipper", "approved")
        self.trust = 40
        self.refused("pipper", "below 70")
        self.trust = 90
        self.present.add("pipper")
        self.refused("pipper", "already installed")
        self.assertEqual(self.calls, [])                          # nothing ever ran

    def test_pip_install_and_uninstall(self):
        from tidos_brain import control
        control.set_switch("tool_install", True)
        scout.set_status("pipper", "approved")
        result = scout.install("pipper", runner=self.runner)
        self.assertTrue(result["ok"])
        self.assertIn("--dry-run", self.calls[0])                  # resolve first: what WOULD be installed
        self.assertEqual(self.calls[1][1:], ["-m", "pip", "install", "--disable-pip-version-check", "pipper==2.0"])
        self.assertIn("installs: pipper==2.0, dep==1.1", result["output"])
        self.assertEqual(scout.state()["pipper"]["installed_by_tidos"]["plan"], ["pipper==2.0", "dep==1.1"])
        self.assertTrue(scout.uninstall("pipper", runner=self.runner)["ok"])
        self.assertEqual(self.calls[2][1:], ["-m", "pip", "uninstall", "-y", "pipper"])
        self.assertNotIn("installed_by_tidos", scout.state()["pipper"])
        with self.assertRaises(scout.InstallRefused):             # tools you installed yourself are never removed
            scout.uninstall("pipper", runner=self.runner)
        with open(os.path.join(os.environ["TIDOS_HOME_DIR"], "tool_installs.log"), encoding="utf-8") as f:
            self.assertIn("pipper==2.0", f.read())

    def test_download_is_verified_and_only_the_binary_is_written(self):
        from tidos_brain import control
        control.set_switch("tool_install", True)
        scout.set_status("dl", "approved")
        with self.assertRaises(scout.InstallRefused) as ctx:     # tampered file: refused, nothing written
            scout.install("dl", runner=self.runner, downloader=lambda url: self.zip + b"x")
        self.assertIn("SHA-256", str(ctx.exception))
        self.assertFalse(os.path.exists(self.bindir))
        result = scout.install("dl", runner=self.runner, downloader=lambda url: self.zip)
        self.assertEqual(os.listdir(self.bindir), ["tool.exe"])   # the ../evil entry is never extracted
        with open(os.path.join(self.bindir, "tool.exe"), "rb") as f:
            self.assertEqual(f.read(), b"BINARY")
        self.assertIn("sha256 verified", result["output"])
        self.assertEqual(self.calls, [])                          # no shell, no package manager
        self.assertTrue(scout.uninstall("dl")["ok"])
        self.assertEqual(os.listdir(self.bindir), [])

    def test_unresolvable_pip_package_installs_nothing(self):
        from tidos_brain import control
        control.set_switch("tool_install", True)
        scout.set_status("pipper", "approved")
        fail = lambda argv, **kw: (self.calls.append(argv), mock.Mock(returncode=1, stdout="", stderr="no match"))[1]
        with self.assertRaises(scout.InstallRefused) as ctx:
            scout.install("pipper", runner=fail)
        self.assertIn("dry run failed", str(ctx.exception))
        self.assertEqual(len(self.calls), 1)                       # only the dry run ran

    def test_prevet_quarantines_bad_binaries(self):
        tool = {"version": ["tool", "--version"]}
        bad = scout.prevet_binary(tool, "tool.exe", b"not a program")
        self.assertFalse(bad["ok"])                                # does not run -> never installed
        script = "import os, sys; open('junk.txt', 'w').write('x'); print('tool 1.0')"
        with mock.patch.object(scout.subprocess, "run", lambda argv, cwd=None, **kw: (
                open(os.path.join(cwd, "junk.txt"), "w").close(), mock.Mock(returncode=0, stdout="tool 1.0", stderr=""))[1]):
            writer = scout.prevet_binary(tool, "tool.exe", b"x")
        self.assertFalse(writer["ok"])
        self.assertIn("wrote", writer["detail"])                   # a version check must not write files
        with mock.patch.object(scout.subprocess, "run", lambda argv, **kw: mock.Mock(returncode=0, stdout="tool 1.0", stderr="")):
            self.assertEqual(scout.prevet_binary(tool, "tool.exe", b"x")["version"], "tool 1.0")

    def test_verify_accepts_catalog_checks_only(self):
        from tidos_mcp import server as mcp
        with mock.patch.object(scout, "catalog", lambda: [{"name": "g", "check": "gitleaks detect --redact"},
                                                         {"name": "s", "check": "shellcheck scripts/*.sh"}]):
            self.assertTrue(mcp.allowed_check(["gitleaks", "detect"]))
            self.assertFalse(mcp.allowed_check(["gitleaks", "protect"]))
            self.assertTrue(mcp.allowed_check(["shellcheck", "a.sh"]))
            self.assertFalse(mcp.allowed_check(["python", "-c", "print(1)"]))


if __name__ == "__main__":
    unittest.main()
