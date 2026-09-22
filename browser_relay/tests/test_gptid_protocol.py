"""Deterministic GPTID unit tests (stdlib unittest — no browser, no network)."""
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from gptid_protocol import (  # noqa: E402
    MODES, build_context_package, build_response, build_task, contains_secret,
    redact_secrets, task_matches_response, truncate, validate_response, validate_task,
)
from chatgpt_adapter import (  # noqa: E402
    USER_ACTION_REQUIRED, AutoDriver, ChatGPTAdapter, detect_driver, detect_walls,
    load_selectors, parse_received_block, render_auto_prompt, render_sent_block,
    tails_stable,
)


class TestIds(unittest.TestCase):
    def test_task_ids_unique(self):
        a = build_task(objective="o", mode="REVIEW")
        b = build_task(objective="o", mode="REVIEW")
        self.assertNotEqual(a["task_id"], b["task_id"])
        self.assertNotEqual(a["session_id"], b["session_id"])

    def test_bad_mode_rejected(self):
        with self.assertRaises(ValueError):
            build_task(objective="o", mode="FINANCE")


class TestSerialization(unittest.TestCase):
    def test_task_roundtrip(self):
        t = build_task(objective="review x", mode="AUDIT", scope=["a"], constraints=["c"],
                       questions=["q?"], session_id="gsess-1", task_id="gtask-1")
        d = json.loads(json.dumps(t))
        self.assertEqual(d["task_id"], "gtask-1")
        self.assertEqual(validate_task(d), [])

    def test_task_missing_field(self):
        t = build_task(objective="o", mode="REVIEW")
        del t["objective"]
        self.assertTrue(any("objective" in e for e in validate_task(t)))

    def test_response_roundtrip_and_correlation(self):
        t = build_task(objective="o", mode="REVIEW")
        r = build_response(t["task_id"], t["session_id"],
                           chatgpt_response="RECEIVED FROM CHATGPT:\nCHATGPT: obs 1, 2, 3")
        self.assertEqual(validate_response(r), [])
        self.assertTrue(task_matches_response(t, r))

    def test_empty_ok_response_rejected(self):
        t = build_task(objective="o", mode="REVIEW")
        r = build_response(t["task_id"], t["session_id"], chatgpt_response="   ", status="OK")
        self.assertTrue(validate_response(r), "silent success must never validate")

    def test_mismatched_ids(self):
        t = build_task(objective="o", mode="REVIEW")
        r = build_response("gtask-other", t["session_id"], chatgpt_response="CHATGPT: hi")
        self.assertFalse(task_matches_response(t, r))


class TestRedaction(unittest.TestCase):
    def test_each_secret_class_redacted(self):
        samples = [
            "api_key=abc123", "password=hunter2", "ssid=deadbeef",
            "deriv_token=xyz", "cookie: yummy", "-----BEGIN PRIVATE KEY-----",
        ]
        for s in samples:
            self.assertTrue(contains_secret(s), s)
            self.assertNotIn(s.split("=")[-1][:4] if "=" in s else s[:4],
                             redact_secrets(s), s)

    def test_task_build_redacts(self):
        t = build_task(objective="check api_key=SECRET123", mode="REVIEW")
        self.assertNotIn("SECRET123", t["objective"])

    def test_logs_have_no_secrets(self):
        block = render_sent_block(build_task(objective="api_key=SECRET123", mode="REVIEW"))
        self.assertNotIn("SECRET123", block)


class TestLimits(unittest.TestCase):
    def test_truncate(self):
        self.assertTrue(truncate("x" * 100, 10).endswith("]"))
        self.assertIn("truncated", truncate("x" * 100, 10))

    def test_context_budget(self):
        parts = {"A": "x" * 5000, "B": "y" * 5000}
        ctx, included, dropped = build_context_package(parts, {"max_context_chars": 6000})
        self.assertLessEqual(len(ctx), 7000)
        self.assertTrue(dropped)


class TestStateMachine(unittest.TestCase):
    def test_manual_lifecycle(self):
        a = ChatGPTAdapter(driver="manual")
        self.assertEqual(a.state, "DISCONNECTED")
        ok, _ = a.start()
        self.assertTrue(ok)
        self.assertEqual(a.state, "BROWSER_READY")
        ok, _ = a.confirm_chatgpt_page(user_confirmed=False)
        self.assertFalse(ok, "MANUAL must not self-confirm readiness")
        ok, _ = a.confirm_chatgpt_page(user_confirmed=True)
        self.assertTrue(ok)
        self.assertEqual(a.state, "CHATGPT_READY")

    def test_driver_fallback_without_playwright(self):
        self.assertIn(detect_driver("auto"), ("auto", "manual"))
        self.assertEqual(detect_driver("manual"), "manual")

    def test_received_validation(self):
        ok, _ = parse_received_block("")
        self.assertFalse(ok)
        ok, _ = parse_received_block("some random text")
        self.assertFalse(ok)
        ok, body = parse_received_block("RECEIVED FROM CHATGPT:\nCHATGPT: three observations")
        self.assertTrue(ok)


class TestSelectors(unittest.TestCase):
    def test_registry_loads_and_has_fallbacks(self):
        reg = load_selectors()
        for key in ("composer", "send_button", "assistant_messages"):
            self.assertTrue(reg[key]["fallback_chain"], key)


class TestConversationReset(unittest.TestCase):
    def test_history_bound(self):
        hist, maxh = [], 5
        for i in range(9):
            hist.append("t%d" % i)
            hist = hist[-maxh:]
        self.assertEqual(len(hist), 5)


class TestModes(unittest.TestCase):
    def test_all_modes_build(self):
        for m in MODES:
            self.assertEqual(build_task(objective="o", mode=m)["mode"], m)


