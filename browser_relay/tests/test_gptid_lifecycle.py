"""GPTID startup/lifecycle regression tests (stdlib only — no browser).

Covers: single-spawn argv (no double-Python), bounded polling beyond the old
15s boundary, timeout + owned-process cleanup, PID identity, stale cleanup,
PID-reuse protection. Time is faked; subprocess is faked; nothing launches.
"""
import os
import subprocess
import sys
import tempfile
import time as time_mod
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import gptid_cli as CLI  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self._real_sleep = time_mod.sleep
        self._real_time = time_mod.time

    def __enter__(self):
        time_mod.sleep = self.advance
        time_mod.time = lambda: self.now
        return self

    def __exit__(self, *exc):
        time_mod.sleep = self._real_sleep
        time_mod.time = self._real_time
        return False

    def advance(self, s):
        self.now += s


class FakePopen:
    instances = []

    def __init__(self, argv, **kw):
        self.argv = list(argv)
        self.kwargs = dict(kw)
        self.pid = 4242
        self._exited = None
        FakePopen.instances.append(self)

    def poll(self):
        return self._exited

    def communicate(self, timeout=None):
        return ("relay traceback tail (owned child)", None)


class LifecycleCase(unittest.TestCase):
    def setUp(self):
        self._saved = {}
        for name in ("_get", "_post", "_reap_stale_pidfile", "_stop_owned",
                     "_remove_pidfile_if", "_pid_alive", "_proc_cmdline",
                     "_terminate", "PID_FILE"):
            self._saved[name] = getattr(CLI, name, None)
        self._real_popen = subprocess.Popen
        subprocess.Popen = FakePopen
        FakePopen.instances = []
        self._td = tempfile.TemporaryDirectory()
        CLI.PID_FILE = os.path.join(self._td.name, "gptid-relay.pid")
        self.addCleanup(self.restore)

    def restore(self):
        for name, val in self._saved.items():
            setattr(CLI, name, val)
        subprocess.Popen = self._real_popen
        self._td.cleanup()

    def write_pid(self, pid):
        with open(CLI.PID_FILE, "w") as fh:
            fh.write(str(pid))


class TestSingleSpawn(unittest.TestCase):
    def test_argv_has_exactly_one_interpreter(self):
        with tempfile.TemporaryDirectory() as td:
            old_pidfile = CLI.PID_FILE
            CLI.PID_FILE = os.path.join(td, "p.pid")
            saved = (CLI._get, CLI._reap_stale_pidfile, CLI._remove_pidfile_if)
            calls = {"get": 0}
            clock = FakeClock()

            def fake_get(port, path, timeout=5):
                calls["get"] += 1
                return (True, {}) if clock.now >= 40 else (False, "down")

            CLI._get = fake_get
            CLI._reap_stale_pidfile = lambda port: True
            CLI._remove_pidfile_if = lambda pid: True
            real_popen = subprocess.Popen
            subprocess.Popen = FakePopen
            FakePopen.instances = []
            try:
                with clock:
                    rc = CLI.cmd_start(8765, "auto", headed=True,
                                       startup_timeout=60)
            finally:
                CLI._get, CLI._reap_stale_pidfile, CLI._remove_pidfile_if = saved
                subprocess.Popen = real_popen
                CLI.PID_FILE = old_pidfile
            self.assertEqual(rc, 0)
            self.assertEqual(len(FakePopen.instances), 1)
            argv = FakePopen.instances[0].argv
            self.assertEqual(argv[0], sys.executable)
            self.assertEqual(argv.count(sys.executable), 1,
                             "double-Python spawn detected: %r" % (argv,))
            self.assertEqual(argv[1], "-u")
            self.assertTrue(argv[2].endswith("relay_server.py"), argv)
            self.assertIn("--headed", argv)
            # Readiness was reached at t=40s — far beyond the old 15s cutoff.
            self.assertGreaterEqual(clock.now, 40)
            self.assertGreater(calls["get"], 8)


