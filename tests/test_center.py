"""Center Link: control-center review for the agent (overview, pending, trust-gated act path)."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import center, cli, trust  # noqa: E402
from tidos_mcp import server as mcp  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.tidos = os.path.join(self.home, ".tidos")
        self.patches = [
            mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tidos}),
            mock.patch("os.path.expanduser", side_effect=lambda p: p.replace("~", self.home, 1)
                       if p.startswith("~") else os.path.expanduser(p)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        import time
        for _ in range(10):                      # a just-finished job thread may still hold the index file
            try:
                self.tmp.cleanup()
                break
            except PermissionError:
                time.sleep(0.2)


class OverviewTests(Isolated):
    def test_overview_shape_and_pending(self):
        write(os.path.join(self.tidos, "control.json"), json.dumps(
            {"switches": {"autopilot": True, "tracing": False}, "texts": {"share_learning": "agree"}}))
        write(os.path.join(self.tidos, "proposals.jsonl"),
              json.dumps({"id": 1, "title": "t1", "status": "new"}) + "\n")
        write(os.path.join(self.tidos, "update.json"),
              json.dumps({"target": "v9.9.0", "bump": "minor", "staged": {"ok": True}}))
        t = center.overview()
        for key in ("generated_at", "switches", "pending", "recommendations", "jobs", "trust", "update",
                    "scout_status", "notices"):
            self.assertIn(key, t)
        self.assertEqual(t["switches"]["switches"]["autopilot"], True)
        self.assertFalse(t["switches"]["switches"]["tracing"])
        whats = {p["what"] for p in t["pending"]["owner"]}
        self.assertIn("release update", whats)
        self.assertIn("evolution proposals", whats)
        self.assertTrue(all(p["who"] == "owner" for p in t["pending"]["owner"]))
        self.assertEqual(t["update"].get("staged", {}).get("ok"), True)

    def test_pending_consent_unasked_and_no_pending_when_clean(self):
        t = center.overview()
        self.assertIn("community-learning consent", {p["what"] for p in t["pending"]["owner"]})
        write(os.path.join(self.tidos, "control.json"), json.dumps({"texts": {"share_learning": "decline"}}))
        t = center.overview()
        self.assertEqual(t["pending"]["owner"], [])

    def test_report_is_text_with_plates_and_actions_hint(self):
        text = center.report()
        self.assertIn("# TIDOS Center review", text)
        self.assertIn("Pending:", text)
        self.assertIn("Recommended now", text)
        self.assertIn("center-act propose", text)          # how to act is always in the report
        self.assertIn("(decide in /TIDOSZIT browser)", text)


class ActTests(Isolated):
    def test_propose_goes_to_the_queue_and_the_journal(self):
        r = center.act("propose", title="Cache the guide output", reason="one helper call per session")
        self.assertTrue(r["ok"])
        from tidos_learn import evolve
        items = evolve.load()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "new")
        entry = trust.journal()[-1]
        self.assertEqual((entry["kind"], entry["by"]), ("propose", "agent"))

    def test_propose_without_title_is_an_error(self):
        with self.assertRaises(ValueError):
            center.act("propose")

    def test_run_job_refused_for_owner_kinds_and_bad_names(self):
        with self.assertRaises(ValueError) as cm:
            center.act("run_job", job="apply_release")
        self.assertIn("refused", str(cm.exception))
        with self.assertRaises(ValueError) as cm2:
            center.act("run_job", job="connect_tools")
        self.assertIn("refused", str(cm2.exception))
        with self.assertRaises(ValueError):
            center.act("set_switch", {"name": "autopilot", "value": True})
        with self.assertRaises(ValueError):
            center.act("unknown_kind")

    def test_run_job_needs_auto_trust(self):
        from tidos_dashboard import jobs
        # activate_unit starts at propose: the agent may not start it by itself...
        with self.assertRaises(ValueError) as cm:
            center.act("run_job", job="activate_unit", params={"unit": "chef"})
        self.assertIn("trust level", str(cm.exception))
        # ...but it may ask for a propose-level job as an owner action in the browser (nothing ran)
        self.assertIsNone(jobs.running())

    def test_run_job_runs_only_when_the_ladder_allows(self):
        import threading
        import time
        from tidos_dashboard import jobs
        done = threading.Event()

        class FakeProc:
            pid = 4242

            def wait(self, timeout=None):      # simulates a long job: the state stays "running"
                return 0 if done.wait(5) else 1

        started = center.act("run_job", job="distill", _popen=lambda argv, **kw: FakeProc())
        self.assertTrue(started["ok"])
        rec = jobs.get(started["job_id"])
        self.assertEqual(rec["by"], "agent")   # journaled with by=agent
        entry = trust.journal()[-1]
        self.assertEqual((entry["kind"], entry["by"], entry["state"]), ("distill", "agent", "open"))

        with self.assertRaises(RuntimeError):  # one job at a time: the runner refuses while one is running
            center.act("run_job", job="distill")
        self.assertEqual(jobs.get(started["job_id"])["state"], "running")  # the refusal started nothing new
        done.set()                             # the "job" ends; the waiter thread closes the record
        for _ in range(50):
            if jobs.get(started["job_id"])["state"] != "running":
                break
            time.sleep(0.05)
        self.assertEqual(jobs.get(started["job_id"])["state"], "done")

    def test_run_job_refused_when_kinds_trust_was_lowered(self):
        write(os.path.join(self.tidos, "trust.json"), json.dumps({"backup": {"level": "propose"}}))
        with self.assertRaises(ValueError) as cm:
            center.act("run_job", job="backup")
        self.assertIn("trust level for backup is propose", str(cm.exception))
        write(os.path.join(self.tidos, "trust.json"), json.dumps({"backup": {"level": "observe"}}))
        with self.assertRaises(ValueError):
            center.act("run_job", job="backup")


class CliAndMcpTests(Isolated):
    def test_cli_center_and_center_act(self):
        import io
        out = io.StringIO()
        with mock.patch("sys.stdout", out):
            code = cli.main(["center"])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("TIDOS Center review", text)
        with mock.patch("sys.stdout", out):
            code = cli.main(["center-act", "propose", "Faster briefs", "--reason", "less tokens"])
        self.assertEqual(code, 0)
        self.assertIn("Proposal #1", out.getvalue())
        with mock.patch("sys.stdout", out):
            code = cli.main(["center-act", "run_job", "connect_tools"])
        self.assertEqual(code, 2)                # refused: owner-only, exit 2
        self.assertIn("refused", out.getvalue())

    def test_mcp_lists_and_routes_the_center_tools(self):
        names = {t["name"] for t in mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list",
                                               "params": {}})["result"]["tools"]}
        self.assertIn("tidos_center", names)
        self.assertIn("tidos_center_act", names)
        res = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                          "params": {"name": "tidos_center_act", "arguments": {"kind": "set_switch"}}})
        self.assertTrue(res["result"]["isError"])

    def test_commands_registry_has_the_center_command(self):
        from tidos_session import commands
        names = {c.name for c in commands.COMMANDS}
        self.assertIn("tidos-center", names)
        line = commands.run_line("tidos_brain center")
        self.assertIn("tidos_brain", line)
        self.assertIn("center", line)


if __name__ == "__main__":
    unittest.main()
