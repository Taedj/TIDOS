"""Tests for the TIDOS orb: what the panel shows and when START TIDOS may start it (no window is opened)."""
import os
import socket
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import control, db  # noqa: E402
from tidos_orb import data, launch  # noqa: E402
from test_learn import add_session  # noqa: E402

CWD = r"D:\work\Dev\APP"
NOW = datetime(2026, 10, 24, 18, 0, tzinfo=timezone.utc)


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": os.path.join(self.tmp.name, "home"),
                                                "TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")})
        self.env.start()
        self.conn = db.connect(":memory:")
        add_session(self.conn, "s", CWD, "APP", "claude-opus-5-5", [
            ("fix the login crash", "success", 1, 0, [], [("pytest", 1)]),
            ("add the export button", "success", 1, 0, [], [("pytest", 1)]),
            ("rename the settings page", "failure", 0, 1, [], [("pytest", 0)]),
        ])

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()

    def test_growth_counts_xp_and_cleared_per_day(self):
        days = data.growth(self.conn, NOW, days=3)
        self.assertEqual([d["day"] for d in days], ["2026-10-22", "2026-10-23", "2026-10-24"])
        today = days[-1]
        self.assertEqual((today["tasks"], today["cleared"]), (3, 2))
        self.assertEqual(today["xp"], 25 + 25 - 20)  # two verified successes, one corrected failure
        self.assertEqual(days[0]["xp"], 0)

    def test_snapshot_has_every_panel_section(self):
        snap = data.snapshot(self.conn, NOW)
        for key in ("player", "stats", "growth", "proposals", "notifications", "solutions", "next", "quests"):
            self.assertIn(key, snap)
        self.assertEqual(len(snap["solutions"]), 2)
        self.assertEqual(len(snap["growth"]), 14)

    def test_attention_mood(self):
        calm = {"notifications": [{"level": "info", "text": "x"}], "proposal_counts": {}}
        self.assertEqual(data.attention(calm), (0, "calm"))
        act = {"notifications": [{"level": "ok", "text": "merge"}], "proposal_counts": {"new": 2}}
        self.assertEqual(data.attention(act), (3, "act"))
        bad = dict(act, notifications=act["notifications"] + [{"level": "bad", "text": "REGRESSION"}])
        self.assertEqual(data.attention(bad), (4, "bad"))


class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_never_starts_in_ci_or_when_asked_not_to(self):
        self.assertFalse(launch.should_start({"CI": "true", "DISPLAY": ":0"}))
        self.assertFalse(launch.should_start({"TIDOS_NO_ORB": "1", "DISPLAY": ":0"}))

    def test_switch_turns_it_off(self):
        env = {"DISPLAY": ":0"}
        self.assertTrue(launch.should_start(env))
        control.set_switch("orb", False)
        self.assertFalse(launch.should_start(env))

    @unittest.skipIf(os.name == "nt" or sys.platform == "darwin", "a display always exists there")
    def test_headless_linux_has_nowhere_to_float(self):
        self.assertFalse(launch.should_start({}))

    def test_spawn_refreshes_a_running_orb_instead_of_starting_another(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        port = server.getsockname()[1]
        try:
            with mock.patch.object(launch, "should_start", return_value=True), \
                    mock.patch("subprocess.Popen") as popen:
                self.assertEqual(launch.spawn(port), "running")
                popen.assert_not_called()
            client, _ = server.accept()
            with client:
                self.assertEqual(client.recv(32), b"refresh")
        finally:
            server.close()

    def test_open_ignores_the_switch_and_opens_the_panel(self):
        control.set_switch("orb", False)
        with mock.patch.object(launch, "send", return_value=False), mock.patch("subprocess.Popen") as popen:
            self.assertEqual(launch.spawn(show=True), "started")
            self.assertEqual(launch.spawn(), "off")
        self.assertEqual(popen.call_count, 1)
        self.assertIn("--show", popen.call_args[0][0])

    def test_send_reports_no_orb(self):
        probe = socket.socket()
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()  # nothing listens on this port now
        self.assertFalse(launch.send(b"show", port, timeout=0.2))


if __name__ == "__main__":
    unittest.main()
