"""GPTID readiness/composer-detection regression tests (stdlib unittest).

Covers the remediation contract with fake pages (no browser, no network):
  A. semantic composer detection (textarea / contenteditable / role=textbox)
  B. textarea/contenteditable/role=textbox fallback behavior
  C. disabled/non-editable composer is NOT READY
  D. registry fallback works when semantic signals are absent
  E. total timeout budget is bounded (no per-selector multiplication)
  F. _classify and quick_ready use the same detector
  G. dead/closed page => non-ready (DEAD, never LOADING/READY)
  H. zero tabs => non-ready (DEAD)
  I. monitor READY -> dead page => downgrade to ERROR
  J. adapter LOADING cannot coexist with relay CHATGPT_READY
  K. transient composer absence => bounded LOADING, never terminal error
  L. /dom_probe diagnostics correspond to the semantic detector
"""
import inspect
import time
import types
import unittest
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import chatgpt_adapter as AD  # noqa: E402
from chatgpt_adapter import (  # noqa: E402
    AutoDriver, find_usable_composer, load_selectors,
)
import relay_server as RELAY  # noqa: E402


ABSENT = {"absent": True}


class FakeLocator:
    """Minimal Playwright-locator double (structural API only)."""

    def __init__(self, spec):
        self._spec = dict(spec or ABSENT)

    @property
    def first(self):
        return self

    def wait_for(self, state="visible", timeout=1000):
        if self._spec.get("absent") or not self._spec.get("visible", False):
            if self._spec.get("simulate_wait"):
                time.sleep(max(0, timeout) / 1000.0)
            else:
                time.sleep(0.01)
            raise TimeoutError("timeout waiting visible")
        return True

    def is_visible(self):
        return bool(self._spec.get("visible", False))

    def is_disabled(self):
        return bool(self._spec.get("disabled", False))

    def is_editable(self):
        if self._spec.get("no_editable_api"):
            raise AttributeError("no is_editable")
        return bool(self._spec.get("editable", True))

    def get_attribute(self, name):
        return (self._spec.get("attrs") or {}).get(name)

    def inner_text(self, timeout=8000):
        return self._spec.get("text", "")

    def count(self):
        if self._spec.get("absent"):
            return 0
        return int(self._spec.get("count", 1))

    def is_visible_count(self):
        return self.is_visible()


class FakePage:
    """Minimal Playwright-page double."""

    def __init__(self, url="https://chatgpt.com/", title="", body="",
                 mapping=None, closed=False, dead=False):
        self._url = url
        self._title = title
        self._body = body
        self._mapping = dict(mapping or {})
        self._closed = closed
        self._dead = dead

    @property
    def url(self):
        if self._dead:
            raise RuntimeError("Target page, context or browser has been closed")
        return self._url

    def is_closed(self):
        return self._closed or self._dead

    def title(self):
        return self._title

    def locator(self, sel):
        if self._dead:
            raise RuntimeError("Target page, context or browser has been closed")
        if sel == "body":
            return FakeLocator({"visible": True, "text": self._body})
        return FakeLocator(self._mapping.get(sel, ABSENT))

    def evaluate(self, script):
        if "readyState" in script:
            return "complete"
        return ["DIV", "MAIN", "FORM"]

    @property
    def frames(self):
        return [object()]


class FakeCtx:
    def __init__(self, pages):
        self.pages = pages


LIVE_BODY = "What can I help with today? Message ChatGPT below."
USABLE_TEXTAREA = {"visible": True, "editable": True, "count": 1}


def live_driver(mapping, budget_ms=700):
    """AutoDriver double wired to a live fake page (patched fast budget)."""
    d = AutoDriver.__new__(AutoDriver)
    d._exec = AD._BrowserExec()
    d.selectors = load_selectors()
    d.browser_up = True
    page = FakePage(body=LIVE_BODY, mapping=mapping)
    d._page = page
    d._ctx = FakeCtx([page])
    d.chatgpt = "UNKNOWN"
    d.page_state = "UNKNOWN"
    d.last_error = ""
    return d