class TestAutoWalls(unittest.TestCase):
    def test_auth_wall_detected(self):
        reg = load_selectors()
        self.assertEqual(detect_walls("Welcome — Log in to continue", reg), "auth-wall")

    def test_captcha_detected(self):
        reg = load_selectors()
        self.assertEqual(detect_walls("Verify you are human to continue", reg), "captcha")

    def test_clean_page_ok(self):
        reg = load_selectors()
        self.assertEqual(detect_walls("What can I help with today? Message ChatGPT", reg), "ok")

    def test_tails_stable(self):
        self.assertTrue(tails_stable("xxabcdef", "yyabcdef", tail_chars=6))
        self.assertTrue(tails_stable("abcdef", "abcdef"))
        self.assertFalse(tails_stable("abcdef", "abcdeg", tail_chars=6))


class TestAutoPrompt(unittest.TestCase):
    def test_auto_prompt_shape(self):
        t = build_task(objective="review x", mode="REVIEW", questions=["q?"])
        body = render_auto_prompt(t)
        self.assertIn("REVIEW", body)
        self.assertIn(t["task_id"], body)
        self.assertIn("review x", body)

    def test_no_fallback_to_manual_by_default(self):
        a = ChatGPTAdapter(driver="manual")
        self.assertFalse(a.fallback_to_manual)


class TestAutoDriverUnit(unittest.TestCase):
    def test_diagnose_before_launch(self):
        d = AutoDriver(headless=True)
        snap = d.diagnose()
        self.assertEqual(snap["mode"], "AUTO")
        self.assertEqual(snap["browser"], "DOWN")
        self.assertIn("profile", snap)
        self.assertIn(snap["page_state"], ("UNKNOWN", "BROWSER_STARTING", "UNAVAILABLE"))
        self.assertIn("nav_outcome", snap)
        self.assertIn("tabs", snap)

    def test_page_states_defined(self):
        from chatgpt_adapter import PAGE_STATES
        for s in ("BROWSER_STARTING", "CHATGPT_LOADING", "AUTH_REQUIRED",
                  "CHATGPT_READY", "ERROR", "UNAVAILABLE"):
            self.assertIn(s, PAGE_STATES)

    def test_engine_default_chromium(self):
        d = AutoDriver(headless=True)
        self.assertEqual(d.browser_name, "chromium")
        self.assertEqual(d.diagnose()["browser_engine"], "chromium")

    def test_engine_firefox_selectable(self):
        d = AutoDriver(headless=True, browser_name="firefox")
        self.assertEqual(d.browser_name, "firefox")

    def test_engine_chromium_selectable(self):
        d = AutoDriver(headless=True, browser_name="chromium")
        self.assertEqual(d.browser_name, "chromium")

    def test_engine_nightly_selectable(self):
        d = AutoDriver(headless=True, browser_name="firefox-nightly")
        self.assertEqual(d.browser_name, "firefox-nightly")

    def test_engine_rejects_unknown(self):
        with self.assertRaises(ValueError):
            AutoDriver(headless=True, browser_name="safari")

    def test_profile_status_string(self):
        d = AutoDriver(headless=True)
        self.assertIsInstance(d.profile_status(), str)

    def test_manual_diagnose_block(self):
        a = ChatGPTAdapter(driver="manual")
        block = a.diagnose_block()
        self.assertIn("GPTID MODE: MANUAL", block)
        self.assertIn("RELAY:", block)

    def test_auto_adapter_no_launch(self):
        a = ChatGPTAdapter(driver="auto")
        self.assertIsNone(a.auto, "constructor must not launch a browser")
        block = a.diagnose_block()
        self.assertIn("GPTID MODE: AUTO", block)
        self.assertIn("USER_ACTION_REQUIRED", USER_ACTION_REQUIRED)


class TestBrowserExec(unittest.TestCase):
    def test_cross_thread_marshal(self):
        import threading
        from chatgpt_adapter import _BrowserExec
        ex = _BrowserExec()
        seen = []
        worker = threading.Thread(
            target=lambda: seen.append(ex.run(lambda: (threading.current_thread().name, 40 + 2))))
        worker.start()
        worker.join(timeout=30)
        self.assertFalse(worker.is_alive())
        self.assertEqual(seen[0][1], 42)
        self.assertEqual(seen[0][0], ex._th.name)

    def test_reentrant_direct_call(self):
        import threading
        from chatgpt_adapter import _BrowserExec
        ex = _BrowserExec()
        out = ex.run(lambda: ex.run(lambda: "inner"))
        self.assertEqual(out, "inner")

    def test_exception_marshalled(self):
        from chatgpt_adapter import _BrowserExec
        ex = _BrowserExec()

        def boom():
            raise ValueError("probe-fail")
        with self.assertRaises(ValueError):
            ex.run(boom)


class TestSplitStatus(unittest.TestCase):
    def test_unavailable_parsed(self):
        from relay_server import _split_status
        s, r = _split_status("STATUS=UNAVAILABLE (reason=USER_ACTION_REQUIRED: login wall)")
        self.assertEqual(s, "UNAVAILABLE")
        self.assertIn("USER_ACTION_REQUIRED", r)

    def test_timeout_parsed(self):
        from relay_server import _split_status
        s, _ = _split_status("STATUS=TIMEOUT (reason=response timeout after 180s)")
        self.assertEqual(s, "TIMEOUT")

    def test_garbage_defaults_error(self):
        from relay_server import _split_status
        s, _ = _split_status("weird string")
        self.assertEqual(s, "ERROR")


if __name__ == "__main__":
    unittest.main(verbosity=2)
