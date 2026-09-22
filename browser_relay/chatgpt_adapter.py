"""GPTID ChatGPT browser adapter.

Two drivers:
  AUTO   - Playwright-controlled Chromium on a dedicated local profile
           (~/.tidos/gptid-profile). The user signs into ChatGPT once,
           manually, in that profile (or a headed window). The relay reuses
           the profile afterwards. Full round-trip: detect -> send -> wait ->
           extract, with machine-readable failures.
  MANUAL - human bridge (default): TIDOS renders a copyable SENT block, the
           user pastes it into their own ChatGPT Free tab and pastes the
           reply back. No DOM access, no credentials, always available.

Security: the adapter NEVER reads, prints, persists, or transmits cookies,
passwords, session tokens, or browser storage. Page text is only ever used
for (a) wall/marker detection and (b) the assistant response itself, which
is redacted downstream by gptid_protocol. Auth walls and CAPTCHAs are
reported as USER_ACTION_REQUIRED — bypass is out of scope.

The adapter NEVER fabricates a ChatGPT response. Every failure returns a
machine-readable (ok=False, status, reason) triple.
"""
import json
import os
import queue
import threading
import time
from functools import wraps

SELECTOR_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "selector_registry.json")

# Machine-readable AUTO failure reasons.
USER_ACTION_REQUIRED = "USER_ACTION_REQUIRED"


class _BrowserExec:
    """Single-threaded executor for ALL Playwright calls.

    Playwright's sync API binds browser objects to the creating thread
    (greenlet affinity): touching a page from any other thread raises
    "Cannot switch to a different thread". The relay serves HTTP on worker
    threads and monitors on its own thread, so every page/context call is
    marshalled here. Re-entrant (nested calls on the owner thread run
    directly) and bounded (wait cap, never indefinite).
    """

    WAIT_CAP_S = 600

    def __init__(self):
        self._q = queue.Queue()
        self._th = threading.Thread(target=self._loop, daemon=True,
                                    name="gptid-browser-exec")
        self._th.start()

    def _loop(self):
        while True:
            fn, args, kwargs, box = self._q.get()
            try:
                box["res"] = fn(*args, **kwargs)
                box["ok"] = True
            except Exception as e:  # noqa: BLE001 — marshalled back to caller
                box["err"] = e
                box["ok"] = False
            box["ev"].set()

    def run(self, fn, *args, **kwargs):
        if threading.current_thread() is self._th:
            return fn(*args, **kwargs)
        box = {"ev": threading.Event()}
        self._q.put((fn, args, kwargs, box))
        if not box["ev"].wait(timeout=self.WAIT_CAP_S):
            raise TimeoutError("browser executor wait exceeded %ds" % self.WAIT_CAP_S)
        if box.get("ok"):
            return box["res"]
        raise box.get("err")


def _on_browser_thread(fn):
    """Run an AutoDriver method on the single browser thread."""
    @wraps(fn)
    def wrapper(self, *args, **kwargs):
        return self._exec.run(fn, self, *args, **kwargs)
    return wrapper

# Page-level states (AUTO driver). A goto timeout NEVER implies an auth wall:
# a live-but-loading page is CHATGPT_LOADING and keeps being monitored.
PAGE_STATES = ("UNKNOWN", "BROWSER_STARTING", "CHATGPT_LOADING",
               "AUTH_REQUIRED", "CHATGPT_READY", "ERROR", "UNAVAILABLE")