class TestSemanticDetection(unittest.TestCase):
    def test_A_semantic_textarea_first(self):
        mapping = {"textarea": dict(USABLE_TEXTAREA)}
        ok, sel, _ = find_usable_composer(FakePage(body=LIVE_BODY, mapping=mapping),
                                          load_selectors(), 700)
        self.assertTrue(ok)
        self.assertEqual(sel, "textarea")

    def test_B_contenteditable_and_textbox_variants(self):
        for sel in ('[contenteditable="true"]', '[role="textbox"]'):
            mapping = {sel: {"visible": True, "editable": True,
                             "attrs": {"contenteditable": "true"}}}
            ok, matched, _ = find_usable_composer(
                FakePage(body=LIVE_BODY, mapping=mapping), load_selectors(), 700)
            self.assertTrue(ok, sel)
            self.assertEqual(matched, sel)

    def test_C_disabled_composer_not_ready(self):
        reg = load_selectors()
        reg_sel = reg["composer"]["fallback_chain"][0]
        cases = {
            "aria-disabled": {"visible": True, "editable": True,
                              "attrs": {"aria-disabled": "true"}},
            "disabled-attr": {"visible": True, "editable": True,
                              "attrs": {"disabled": ""}},
            "not-editable": {"visible": True, "editable": False},
            "not-visible": {"visible": False, "editable": True},
        }
        for name, spec in cases.items():
            mapping = {reg_sel: spec}
            ok, _sel, _ = find_usable_composer(
                FakePage(body=LIVE_BODY, mapping=mapping), reg, 700)
            self.assertFalse(ok, name)

    def test_D_registry_fallback_when_semantic_absent(self):
        reg = load_selectors()
        reg_sel = reg["composer"]["fallback_chain"][0]
        mapping = {reg_sel: {"visible": True, "editable": True}}
        ok, matched, _ = find_usable_composer(
            FakePage(body=LIVE_BODY, mapping=mapping), reg, 2000)
        self.assertTrue(ok)
        self.assertEqual(matched, reg_sel)


class TestBudget(unittest.TestCase):
    def test_E_total_budget_bounded_no_multiplication(self):
        reg = load_selectors()
        n = len(AD.SEMANTIC_COMPOSER_SELECTORS) + len(reg["composer"]["fallback_chain"])
        mapping = {s: {"absent": True, "simulate_wait": True}
                   for s in list(AD.SEMANTIC_COMPOSER_SELECTORS)
                   + reg["composer"]["fallback_chain"]}
        budget_ms = 1500
        start = time.monotonic()
        ok, _sel, _ = find_usable_composer(
            FakePage(body=LIVE_BODY, mapping=mapping), reg, budget_ms)
        elapsed_ms = (time.monotonic() - start) * 1000.0
        self.assertFalse(ok)
        # Naive per-selector multiplication would cost n * slice ~= 8s.
        self.assertLess(elapsed_ms, budget_ms + 1500,
                        "budget exceeded: %.0fms for %d candidates" % (elapsed_ms, n))
        self.assertLess(elapsed_ms, n * AD._PROBE_SLICE_MS,
                        "timeout multiplied per selector")

    def test_F_classify_and_quick_ready_share_detector(self):
        for fn in (AutoDriver._classify, AutoDriver.quick_ready):
            src = inspect.getsource(inspect.unwrap(fn))
            self.assertIn("_composer_usable", src, fn)
        for fn in (AutoDriver._classify, AutoDriver.quick_ready):
            src = inspect.getsource(inspect.unwrap(fn))
            self.assertNotIn('_find_first(self.selectors["composer"]', src, fn)
        self.assertGreater(AD.READINESS_BUDGET_MS, 0)
        self.assertGreater(AD.MONITOR_BUDGET_MS, 0)
        self.assertLessEqual(AD._PROBE_SLICE_MS, AD.MONITOR_BUDGET_MS)


class TestLiveness(unittest.TestCase):
    def setUp(self):
        self._old = AD.MONITOR_BUDGET_MS
        AD.MONITOR_BUDGET_MS = 700

    def tearDown(self):
        AD.MONITOR_BUDGET_MS = self._old

    def test_G_dead_page_is_dead_never_loading(self):
        d = AutoDriver.__new__(AutoDriver)
        d._exec = AD._BrowserExec()
        d.selectors = load_selectors()
        d.browser_up = True
        d._page = FakePage(dead=True)
        d._ctx = FakeCtx([])
        d.chatgpt = "LOADING"
        d.page_state = "CHATGPT_LOADING"
        d.last_error = ""
        ok, status, msg = d.quick_ready()
        self.assertFalse(ok)
        self.assertEqual(status, "UNAVAILABLE")
        self.assertIn("DEAD", msg)
        self.assertEqual(d.chatgpt, "UNAVAILABLE")
        self.assertEqual(d.page_state, "UNAVAILABLE")

    def test_H_zero_tabs_is_dead(self):
        d = AutoDriver.__new__(AutoDriver)
        d._exec = AD._BrowserExec()
        d.selectors = load_selectors()
        d.browser_up = True
        page = FakePage(body=LIVE_BODY, mapping={}, closed=True)
        d._page = page
        d._ctx = FakeCtx([])
        d.chatgpt = "READY"
        d.page_state = "CHATGPT_READY"
        d.last_error = ""
        self.assertEqual(d._live_tab_count(), 0)
        ok, _status, msg = d.quick_ready()
        self.assertFalse(ok)
        self.assertIn("DEAD", msg)
        self.assertEqual(d.chatgpt, "UNAVAILABLE")

    def test_K_transient_absence_is_bounded_loading(self):
        d = live_driver({})
        ok, status, msg = d.quick_ready()
        self.assertFalse(ok)
        self.assertEqual(status, "UNAVAILABLE")
        self.assertIn("still loading", msg)
        self.assertEqual(d.page_state, "CHATGPT_LOADING")
        self.assertEqual(d.chatgpt, "LOADING")
        self.assertNotIn(d.page_state, ("ERROR", "UNAVAILABLE"))

    def test_K_ready_when_composer_usable(self):
        d = live_driver({"textarea": dict(USABLE_TEXTAREA)})
        ok, status, msg = d.quick_ready()
        self.assertTrue(ok)
        self.assertEqual(status, "OK")
        self.assertEqual(d.chatgpt, "READY")
        self.assertEqual(d.page_state, "CHATGPT_READY")


