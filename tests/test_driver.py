"""Tests for tidos_driver with scripted fake agents (no models are called)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_driver import Driver, detect_language  # noqa: E402
from tidos_driver import driver as driver_mod  # noqa: E402
from tidos_evals.agents import AgentResult  # noqa: E402

BUGGY = "def add(a, b):\n    return a - b\n"
FIXED = "def add(a, b):\n    return a + b\n"
GOOD_CHECK = "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n"
USELESS_CHECK = "def test_nothing():\n    assert True\n"


def write(workdir, rel, text):
    path = os.path.join(workdir, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(workdir, rel):
    with open(os.path.join(workdir, rel), encoding="utf-8") as f:
        return f.read()


class FakeAgents:
    """Plays a scripted behaviour per (agent spec, step kind)."""

    def __init__(self, script):
        self.script = script
        self.calls = []

    def __call__(self, spec, workdir, prompt, timeout, budget_usd=1.0):
        step = read(workdir, driver_mod.STEP_FILE)
        kind = "define" if "write executable checks" in step else "implement"
        self.calls.append((spec, kind, "FAILED" in step))
        actions = self.script.get((spec, kind), [])
        action = actions.pop(0) if actions else None
        if action:
            action(workdir)
        return AgentResult(cost_usd=0.01)


class DriverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.work = self.tmp.name
        write(self.work, "calc.py", BUGGY)
        write(self.work, "TASK.md", "add(a, b) must return the sum.")

    def tearDown(self):
        self.tmp.cleanup()

    def drive(self, fake, **kwargs):
        with mock.patch.object(driver_mod, "run_agent", fake):
            return Driver(**kwargs).drive(self.work, timeout=60)

    def test_happy_path_teacher_defines_student_implements(self):
        fake = FakeAgents({
            ("claude:teacher", "define"): [lambda w: write(w, "driver_checks/test_driver_checks.py", GOOD_CHECK)],
            ("opencode:student", "implement"): [lambda w: write(w, "calc.py", FIXED)],
        })
        result = self.drive(fake, student="opencode:student", teacher="claude:teacher")
        self.assertTrue(result.passed, result.log())
        self.assertEqual([c[:2] for c in fake.calls], [("claude:teacher", "define"), ("opencode:student", "implement")])
        self.assertFalse(os.path.exists(os.path.join(self.work, "driver_checks")))  # cleaned up
        self.assertAlmostEqual(result.cost_usd, 0.02)

    def test_gate_rejects_checks_that_pass_on_untouched_code(self):
        fake = FakeAgents({("opencode:student", "define"): [
            lambda w: write(w, "driver_checks/test_driver_checks.py", USELESS_CHECK),
            lambda w: write(w, "driver_checks/test_driver_checks.py", USELESS_CHECK)]})
        result = self.drive(fake, student="opencode:student")
        self.assertFalse(result.passed)
        self.assertEqual(result.reason, "could not define executable checks")
        self.assertEqual(len(fake.calls), 2)

    def test_check_author_cannot_change_the_project(self):
        def sneaky(w):
            write(w, "driver_checks/test_driver_checks.py", GOOD_CHECK)
            write(w, "calc.py", FIXED)               # "implements" while it should only define
            write(w, "extra.py", "x = 1\n")
        fake = FakeAgents({("opencode:student", "define"): [sneaky],
                           ("opencode:student", "implement"): [lambda w: write(w, "calc.py", FIXED)]})
        result = self.drive(fake, student="opencode:student")
        self.assertTrue(result.passed)
        self.assertFalse(os.path.exists(os.path.join(self.work, "extra.py")))
        self.assertIn("define", [c[1] for c in fake.calls])

    def test_tampering_restored_repair_then_escalation(self):
        fake = FakeAgents({
            ("claude:teacher", "define"): [lambda w: write(w, "driver_checks/test_driver_checks.py", GOOD_CHECK)],
            # student cheats by rewriting the check, then fails twice more
            ("opencode:student", "implement"): [
                lambda w: write(w, "driver_checks/test_driver_checks.py", USELESS_CHECK), None, None],
            ("claude:teacher", "implement"): [lambda w: write(w, "calc.py", FIXED)],
        })
        result = self.drive(fake, student="opencode:student", teacher="claude:teacher", max_repairs=2)
        self.assertTrue(result.passed, result.log())
        kinds = [(c[0], c[1], c[2]) for c in fake.calls]
        self.assertEqual(kinds, [("claude:teacher", "define", False), ("opencode:student", "implement", False),
                                 ("opencode:student", "implement", True), ("opencode:student", "implement", True),
                                 ("claude:teacher", "implement", True)])
        self.assertIn("checks were modified by the model -> restored", result.log())

    def test_no_teacher_fails_cleanly(self):
        fake = FakeAgents({("opencode:student", "define"): [
            lambda w: write(w, "driver_checks/test_driver_checks.py", GOOD_CHECK)]})
        result = self.drive(fake, student="opencode:student", max_repairs=1)
        self.assertFalse(result.passed)
        self.assertEqual(result.reason, "checks still failing")
        self.assertEqual(read(self.work, "calc.py"), BUGGY)

    def test_detect_language(self):
        self.assertEqual(detect_language(self.work), "python")
        write(self.work, "a.js", "")
        write(self.work, "b.js", "")
        self.assertEqual(detect_language(self.work), "javascript")


if __name__ == "__main__":
    unittest.main()