def load_selectors():
    with open(SELECTOR_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def playwright_available():
    try:
        import playwright  # noqa: F401
        return True
    except Exception:
        return False


def detect_driver(preferred="auto"):
    """Resolve which driver to use. Returns 'auto' or 'manual'.

    Anything other than an installed playwright collapses to 'manual' —
    offline-safe, dependency-free, never blocks TIDOS.
    """
    if preferred == "manual":
        return "manual"
    if preferred in ("auto", "browser") and playwright_available():
        return "auto"
    return "manual"


def render_sent_block(task):
    """Copyable human-bridge prompt for MANUAL mode. No secrets (caller redacts)."""
    lines = [
        "SENT TO CHATGPT — copy below into your ChatGPT Free tab:",
        "```text",
        "[TIDOS via GPTID | mode=%s | task=%s]" % (task.get("mode"), task.get("task_id")),
        "Objective: %s" % task.get("objective"),
    ]
    if task.get("questions"):
        lines.append("Questions:")
        for q in task["questions"]:
            lines.append("- %s" % q)
    if task.get("context"):
        lines.append("Context:")
        lines.append(str(task["context"])[:4000])
    if task.get("constraints"):
        lines.append("Constraints: %s" % "; ".join(task["constraints"]))
    lines.append("Reply with: 3 observations + findings + uncertainties. No code execution, no secrets.")
    lines.append("```")
    return "\n".join(lines)


def render_auto_prompt(task):
    """Prompt text injected into the ChatGPT composer by the AUTO driver."""
    lines = [
        "[TIDOS via GPTID | mode=%s | task=%s]" % (task.get("mode"), task.get("task_id")),
        "Objective: %s" % task.get("objective"),
    ]
    if task.get("questions"):
        lines.append("Questions:")
        for q in task["questions"]:
            lines.append("- %s" % q)
    if task.get("context"):
        lines.append("Context:")
        lines.append(str(task["context"])[:4000])
    if task.get("constraints"):
        lines.append("Constraints: %s" % "; ".join(task["constraints"]))
    lines.append("Reply with: 3 observations + findings + uncertainties. No code execution, no secrets.")
    return "\n".join(lines)


def parse_received_block(text):
    """Validate a pasted RECEIVED block. Returns (ok, body_or_reason)."""
    if not text or not text.strip():
        return False, "MALFORMED: empty paste"
    head = text.strip().splitlines()[0]
    if "RECEIVED FROM CHATGPT" not in head and "CHATGPT:" not in text[:200]:
        return False, "MALFORMED: missing RECEIVED FROM CHATGPT: / CHATGPT: marker"
    return True, text.strip()


def detect_walls(page_text, selectors):
    """Pure helper: classify wall markers in visible page text.

    Returns one of: 'ok', 'auth-wall', 'captcha'. Never touches credentials.
    """
    low = (page_text or "").lower()
    for marker in selectors.get("page", {}).get("captcha_markers", []):
        if marker.lower() in low:
            return "captcha"
    for marker in selectors.get("page", {}).get("logged_out_markers", []):
        if marker.lower() in low:
            return "auth-wall"
    return "ok"


def tails_stable(previous, current, tail_chars=200):
    """Pure helper: trailing-text stability check for completion detection."""
    return (previous or "")[-tail_chars:] == (current or "")[-tail_chars:]


# -- unified readiness detection (single source of truth) ------------------
# ONE authoritative composer detector used by EVERY readiness path
# (_classify, quick_ready, monitor probes, /dom_probe diagnostics).
# Semantic-first: generic editable-composer signals come before the
# registry fallback chain (which stays as fallback, never primary).
# No brittle class-name dependency. Never fabricates readiness.
SEMANTIC_COMPOSER_SELECTORS = (
    "textarea",
    "[contenteditable=\"true\"]",
    "[role=\"textbox\"]",
)

# Authoritative bounded budgets (total wall-clock per detection operation).
# The budget caps the COMPLETE operation — never per-selector.
READINESS_BUDGET_MS = 10000   # full classification (_classify at startup)
MONITOR_BUDGET_MS = 5000      # monitor / quick probes (quick_ready)
DOM_PROBE_BUDGET_MS = 5000    # /dom_probe diagnostic detector run
_PROBE_SLICE_MS = 1000        # max wait slice per candidate; total <= budget


def _locator_usable(loc):
    """True only if a candidate composer is genuinely usable.

    Checks (all structural, never content/credentials):
      visible + enabled (when the DOM exposes enabled state) +
      editable/contenteditable (when applicable) +
      not disabled / not aria-disabled.
    """
    try:
        if not loc.is_visible():
            return False
    except Exception:
        return False
    try:
        if loc.is_disabled():
            return False
    except Exception:
        pass
    try:
        aria = loc.get_attribute("aria-disabled")
    except Exception:
        aria = None
    if aria is not None and str(aria).lower() == "true":
        return False
    try:
        disabled = loc.get_attribute("disabled")
    except Exception:
        disabled = None
    if disabled is not None:
        return False
    try:
        editable = loc.is_editable()
    except Exception:
        editable = None
    if editable is not None:
        return bool(editable)
    # No editability API exposed: semantic fallback on markup signals.
    try:
        ce = loc.get_attribute("contenteditable")
    except Exception:
        ce = None
    if ce is not None:
        return str(ce).lower() == "true"
    return True


def find_usable_composer(page, selectors, budget_ms=READINESS_BUDGET_MS):
    """Authoritative composer detector (semantic-first, budget-bounded).

    Returns (usable, matched_selector_or_None, detail). Total wall-clock is
    capped by budget_ms across ALL candidates — never timeout-per-selector
    multiplication. Safe on a dead page (per-candidate guards): returns
    (False, None, ...) instead of raising.
    """
    ordered, seen = [], set()
    chain = list(SEMANTIC_COMPOSER_SELECTORS) + list(
        (selectors or {}).get("composer", {}).get("fallback_chain", []))
    for sel in chain:
        if isinstance(sel, str) and sel not in seen:
            seen.add(sel)
            ordered.append(sel)
    try:
        budget = max(0, int(budget_ms))
    except Exception:
        budget = READINESS_BUDGET_MS
    deadline = time.monotonic() + budget / 1000.0
    for sel in ordered:
        remaining_ms = (deadline - time.monotonic()) * 1000.0
        if remaining_ms <= 0:
            break
        try:
            loc = page.locator(sel).first
        except Exception:
            continue
        try:
            loc.wait_for(state="visible",
                         timeout=int(min(_PROBE_SLICE_MS, remaining_ms)))
        except Exception:
            continue
        try:
            if _locator_usable(loc):
                return True, sel, "composer usable (%s)" % sel
        except Exception:
            continue
    return False, None, "no usable composer within %dms (%d candidates)" % (
        budget, len(ordered))


class AutoDriver:
    """Playwright lifecycle + ChatGPT page automation.

    Engine: Firefox by default (Mozilla, user request), Chromium available
    as fallback via browser_name="chromium". All methods return
    (ok, status_or_payload, reason). Statuses mirror the GPTID protocol:
    OK | UNAVAILABLE | TIMEOUT | MALFORMED | ERROR.
    """

    ENGINES = ("firefox", "firefox-nightly", "chromium")
    # firefox         -> installed stable Mozilla Firefox (channel="firefox"),
    #                    dedicated GPTID profile (binary shared, profile isolated).
    # firefox-nightly -> Playwright-bundled Nightly build (fallback).
    # chromium        -> Playwright-bundled Chromium (fallback).

    def __init__(self, profile_dir=None, chatgpt_url="https://chatgpt.com/",
                 selectors=None, headless=True, response_timeout_seconds=180,
                 browser_name="chromium"):
        if browser_name not in self.ENGINES:
            raise ValueError("unknown engine %r (expected firefox|chromium)" % (browser_name,))
        self.browser_name = browser_name
        self.profile_dir = profile_dir or os.path.join(
            os.path.expanduser("~"), ".tidos", "gptid-profile")
        self.chatgpt_url = chatgpt_url
        self.selectors = selectors or load_selectors()
        self.headless = headless
        self.response_timeout_seconds = response_timeout_seconds
        self._pw = None
        self._ctx = None
        self._page = None
        self.browser_up = False
        self.chatgpt = "UNKNOWN"  # READY | AUTHENTICATION_REQUIRED | LOADING | UNKNOWN
        self.page_state = "UNKNOWN"  # one of PAGE_STATES
        self.last_error = ""
        # Safe nav diagnostics (no content, no credentials, no storage).
        self.nav = {"started": "", "ended": "", "outcome": "none",
                    "url": "", "elapsed_s": 0.0}
        # All Playwright calls run on this single thread (greenlet affinity).
        self._exec = _BrowserExec()

    # -- lifecycle ------------------------------------------------------
    @_on_browser_thread
    def launch(self):
        """Launch Chromium on the dedicated profile and reach ChatGPT.

        Robust startup (Windows-headed safe):
          1. launch browser process on the persistent profile,
          2. create a page, navigate with wait_until="commit" (a committed
             navigation means bytes are flowing; slow JS/challenge pages must
             NOT fail startup the way domcontentloaded timeouts do),
          3. on navigation timeout: inspect page aliveness BEFORE any verdict —
             a live page continues to state classification, never BROWSER_DOWN,
          4. dead page: recreate it ONCE and retry navigation ONCE (bounded),
          5. classify the live page: READY | LOADING | AUTH_REQUIRED.

        Returns ok=True whenever the browser/page is alive (even if ChatGPT
        is still loading). ok=False only when the browser/page is genuinely
        unavailable. Never touches credentials, cookies, or storage.
        """
        from playwright.sync_api import sync_playwright
        self.close(quiet=True)
        self.page_state = "BROWSER_STARTING"
        self.last_error = ""
        self.nav = {"started": _utc(), "ended": "", "outcome": "none",
                    "url": "", "elapsed_s": 0.0}
        os.makedirs(self.profile_dir, exist_ok=True)
        try:
            self._pw = sync_playwright().start()
            if self.browser_name in ("firefox", "firefox-nightly"):
                kwargs = {"headless": self.headless,
                          "viewport": {"width": 1366, "height": 900}}
                if self.browser_name == "firefox":
                    kwargs["channel"] = "firefox"  # installed stable Firefox
                self._ctx = self._pw.firefox.launch_persistent_context(
                    self.profile_dir, **kwargs)
            else:
                self._ctx = self._pw.chromium.launch_persistent_context(
                    self.profile_dir, headless=self.headless,
                    viewport={"width": 1366, "height": 900},
                    args=["--disable-blink-features=AutomationControlled",
                          "--no-first-run",
                          "--no-default-browser-check"])
        except Exception as e:
            self.page_state = "UNAVAILABLE"
            self.last_error = "browser launch failed: %s" % _short(e)
            self.close(quiet=True)
            return False, "UNAVAILABLE", self.last_error
        # Single-tab discipline: a persistent context already owns one blank
        # tab — reuse it instead of opening a second one.
        self._page = self._take_page()
        if self._page is None:
            self.page_state = "UNAVAILABLE"
            self.last_error = "no usable tab in browser context"
            self.close(quiet=True)
            return False, "UNAVAILABLE", self.last_error
        # Navigate (bounded single page-recreate retry; profile preserved).
        for attempt in (1, 2):
            alive, nav_msg = self._navigate_once()
            if alive:
                break
            if attempt == 1:
                try:
                    if self._page is not None:
                        self._page.close()
                except Exception:
                    pass
                self._page = self._take_page()
                if self._page is None:
                    self.page_state = "UNAVAILABLE"
                    self.last_error = "page recreate failed: no usable tab"
                    self.close(quiet=True)
                    return False, "UNAVAILABLE", self.last_error
        if not alive:
            self.page_state = "UNAVAILABLE"
            self.last_error = "browser page genuinely unavailable: %s" % nav_msg
            self.close(quiet=True)
            return False, "UNAVAILABLE", self.last_error
        self.browser_up = True
        state = self._classify()
        return True, "OK", "%s | %s" % (nav_msg, state)

    def _take_page(self):
        """Return the context's existing tab, or open one if none exists.

        Guarantees single-tab discipline: never stacks a new tab on top of
        the blank tab a persistent context already owns.
        """
        try:
            pages = self._ctx.pages if self._ctx is not None else []
            live = [p for p in pages if not p.is_closed()]
            if live:
                return live[0]
            return self._ctx.new_page()
        except Exception:
            return None

    def _page_alive(self):
        """True only if the page handle exists, is not closed, and answers."""
        try:
            if self._page is None or self._page.is_closed():
                return False
            _ = self._page.url  # answers => session alive
            return True
        except Exception:
            return False

    def _navigate_once(self):
        """One navigation pass. Returns (alive, message).

        Uses wait_until="commit": success means the server responded and the
        document started loading. A TimeoutError here means the load event is
        slow (challenge/heavy JS/first run) — the page may still be perfectly
        alive, so aliveness is probed before any verdict.
        """
        import time as _t
        if self._page is None or self._page.is_closed():
            self._page = self._take_page()
        if self._page is None:
            return False, "page create failed: no usable tab"
        start = _t.time()
        self.nav["started"] = _utc()
        try:
            self._page.goto(self.chatgpt_url, wait_until="commit", timeout=60000)
            outcome = "committed"
        except Exception as e:
            outcome = "timeout: %s" % _short(e)
        elapsed = _t.time() - start
        try:
            self._page.wait_for_timeout(2500)
        except Exception:
            pass
        self.nav["ended"] = _utc()
        self.nav["elapsed_s"] = round(elapsed, 1)
        try:
            self.nav["url"] = self._page.url or ""
        except Exception:
            self.nav["url"] = ""
        self.nav["outcome"] = outcome
        if self._page_alive():
            return True, "nav %s in %ss (url=%s)" % (outcome, self.nav["elapsed_s"],
                                                     self.nav["url"] or "?")
        return False, "page dead after nav %s" % outcome

    def _live_tab_count(self):
        """Number of non-closed tabs in the browser context (-1 when unknown)."""
        try:
            pages = self._ctx.pages if self._ctx is not None else []
            return len([p for p in pages if not p.is_closed()])
        except Exception:
            return -1

    @_on_browser_thread
    def _composer_usable(self, budget_ms=READINESS_BUDGET_MS):
        """Single authoritative readiness detector for ALL readiness paths.

        Marshalled to the browser thread (safe from monitor/HTTP threads,
        re-entrant when already on it). Returns the
        find_usable_composer triple (usable, matched_selector, detail).
        """
        return find_usable_composer(self._page, self.selectors, budget_ms)

    def _classify(self):
        """DOM/state-based page classification (never goto-success alone).

        Uses the single authoritative detector with the full startup budget.
        A dead page is UNAVAILABLE here — never LOADING, never READY.
        """
        if not self._page_alive():
            self.page_state = "UNAVAILABLE"
            self.chatgpt = "UNAVAILABLE"
            self.last_error = "DEAD: browser page closed or unreachable during classification"
            return "state=UNAVAILABLE (DEAD: page closed or unreachable)"
        wall = self._wall_state()
        if wall in ("auth-wall", "captcha"):
            self.page_state = "AUTH_REQUIRED"
            self.chatgpt = "AUTHENTICATION_REQUIRED"
            return "state=AUTH_REQUIRED (%s)" % wall
        usable, _sel, detail = self._composer_usable(READINESS_BUDGET_MS)
        if usable:
            self.page_state = "CHATGPT_READY"
            self.chatgpt = "READY"
            self.last_error = ""
            return "state=CHATGPT_READY (%s)" % detail
        self.page_state = "CHATGPT_LOADING"
        self.chatgpt = "LOADING"
        return "state=CHATGPT_LOADING (page alive, UI not present yet — monitoring continues)"

    def _wall_state(self):
        """Check current page for auth/CAPTCHA/bot-challenge walls.

        Inspects title + body: Cloudflare challenges render an (almost) empty
        body with the signal in <title>. Returns 'ok', 'auth-wall', 'captcha',
        or 'unknown'. Never touches credentials or storage.
        """
        try:
            title = self._page.title() or ""
        except Exception:
            title = ""
        try:
            text = self._page.locator("body").first.inner_text(timeout=8000)
        except Exception:
            text = ""
        if "just a moment" in title.lower() and not (text or "").strip():
            return "captcha"
        return detect_walls("%s\n%s" % (title, text), self.selectors)

    @_on_browser_thread
    def quick_ready(self):
        """Lightweight readiness probe (no settle wait) for the auth monitor.

        Safe to call repeatedly while the browser stays open: checks liveness
        (browser up, page answers, tab exists), URL, walls, and composer
        usability through the single authoritative detector with the monitor
        budget. Never navigates, never submits, never touches credentials or
        storage. A dead page returns DEAD (terminal) — never LOADING, so the
        monitor can downgrade instead of retaining stale state.
        """
        if not self.browser_up or self._page is None:
            self.page_state = "UNAVAILABLE"
            self.chatgpt = "UNAVAILABLE"
            self.last_error = "DEAD: no live browser session"
            return False, "UNAVAILABLE", "DEAD: no live browser session"
        try:
            url = self._page.url or ""
        except Exception:
            self.page_state = "UNAVAILABLE"
            self.chatgpt = "UNAVAILABLE"
            self.last_error = "DEAD: browser session lost (page does not answer)"
            return False, "UNAVAILABLE", self.last_error
        if "chatgpt.com" not in url and "chat.openai.com" not in url:
            self.chatgpt = "UNKNOWN"
            return False, "UNAVAILABLE", "not on the ChatGPT page"
        if not self._page_alive():
            self.page_state = "UNAVAILABLE"
            self.chatgpt = "UNAVAILABLE"
            self.last_error = "DEAD: ChatGPT page closed or unreachable"
            return False, "UNAVAILABLE", self.last_error
        if self._live_tab_count() == 0:
            self.page_state = "UNAVAILABLE"
            self.chatgpt = "UNAVAILABLE"
            self.last_error = "DEAD: zero usable ChatGPT tabs remain"
            return False, "UNAVAILABLE", self.last_error
        wall = self._wall_state()
        if wall in ("auth-wall", "captcha"):
            self.page_state = "AUTH_REQUIRED"
            self.chatgpt = "AUTHENTICATION_REQUIRED"
            return False, "UNAVAILABLE", "%s: sign in to ChatGPT manually (%s)" % (
                USER_ACTION_REQUIRED,
                "security check" if wall == "captcha" else "login wall")
        usable, _sel, detail = self._composer_usable(MONITOR_BUDGET_MS)
        if not usable:
            # Live page, no wall, no usable composer => still loading. This is
            # NOT an auth wall and must never be reported as one. Transient
            # only: bounded by the monitor cadence, never a terminal error.
            self.page_state = "CHATGPT_LOADING"
            self.chatgpt = "LOADING"
            return False, "UNAVAILABLE", "ChatGPT still loading (page alive, UI not present)"
        self.page_state = "CHATGPT_READY"
        self.chatgpt = "READY"
        self.last_error = ""
        return True, "OK", "CHATGPT_SESSION_READY (%s)" % detail

    @_on_browser_thread
    def ensure_ready(self):
        """ChatGPT page detection: URL + composer presence + wall check."""
        if not self.browser_up or self._page is None:
            return False, "UNAVAILABLE", "no live browser session"
        try:
            url = self._page.url or ""
        except Exception:
            return False, "UNAVAILABLE", "browser session lost"
        if "chatgpt.com" not in url and "chat.openai.com" not in url:
            try:
                self._page.goto(self.chatgpt_url, wait_until="domcontentloaded", timeout=45000)
                self._page.wait_for_timeout(2500)
            except Exception as e:
                return False, "UNAVAILABLE", "navigation failed: %s" % _short(e)
        wall = self._wall_state()
        if wall == "captcha":
            # Bot challenge (e.g. Cloudflare "Just a moment...") sometimes
            # clears on its own in a real browser profile — allow bounded
            # settle time, then report honestly. Never bypassed.
            for _ in range(4):
                self._page.wait_for_timeout(5000)
                wall = self._wall_state()
                if wall != "captcha":
                    break
        if wall in ("auth-wall", "captcha"):
            self.chatgpt = "AUTHENTICATION_REQUIRED"
            self.last_error = "%s: sign in to ChatGPT manually (%s)" % (
                USER_ACTION_REQUIRED, "security check" if wall == "captcha" else "login wall")
            return False, "UNAVAILABLE", self.last_error
        return self.quick_ready()

    def _find_first(self, fallback_chain, timeout_ms=8000):
        """First visible locator across the registry fallback chain, else None."""
        for sel in fallback_chain:
            try:
                loc = self._page.locator(sel).first
                loc.wait_for(state="visible", timeout=timeout_ms)
                return loc
            except Exception:
                continue
        return None

    def _assistant_count(self):
        try:
            return self._page.locator(
                self.selectors["assistant_messages"]["fallback_chain"][0]).count()
        except Exception:
            return -1

    def _last_assistant_text(self):
        for sel in self.selectors["assistant_messages"]["fallback_chain"]:
            try:
                loc = self._page.locator(sel)
                if loc.count() > 0:
                    return loc.last.inner_text(timeout=8000)
            except Exception:
                continue
        return ""

    def _generating(self):
        for sel in self.selectors["stop_button"]["fallback_chain"]:
            try:
                if self._page.locator(sel).first.is_visible():
                    return True
            except Exception:
                continue
        return False

    # -- task transport --------------------------------------------------
    @_on_browser_thread
    def send_prompt(self, prompt_text):
        """Inject the prompt into the composer and submit. Bounded single retry."""
        for attempt in (1, 2):
            composer = self._find_first(self.selectors["composer"]["fallback_chain"])
            if composer is None:
                if attempt == 1:
                    try:
                        self._page.reload(wait_until="domcontentloaded", timeout=30000)
                        self._page.wait_for_timeout(2500)
                        continue
                    except Exception:
                        pass
                return False, "ERROR", "selector failure: composer not found (attempt %d)" % attempt
            try:
                before = self._assistant_count()
                try:
                    composer.click(timeout=8000)
                    composer.fill(prompt_text, timeout=15000)
                except Exception:
                    # contenteditable fallback: click + sequential typing
                    composer.click(timeout=8000)
                    self._page.keyboard.press("ControlOrMeta+a")
                    self._page.keyboard.type(prompt_text, delay=2)
                send_btn = self._find_first(self.selectors["send_button"]["fallback_chain"],
                                            timeout_ms=5000)
                if send_btn is not None:
                    send_btn.click(timeout=8000)
                else:
                    self._page.keyboard.press("Enter")
                self._page.wait_for_timeout(2500)
                return True, "OK", "message submitted (assistant turns before=%d)" % before
            except Exception as e:
                if attempt == 2:
                    return False, "ERROR", "submit failed: %s" % _short(e)
                try:
                    self._page.reload(wait_until="domcontentloaded", timeout=30000)
                    self._page.wait_for_timeout(2500)
                except Exception:
                    return False, "ERROR", "submit failed + reload failed: %s" % _short(e)
        return False, "ERROR", "submit failed after retry"

    @_on_browser_thread
    def wait_completion(self, timeout_seconds=None):
        """Completion detection: stop-button-gone + count-stable + tail-stable.

        Timeout is NEVER success — it returns TIMEOUT explicitly.
        """
        limit = timeout_seconds or self.response_timeout_seconds
        comp = self.selectors.get("completion", {})
        need = int(comp.get("stable_polls_required", 3))
        interval = float(comp.get("poll_interval_ms", 1500)) / 1000.0
        stable, last_tail, last_count = 0, None, None
        deadline = time.time() + limit
        while time.time() < deadline:
            if self._wall_state() in ("auth-wall", "captcha"):
                return False, "UNAVAILABLE", "%s: wall appeared mid-generation" % USER_ACTION_REQUIRED
            generating = self._generating()
            count = self._assistant_count()
            tail = (self._last_assistant_text() or "")[-200:]
            if (not generating and count == last_count and tail
                    and tails_stable(last_tail, tail)):
                stable += 1
            else:
                stable = 0
            last_tail, last_count = tail, count
            if stable >= need and tail:
                return True, "OK", "generation completed (turns=%s)" % count
            time.sleep(interval)
        return False, "TIMEOUT", "response timeout after %ds (never treated as success)" % limit

    @_on_browser_thread
    def extract_response(self):
        """Extract the newest assistant message. Empty => explicit failure."""
        text = (self._last_assistant_text() or "").strip()
        if not text:
            return False, "ERROR", "response extraction failure: no assistant text found"
        return True, "OK", text

    @_on_browser_thread
    def ask(self, prompt_text, timeout_seconds=None):
        """Full AUTO round-trip. Returns (ok, status, body_or_reason)."""
        ok, status, msg = self.ensure_ready()
        if not ok:
            return False, status, msg
        ok, status, msg = self.send_prompt(prompt_text)
        if not ok:
            return False, status, msg
        ok, status, msg = self.wait_completion(timeout_seconds)
        if not ok:
            return False, status, msg
        return self.extract_response()

    @_on_browser_thread
    def diagnose(self):
        """Secret-free diagnostic snapshot for the required status block."""
        try:
            pages = self._ctx.pages if self._ctx is not None else []
            tabs = len([p for p in pages if not p.is_closed()])
        except Exception:
            tabs = -1
        return {
            "mode": "AUTO",
            "browser": "READY" if self.browser_up else "DOWN",
            "browser_engine": self.browser_name,
            "tabs": tabs,
            "page_state": self.page_state,
            "chatgpt": self.chatgpt,
            "profile": self.profile_dir,
            "headless": self.headless,
            "nav_outcome": self.nav.get("outcome", "none"),
            "nav_url": self.nav.get("url", ""),
            "nav_elapsed_s": self.nav.get("elapsed_s", 0.0),
            "last_error": self.last_error,
        }

    @_on_browser_thread
    def dom_probe(self, extra_selectors=None):
        """Structural DOM probe (counts + visibility only).

        Inspects URL, title, readyState, wall class, per-selector
        count/visibility, frame count, top-level tags. NEVER page text,
        cookies, storage, or credentials. Runs on the browser thread.
        """
        try:
            url = self._page.url or ""
            title = self._page.title() or ""
            ready = self._page.evaluate("document.readyState") or "?"
        except Exception as e:
            return {"ok": False, "status": "UNAVAILABLE",
                    "reason": "page does not answer: %s" % _short(e)}
        try:
            wall = self._wall_state()
        except Exception:
            wall = "unknown"
        suite = list(self.selectors.get("composer", {}).get("fallback_chain", []))
        suite += ["textarea", "[contenteditable='true']", "[role='textbox']",
                  "form", "main", "[data-testid]"]
        seen, ordered = set(), []
        for s in list(suite) + list(extra_selectors or []):
            if isinstance(s, str) and s not in seen:
                seen.add(s)
                ordered.append(s)
        probes = []
        for sel in ordered[:40]:
            try:
                loc = self._page.locator(sel)
                n = loc.count()
                vis = bool(loc.first.is_visible()) if n > 0 else False
            except Exception:
                n, vis = -1, False
            probes.append({"selector": sel, "count": n, "visible": vis})
        try:
            frames = len(self._page.frames)
        except Exception:
            frames = -1
        try:
            tags = self._page.evaluate(
                "document.body ? [...document.body.children]"
                ".map(e=>e.tagName).slice(0,25) : []")
        except Exception:
            tags = []
        try:
            tabs = len([p for p in self._ctx.pages if not p.is_closed()])
        except Exception:
            tabs = -1
        return {"ok": True, "url": url, "title": title, "ready_state": ready,
                "wall": wall, "tabs": tabs, "frames": frames,
                "top_tags": tags, "probes": probes}

    def profile_status(self):
        """Dedicated-profile health: exists + non-empty (login state stays in-browser)."""
        try:
            if not os.path.isdir(self.profile_dir):
                return "MISSING (will be created on launch)"
            entries = os.listdir(self.profile_dir)
            if not entries:
                return "EMPTY (first run — manual ChatGPT login required)"
            return "PRESENT (%d entries)" % len(entries)
        except Exception as e:
            return "UNKNOWN (%s)" % _short(e)

    @_on_browser_thread
    def close(self, quiet=False):
        try:
            if self._ctx is not None:
                self._ctx.close()
        except Exception:
            pass
        try:
            if self._pw is not None:
                self._pw.stop()
        except Exception:
            pass
        self._pw, self._ctx, self._page = None, None, None
        self.browser_up = False
        if not quiet:
            return True, "adapter stopped (browser shut down gracefully)"
        return True, "closed"


def _short(exc, limit=160):
    try:
        msg = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
    except Exception:
        msg = "error"
    # Never leak page dumps: keep only the first short line.
    return msg[:limit]


def _utc():
    try:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    except Exception:
        return ""


class ChatGPTAdapter:
    """Lifecycle wrapper over MANUAL bridge and AUTO Playwright driver."""

    STATES = ("DISCONNECTED", "STARTING", "BROWSER_READY", "CHATGPT_READY",
              "BUSY", "WAITING_RESPONSE", "CONNECTED", "ERROR")

    def __init__(self, driver="manual", profile_dir=None, chatgpt_url="https://chatgpt.com/",
                 headless=True, response_timeout_seconds=180, fallback_to_manual=False,
                 browser_name="chromium"):
        self.driver = detect_driver(driver)
        self.browser_name = browser_name if browser_name in AutoDriver.ENGINES else "chromium"
        self.driver = detect_driver(driver)
        self.profile_dir = profile_dir or os.path.join(os.path.expanduser("~"), ".tidos", "gptid-profile")
        self.chatgpt_url = chatgpt_url
        self.headless = headless
        self.response_timeout_seconds = response_timeout_seconds
        # Req 18: AUTO failure falls back to MANUAL only when explicitly configured.
        self.fallback_to_manual = fallback_to_manual
        self.state = "DISCONNECTED"
        self.last_error = ""
        self.auto = None

    # -- lifecycle ------------------------------------------------------
    def start(self):
        self.state = "STARTING"
        if self.driver == "manual":
            # MANUAL has no browser to crash; readiness = user confirms tab open.
            self.state = "BROWSER_READY"
            return True, "MANUAL bridge ready (open your ChatGPT Free tab)"
        if not playwright_available():
            self.state = "ERROR"
            self.last_error = "playwright not installed"
            return False, "UNAVAILABLE: playwright not installed (use MANUAL bridge)"
        self.auto = AutoDriver(profile_dir=self.profile_dir, chatgpt_url=self.chatgpt_url,
                               headless=self.headless,
                               response_timeout_seconds=self.response_timeout_seconds,
                               browser_name=self.browser_name)
        ok, _, msg = self.auto.launch()
        if not ok:
            self.state = "ERROR"
            self.last_error = msg
            return False, "STATUS=UNAVAILABLE (reason=%s)" % msg
        self.state = "BROWSER_READY"
        return True, "browser profile ready (%s): %s" % (self.auto.browser_name, self.profile_dir)

    def confirm_chatgpt_page(self, user_confirmed=False):
        """MANUAL: only CHATGPT_READY after explicit user confirmation.
        AUTO: live page detection (URL + composer + wall check)."""
        if self.driver == "manual":
            if user_confirmed:
                self.state = "CHATGPT_READY"
                return True, "CHATGPT_SESSION_READY (user-confirmed)"
            return False, "STATUS=UNAVAILABLE (reason=user has not confirmed the ChatGPT tab yet)"
        if self.auto is None:
            self.state = "ERROR"
            self.last_error = "auto page detection needs a live browser session"
            return False, "STATUS=UNAVAILABLE (reason=no live browser session)"
        ok, status, msg = self.auto.ensure_ready()
        if ok:
            self.state = "CHATGPT_READY"
            return True, msg
        # Auth/CAPTCHA wall: honest pause, NOT an error state wipeout.
        if USER_ACTION_REQUIRED in msg:
            self.state = "BROWSER_READY"
            self.last_error = msg
            return False, "STATUS=UNAVAILABLE (reason=%s)" % msg
        # Still loading (page alive): keep the browser open and monitoring.
        if "still loading" in msg:
            self.state = "BROWSER_READY"
            self.last_error = msg
            return False, "STATUS=UNAVAILABLE (reason=%s)" % msg
        self.state = "ERROR"
        self.last_error = msg
        return False, "STATUS=%s (reason=%s)" % (status, msg)

    def diagnose_block(self):
        """Required diagnostic block (secret-free)."""
        if self.driver == "manual":
            return ("GPTID MODE: MANUAL\nBROWSER: N/A (human bridge)\n"
                    "CHATGPT: USER_MANAGED\nRELAY: %s" % self.state)
        snap = self.auto.diagnose() if self.auto else {"browser": "DOWN", "chatgpt": "UNKNOWN",
                                                         "page_state": "UNKNOWN"}
        chatgpt = snap["chatgpt"]
        if chatgpt == "AUTHENTICATION_REQUIRED":
            return ("GPTID MODE: AUTO\nBROWSER: %s\nCHATGPT: AUTHENTICATION_REQUIRED\n"
                    "RELAY: %s\nreason=%s" % (snap["browser"], self.state, USER_ACTION_REQUIRED))
        if chatgpt == "LOADING" or snap.get("page_state") == "CHATGPT_LOADING":
            return ("GPTID MODE: AUTO\nBROWSER: %s\nCHATGPT: LOADING\n"
                    "RELAY: %s" % (snap["browser"], self.state))
        if chatgpt == "UNAVAILABLE" or snap.get("page_state") == "UNAVAILABLE":
            return ("GPTID MODE: AUTO\nBROWSER: %s\nCHATGPT: UNAVAILABLE\n"
                    "RELAY: %s\nreason=%s" % (snap["browser"], self.state,
                                              snap.get("last_error", "dead page")))
        ready = "READY" if (snap["browser"] == "READY" and self.state in
                            ("CHATGPT_READY", "CONNECTED")) else snap["browser"]
        return ("GPTID MODE: AUTO\nBROWSER: %s\nCHATGPT: %s\nRELAY: %s"
                % (snap["browser"], chatgpt if chatgpt != "UNKNOWN" else ready, self.state))

    def stop(self):
        if self.auto is not None:
            self.auto.close(quiet=True)
            self.auto = None
        self.state = "DISCONNECTED"
        return True, "adapter stopped"

    # -- task transport --------------------------------------------------
    def send_task(self, task):
        if self.driver == "manual":
            self.state = "WAITING_RESPONSE"
            return True, render_sent_block(task)
        if self.auto is None:
            return False, "STATUS=UNAVAILABLE (reason=no live browser session)"
        # AUTO: full round-trip inside the send call (caller runs it on a worker thread).
        self.state = "BUSY"
        ok, status, body = self.auto.ask(render_auto_prompt(task), self.response_timeout_seconds)
        if ok:
            self.state = "WAITING_RESPONSE"  # response stored; /poll collects it
            return True, body
        self.state = "ERROR" if status != "UNAVAILABLE" else "BROWSER_READY"
        self.last_error = body
        hint = ""
        if self.fallback_to_manual:
            hint = " (fallback_to_manual=true: re-send with driver=manual)"
        return False, "STATUS=%s (reason=%s)%s" % (status, body, hint)

    def note_response(self, task_id, body):
        self.state = "CONNECTED"
        return {"task_id": task_id, "status": "OK", "chatgpt_response": body}