class TestStateTruth(unittest.TestCase):
    def _fake_adapter(self, state, page_state, chatgpt, last_error=""):
        auto = types.SimpleNamespace(page_state=page_state, chatgpt=chatgpt,
                                     last_error=last_error, browser_up=True)
        return types.SimpleNamespace(driver="auto", state=state, auto=auto)

    def test_I_dead_downgrades_ready_to_error(self):
        old = RELAY.STATE["relay"]
        try:
            RELAY.STATE["relay"] = "CHATGPT_READY"
            fake = self._fake_adapter("CHATGPT_READY", "UNAVAILABLE", "UNAVAILABLE",
                                      "DEAD: page does not answer")
            self.assertTrue(RELAY._adapter_dead(fake.auto))
            res = RELAY.sync_relay_state("test-dead", adapter=fake)
            self.assertEqual(res, "DOWNGRADED-ERROR")
            self.assertEqual(fake.state, "ERROR")
            self.assertEqual(RELAY.STATE["relay"], "ERROR")
        finally:
            RELAY.STATE["relay"] = old

    def test_J_loading_cannot_coexist_with_relay_ready(self):
        old = RELAY.STATE["relay"]
        try:
            RELAY.STATE["relay"] = "CHATGPT_READY"
            fake = self._fake_adapter("CHATGPT_READY", "CHATGPT_LOADING", "LOADING")
            self.assertFalse(RELAY._adapter_dead(fake.auto))
            res = RELAY.sync_relay_state("test-loading", adapter=fake)
            self.assertEqual(res, "DOWNGRADED-LOADING")
            self.assertEqual(fake.state, "BROWSER_READY")
            self.assertEqual(RELAY.STATE["relay"], "BROWSER_READY")
        finally:
            RELAY.STATE["relay"] = old

    def test_J_ready_stays_consistent(self):
        old = RELAY.STATE["relay"]
        try:
            RELAY.STATE["relay"] = "CHATGPT_READY"
            fake = self._fake_adapter("CHATGPT_READY", "CHATGPT_READY", "READY")
            res = RELAY.sync_relay_state("test-ready", adapter=fake)
            self.assertEqual(res, "CONSISTENT")
            self.assertEqual(RELAY.STATE["relay"], "CHATGPT_READY")
        finally:
            RELAY.STATE["relay"] = old


class TestDomProbeCorrespondence(unittest.TestCase):
    def test_L_probe_signals_match_detector(self):
        d = AutoDriver.__new__(AutoDriver)
        d._exec = AD._BrowserExec()
        d.selectors = load_selectors()
        d.profile_dir = "fake-profile"
        d.headless = True
        d.browser_name = "chromium"
        d.browser_up = True
        page = FakePage(body=LIVE_BODY, mapping={"textarea": dict(USABLE_TEXTAREA)})
        d._page = page
        d._ctx = FakeCtx([page])
        d.chatgpt = "READY"
        d.page_state = "CHATGPT_READY"
        d.last_error = ""
        d.nav = {"outcome": "committed", "url": "https://chatgpt.com/", "elapsed_s": 1.0}
        out = d.dom_probe([])
        self.assertTrue(out["ok"])
        textarea_rows = [p for p in out["probes"] if p["selector"] == "textarea"]
        self.assertTrue(textarea_rows and textarea_rows[0]["visible"])
        ok, sel, _ = find_usable_composer(page, d.selectors, 700)
        self.assertTrue(ok)
        self.assertEqual(sel, "textarea")


if __name__ == "__main__":
    unittest.main(verbosity=2)
