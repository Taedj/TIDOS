"""GPTID auto-REVIEW layer tests (stdlib unittest — no browser, no network).

Covers: decision policy, skip conditions, one-review-per-task bound,
unavailable-GPTID handling, untrusted classification, provenance,
no-blind-implementation, no-retry-loop.
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from gptid_review import (  # noqa: E402
    LARGE_CHANGE_LINES, LOW_VALUE_KINDS, SIGNIFICANT_KINDS, UNTRUSTED_SOURCE,
    ReviewLedger, build_review_prompt, build_review_task, decide_review,
    readiness_ok, untrusted_envelope, verification_checklist,
)
import gptid_cli as CLI  # noqa: E402


def change(**kw):
    base = {"change_id": "chg-test", "kind": "", "summary": "test change",
            "scope": [], "lines_changed": 0}
    base.update(kw)
    return base


class TestDecisionPolicy(unittest.TestCase):
    def test_significant_kinds_invoke(self):
        for kind in sorted(SIGNIFICANT_KINDS):
            invoke, _reason, log = decide_review(change(kind=kind))
            self.assertTrue(invoke, kind)
            self.assertIn("GPTID REVIEW: REQUESTED", log)

    def test_low_value_kinds_skip(self):
        for kind in sorted(LOW_VALUE_KINDS):
            invoke, _reason, log = decide_review(change(kind=kind,
                                                        lines_changed=5000))
            self.assertFalse(invoke, kind)
            self.assertIn("SKIPPED", log)

    def test_signals_invoke(self):
        self.assertTrue(decide_review(change(unresolved_debug=True))[0])
        self.assertTrue(decide_review(change(alternatives=True))[0])
        self.assertTrue(decide_review(change(uncertainty=True))[0])
        self.assertTrue(decide_review(
            change(lines_changed=LARGE_CHANGE_LINES))[0])

    def test_no_signal_skips(self):
        invoke, _reason, log = decide_review(change())
        self.assertFalse(invoke)
        self.assertIn("SKIPPED", log)
        invoke, _reason, _log = decide_review(change(kind="mystery-kind"))
        self.assertFalse(invoke)


class TestReadinessGate(unittest.TestCase):
    def good(self):
        return {"browser": "READY", "chatgpt": "READY",
                "page_state": "CHATGPT_READY", "tabs": 1, "state": "CHATGPT_READY"}

    def test_ready_passes(self):
        ok, _ = readiness_ok(self.good())
        self.assertTrue(ok)

    def test_not_ready_states_fail(self):
        for bad in ("LOADING", "AUTHENTICATION_REQUIRED", "UNAVAILABLE", "UNKNOWN"):
            h = self.good()
            h["chatgpt"] = bad
            ok, _ = readiness_ok(h)
            self.assertFalse(ok, bad)
        h = self.good()
        h["tabs"] = 0
        self.assertFalse(readiness_ok(h)[0])
        h = self.good()
        h["state"] = "ERROR"
        self.assertFalse(readiness_ok(h)[0])
        self.assertFalse(readiness_ok({})[0])
        self.assertFalse(readiness_ok(None)[0])


class TestLedgerBound(unittest.TestCase):
    def test_record_then_block_second_review(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "reviews.json")
            led = ReviewLedger(path=path)
            self.assertFalse(led.already_reviewed("c1"))
            led.record("c1", {"status": "OK", "task_id": "gtask-1"})
            led2 = ReviewLedger(path=path)
            self.assertTrue(led2.already_reviewed("c1"))
            self.assertEqual(led2.get("c1")["task_id"], "gtask-1")
            self.assertIn("recorded_at", led2.get("c1"))

    def test_empty_id_never_blocks(self):
        with tempfile.TemporaryDirectory() as td:
            led = ReviewLedger(path=os.path.join(td, "r.json"))
            self.assertFalse(led.already_reviewed(""))


class TestPromptAndEnvelope(unittest.TestCase):
    def test_prompt_bounded_and_constrained(self):
        p = build_review_prompt(change(summary="refactor auth flow",
                                       scope=["auth/login"]),
                                questions=["Edge cases?"])
        self.assertIn("refactor auth flow", p)
        self.assertIn("do NOT modify", p)
        self.assertIn("Edge cases?", p)

    def test_task_envelope_valid_review(self):
        from gptid_protocol import validate_task
        t = build_review_task(change(summary="x"), questions=["q?"])
        self.assertEqual(t["mode"], "REVIEW")
        self.assertEqual(validate_task(t), [])

    def test_untrusted_provenance(self):
        t = build_review_task(change(summary="x"))
        env = untrusted_envelope(t, chatgpt_response="findings…", status="OK")
        self.assertEqual(env["source"], UNTRUSTED_SOURCE)
        self.assertEqual(env["task_id"], t["task_id"])
        self.assertEqual(env["session_id"], t["session_id"])
        self.assertIn("timestamp", env)
        fail = untrusted_envelope(t, status="UNAVAILABLE",
                                  failure_reason="relay down")
        self.assertEqual(fail["source"], UNTRUSTED_SOURCE)
        self.assertEqual(fail["failure_reason"], "relay down")

    def test_checklist_forbids_blind_implementation(self):
        text = "\n".join(verification_checklist())
        self.assertIn("UNTRUSTED", text)
        self.assertIn("Never implement", text)


class TestNoBlindImplementation(unittest.TestCase):
    def test_api_surface_has_no_apply_path(self):
        import gptid_review as R
        names = set(n for n in dir(R) if not n.startswith("_"))
        for banned in ("apply", "patch", "commit", "write_code", "execute",
                       "implement", "fix_code"):
            self.assertNotIn(banned, names, banned)
        self.assertNotIn("subprocess", R.__dict__.get("__dict__", {}))

    def test_api_calls_create_no_workspace_files(self):
        import gptid_review as R
        with tempfile.TemporaryDirectory() as td:
            work = os.path.join(td, "workspace")
            os.makedirs(work)
            old = os.getcwd()
            os.chdir(work)
            try:
                decide_review(change(kind="architecture"))
                readiness_ok({"browser": "x"})
                build_review_prompt(change(summary="s"))
                build_review_task(change(summary="s"))
                untrusted_envelope({"task_id": "t", "session_id": "s"})
                verification_checklist()
                ReviewLedger(path=os.path.join(td, "ledger.json"))
            finally:
                os.chdir(old)
            self.assertEqual(os.listdir(work), [])


class TestCliSingleAttempt(unittest.TestCase):
    def run_cli(self, change_d, health, send_payload, ledger_path):
        calls = {"get": 0, "post": 0}
        old_get, old_post = CLI._get, CLI._post
        CLI._get = lambda port, path, timeout=5: (calls.__setitem__("get", calls["get"] + 1) or (True, health))
        CLI._post = lambda port, path, payload, timeout=10: (calls.__setitem__("post", calls["post"] + 1) or (True, send_payload))
        try:
            rc = CLI.cmd_review_auto(8765, json.dumps(change_d), "Edge?",
                                     "ctx", dry_run=False,
                                     ledger_path=ledger_path,
                                     response_timeout=5)
        finally:
            CLI._get, CLI._post = old_get, old_post
        return rc, calls

    def good_health(self):
        return {"browser": "READY", "chatgpt": "READY",
                "page_state": "CHATGPT_READY", "tabs": 1, "state": "CHATGPT_READY"}

    def test_skip_kind_touches_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            rc, calls = self.run_cli(change(kind="format", change_id="s1"),
                                     self.good_health(), {}, os.path.join(td, "l.json"))
            self.assertEqual(rc, 0)
            self.assertEqual(calls, {"get": 0, "post": 0})

    def test_unavailable_never_blocks_and_never_sends(self):
        with tempfile.TemporaryDirectory() as td:
            old_get = CLI._get
            CLI._get = lambda port, path, timeout=5: (False, "refused")
            try:
                rc = CLI.cmd_review_auto(8765, json.dumps(change(kind="architecture",
                                                                 change_id="u1")),
                                         "", "", ledger_path=os.path.join(td, "l.json"))
            finally:
                CLI._get = old_get
            self.assertEqual(rc, 0)

    def test_unready_health_skips_send(self):
        with tempfile.TemporaryDirectory() as td:
            h = self.good_health()
            h["chatgpt"] = "LOADING"
            rc, calls = self.run_cli(change(kind="architecture", change_id="u2"),
                                     h, {}, os.path.join(td, "l.json"))
            self.assertEqual(rc, 0)
            self.assertEqual(calls["post"], 0)

    def test_hard_requirement_blocks_on_unavailable(self):
        with tempfile.TemporaryDirectory() as td:
            old_get = CLI._get
            CLI._get = lambda port, path, timeout=5: (False, "refused")
            try:
                rc = CLI.cmd_review_auto(8765, json.dumps(change(kind="architecture",
                                                                 change_id="u3",
                                                                 user_required=True)),
                                         "", "", ledger_path=os.path.join(td, "l.json"))
            finally:
                CLI._get = old_get
            self.assertEqual(rc, 2)

    def test_auto_success_correlated_no_retry(self):
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "l.json")
            task_holder = {}

            old_post = CLI._post
            old_get = CLI._get
            CLI._get = lambda port, path, timeout=5: (True, self.good_health())

            def fake_post(port, path, payload, timeout=10):
                task_holder.update(payload)
                resp = {"task_id": payload["task_id"],
                        "session_id": payload["session_id"],
                        "status": "OK", "chatgpt_response": "findings…"}
                return True, {"mode": "auto", "auto_response": resp}
            CLI._post = fake_post
            try:
                rc = CLI.cmd_review_auto(8765, json.dumps(change(kind="architecture",
                                                                 change_id="ok1")),
                                         "", "", ledger_path=lp)
            finally:
                CLI._get, CLI._post = old_get, old_post
            self.assertEqual(rc, 0)
            led = ReviewLedger(path=lp)
            self.assertEqual(led.get("ok1")["status"], "OK")
            # Second run with same change_id: bound holds, nothing re-sent.
            rc2, calls2 = self.run_cli(change(kind="architecture", change_id="ok1"),
                                       self.good_health(), {}, lp)
            self.assertEqual(rc2, 0)
            self.assertEqual(calls2["post"], 0)

    def test_send_failure_recorded_once_no_retry(self):
        with tempfile.TemporaryDirectory() as td:
            old_get, old_post = CLI._get, CLI._post
            posts = []
            CLI._get = lambda port, path, timeout=5: (True, self.good_health())
            CLI._post = lambda port, path, payload, timeout=10: (posts.append(1) or (False, "boom"))
            try:
                rc = CLI.cmd_review_auto(8765, json.dumps(change(kind="architecture",
                                                                 change_id="f1")),
                                         "", "", ledger_path=os.path.join(td, "l.json"))
            finally:
                CLI._get, CLI._post = old_get, old_post
            self.assertEqual(rc, 0)
            self.assertEqual(len(posts), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
