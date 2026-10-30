"""Tests for diagnose: TIDOS reads its evidence and files improvement proposals for itself (never applied)."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import db  # noqa: E402
from tidos_learn import diagnose, evolve  # noqa: E402

WEAK, STRONG = "opencode/big-pickle", "claude-opus-5-5"


def now(minutes=0):
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat(timespec="seconds")


class DiagnoseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": os.path.join(self.tmp.name, "home")})
        self.env.start()
        self.conn = db.connect(":memory:")
        self.n = 0

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()

    def task(self, model, project="APP", source="opencode", ttype="bugfix", corrected=0, errors=0, checks=()):
        self.n += 1
        sid = "s%d" % self.n
        self.conn.execute("INSERT INTO sessions (id, source, model, cwd, project) VALUES (?,?,?,?,?)",
                          (sid, source, model, self.tmp.name, project))
        cur = self.conn.execute("INSERT INTO tasks (session_id, seq, model, started_at, task_type, corrected, tool_errors) "
                                "VALUES (?,?,?,?,?,?,?)", (sid, 0, model, now(self.n), ttype, corrected, errors))
        for cmd, ok in checks:
            self.conn.execute("INSERT INTO verifications (task_id, ts, command, passed) VALUES (?,?,?,?)",
                              (cur.lastrowid, now(self.n), cmd, ok))
        self.conn.commit()

    def keys(self, history=()):
        return {f["key"]: f for f in diagnose.findings(self.conn, list(history))}

    def test_check_names(self):
        self.assertEqual(diagnose.check_name("cd /d/x; flutter analyze lib 2>&1 | head"), "flutter analyze")
        self.assertEqual(diagnose.check_name("python -m pytest -q tests/"), "pytest")
        self.assertEqual(diagnose.check_name("npm run test -- --watch=false"), "npm test")
        self.assertIsNone(diagnose.check_name("git status"))

    def test_quiet_brain_has_no_finding(self):
        for _ in range(3):
            self.task(STRONG, source="claude-code", checks=[("pytest", 1)])
        self.assertEqual(self.keys(), {})

    def test_each_rule_finds_its_evidence(self):
        for i in range(20):                                    # weak-model work, never guided
            self.task(WEAK, errors=6 if i < 3 else 0)
        for i in range(5):                                     # corrected 2 of 5 refactors
            self.task(STRONG, source="claude-code", ttype="refactor", corrected=1 if i < 2 else 0)
        for ok in (0, 0, 0, 1):                                # pytest fails in 3 tasks out of 4 runs
            self.task(STRONG, source="claude-code", project="WEB", ttype="feature", checks=[("python -m pytest", ok)])
        history = [{"job": "trial", "state": "failed", "started": now(10), "log": "a.log"},
                   {"job": "trial", "state": "failed", "started": now(5), "log": "b.log"},
                   {"job": "backup", "state": "failed", "started": now(5)}]
        found = self.keys(history)
        self.assertEqual(found["weak_unguided"]["priority"], "high")
        self.assertIn("20 tasks", found["weak_unguided"]["reason"])
        self.assertIn("stuck:" + WEAK, found)
        self.assertIn("corrections:APP:refactor", found)
        self.assertEqual(found["failing_check:WEB:pytest"]["baseline"], {"pass_rate": 25})
        self.assertIn("job_failing:trial", found)
        self.assertNotIn("job_failing:backup", found)           # one failure is not a pattern
        for f in found.values():
            self.assertTrue(f["measure"] and f["reason"])       # every proposal says how success is measured

    def test_guidance_that_does_not_help(self):
        side = lambda rate: {"tasks": 8, "verified": 6, "passed": 0, "corrected": 0, "errors": 0, "pass_rate": rate}
        rows = [{"model": WEAK, "guided": side(40), "unguided": side(60)},
                {"model": "x/y-free", "guided": side(80), "unguided": side(50)}]
        self.assertEqual([f["key"] for f in diagnose.guide_no_help(rows)], ["guide_no_help:" + WEAK])

    def test_filing_deduplicates_and_respects_your_answers(self):
        f = diagnose._finding("job_failing:x", "Job x keeps failing", "2 failed runs", "next 3 runs succeed", {"failed": 2})
        status, item = diagnose.file([f])[0]
        self.assertEqual((status, item["source"], item["measure"], item["status"]), ("new", "diagnose",
                                                                                     "next 3 runs succeed", "new"))
        self.assertEqual(diagnose.file([dict(f, reason="3 failed runs")])[0][0], "refreshed")
        self.assertEqual(len(evolve.load()), 1)                 # one proposal per finding
        self.assertEqual(evolve.load()[0]["reason"], "3 failed runs")
        evolve.set_status(item["id"], "rejected")
        self.assertEqual(diagnose.file([f])[0][0], "skipped (you rejected it)")
        evolve.set_status(item["id"], "implemented")
        self.assertEqual(diagnose.file([f])[0][0], "still seen after implementation")
        self.assertEqual(len(evolve.load()), 1)
        self.assertEqual(diagnose.run(self.conn, dry_run=True, history=[]), [])  # dry run files nothing

    def test_autopilot_runs_diagnose_once_a_day(self):
        from tidos_dashboard import autopilot
        recs = {r["key"]: r for r in autopilot.decide(self.conn)}
        self.assertIsNone(recs["diagnose"]["model"])             # no model: free and local
        with mock.patch.object(autopilot, "_last", lambda job, *a, **k: datetime.now(timezone.utc)
                               if job == "diagnose" else None):
            self.assertNotIn("diagnose", {r["key"] for r in autopilot.decide(self.conn)})


if __name__ == "__main__":
    unittest.main()