class TestStartupTimeout(LifecycleCase):
    def test_timeout_cleans_owned_child_only(self):
        stopped = []
        removed = []
        CLI._get = lambda port, path, timeout=5: (False, "down")
        CLI._reap_stale_pidfile = lambda port: True
        CLI._stop_owned = lambda proc: stopped.append(proc.pid)
        CLI._remove_pidfile_if = lambda pid: removed.append(pid) or True
        with FakeClock():
            rc = CLI.cmd_start(8765, "auto", startup_timeout=10)
        self.assertEqual(rc, 1)
        self.assertEqual(stopped, [4242])
        self.assertEqual(removed, [4242])

    def test_child_death_reported_no_hang(self):
        class DeadPopen(FakePopen):
            def poll(self):
                return 1
        real = subprocess.Popen
        subprocess.Popen = DeadPopen
        FakePopen.instances = []
        removed = []
        CLI._get = lambda port, path, timeout=5: (False, "down")
        CLI._reap_stale_pidfile = lambda port: True
        CLI._remove_pidfile_if = lambda pid: removed.append(pid) or True
        try:
            with FakeClock():
                rc = CLI.cmd_start(8765, "auto", startup_timeout=60)
        finally:
            subprocess.Popen = real
        self.assertEqual(rc, 1)
        self.assertEqual(removed, [4242])

    def test_live_relay_process_blocks_second_launch(self):
        CLI._get = lambda port, path, timeout=5: (False, "down")
        CLI._reap_stale_pidfile = lambda port: False
        with FakeClock():
            rc = CLI.cmd_start(8765, "auto", startup_timeout=5)
        self.assertEqual(rc, 1)
        self.assertEqual(FakePopen.instances, [])


class TestPidSafety(LifecycleCase):
    def test_identity_requires_relay_marker(self):
        CLI._proc_cmdline = lambda pid: "C:\\Python\\python.exe relay_server.py --port 1"
        self.assertTrue(CLI._is_relay_process(123))
        CLI._proc_cmdline = lambda pid: "C:\\Windows\\notepad.exe"
        self.assertFalse(CLI._is_relay_process(123))
        CLI._proc_cmdline = lambda pid: None
        self.assertFalse(CLI._is_relay_process(123))
        CLI._proc_cmdline = lambda pid: (_ for _ in ()).throw(RuntimeError("x"))
        self.assertFalse(CLI._is_relay_process(123))

    def test_stop_dead_pid_clears_stale_file_no_kill(self):
        killed = []
        self.write_pid(99991)
        CLI._pid_alive = lambda pid: False
        CLI._terminate = lambda pid: killed.append(pid)
        rc = CLI.cmd_stop(8765)
        self.assertEqual(rc, 0)
        self.assertEqual(killed, [])
        self.assertFalse(os.path.exists(CLI.PID_FILE))

    def test_stop_live_relay_kills_and_clears(self):
        killed = []
        self.write_pid(4242)
        CLI._pid_alive = lambda pid: True
        CLI._proc_cmdline = lambda pid: "python relay_server.py --port 8765"
        CLI._terminate = lambda pid: killed.append(pid)
        rc = CLI.cmd_stop(8765)
        self.assertEqual(rc, 0)
        self.assertEqual(killed, [4242])
        self.assertFalse(os.path.exists(CLI.PID_FILE))

    def test_stop_reuse_protection_live_relay(self):
        killed = []
        self.write_pid(4242)
        CLI._pid_alive = lambda pid: True
        CLI._proc_cmdline = lambda pid: "C:\\Windows\\explorer.exe"
        CLI._terminate = lambda pid: killed.append(pid)
        CLI._get = lambda port, path, timeout=5: (True, {"state": "CHATGPT_READY"})
        rc = CLI.cmd_stop(8765)
        self.assertEqual(rc, 1)
        self.assertEqual(killed, [])
        self.assertFalse(os.path.exists(CLI.PID_FILE))

    def test_stop_nonrelay_no_health(self):
        killed = []
        self.write_pid(4242)
        CLI._pid_alive = lambda pid: True
        CLI._proc_cmdline = lambda pid: "C:\\Windows\\explorer.exe"
        CLI._terminate = lambda pid: killed.append(pid)
        CLI._get = lambda port, path, timeout=5: (False, "refused")
        rc = CLI.cmd_stop(8765)
        self.assertEqual(rc, 0)
        self.assertEqual(killed, [])
        self.assertFalse(os.path.exists(CLI.PID_FILE))

    def test_stop_no_pidfile_no_relay(self):
        CLI._get = lambda port, path, timeout=5: (False, "refused")
        self.assertEqual(CLI.cmd_stop(8765), 0)

    def test_remove_pidfile_only_matching(self):
        self.write_pid(111)
        self.assertFalse(CLI._remove_pidfile_if(222))
        self.assertTrue(os.path.exists(CLI.PID_FILE))
        self.assertTrue(CLI._remove_pidfile_if(111))
        self.assertFalse(os.path.exists(CLI.PID_FILE))


class TestStdioDecoupled(LifecycleCase):
    def run_start(self, **kw):
        calls = {"n": 0}

        def fake_get(port, path, timeout=5):
            calls["n"] += 1
            # First polls see no relay (pre-spawn + starting); then healthy.
            return (True, {}) if calls["n"] >= 3 else (False, "down")

        CLI._get = fake_get
        CLI._reap_stale_pidfile = lambda port: True
        kw.setdefault("startup_timeout", 30)
        with FakeClock():
            return CLI.cmd_start(8765, "auto", **kw)

    def test_no_pipe_stdio_persistent_log(self):
        import subprocess as sp
        with tempfile.TemporaryDirectory() as td:
            CLI.RELAY_LOG = os.path.join(td, "gptid-relay.log")
            rc = self.run_start(headed=True)
            self.assertEqual(rc, 0)
            self.assertEqual(len(FakePopen.instances), 1)  # still one spawn
            out = FakePopen.instances[0].kwargs.get("stdout")
            err = FakePopen.instances[0].kwargs.get("stderr")
            self.assertIsNot(out, sp.PIPE)
            self.assertIsNot(err, sp.PIPE)
            self.assertTrue(hasattr(out, "fileno"),
                            "child stdout must be a real persistent file")
            self.assertEqual(os.path.abspath(out.name),
                             os.path.abspath(CLI.RELAY_LOG))
            self.assertTrue(os.path.exists(CLI.RELAY_LOG),
                            "log file must survive the CLI call")

    def test_log_append_never_truncates(self):
        with tempfile.TemporaryDirectory() as td:
            CLI.RELAY_LOG = os.path.join(td, "gptid-relay.log")
            with open(CLI.RELAY_LOG, "w") as fh:
                fh.write("prior-evidence-marker\n")
            self.run_start()
            with open(CLI.RELAY_LOG) as fh:
                self.assertIn("prior-evidence-marker", fh.read())

    def test_failure_tail_comes_from_log(self):
        with tempfile.TemporaryDirectory() as td:
            CLI.RELAY_LOG = os.path.join(td, "gptid-relay.log")
            with open(CLI.RELAY_LOG, "w") as fh:
                fh.write("owned-traceback-marker\n")
            self.assertIn("owned-traceback-marker", CLI._relay_log_tail())

    def test_devnull_last_resort(self):
        import subprocess as sp
        with tempfile.TemporaryDirectory() as td:
            CLI.RELAY_LOG = os.path.join(td, "bad\x00name.log")
            rc = self.run_start()
            self.assertEqual(rc, 0)
            out = FakePopen.instances[0].kwargs.get("stdout")
            self.assertIsNot(out, sp.PIPE)
            self.assertTrue(out is sp.DEVNULL or hasattr(out, "fileno"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
