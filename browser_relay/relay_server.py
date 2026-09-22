"""GPTID local Browser Relay server (stdlib only + optional Playwright AUTO driver).

Endpoints (all JSON, localhost only by default):
  GET  /health  -> {ok, relay, driver, browser, chatgpt, state}
  GET  /status  -> state + driver diagnostics + correlation counters
  POST /send    -> MANUAL: queue task, return copyable sent_block.
                   AUTO: full browser round-trip (bounded), return auto_response envelope.
  POST /poll    -> MANUAL: submit a RECEIVED body for a task_id.
                   AUTO: empty body returns the stored round-trip response.
  POST /reset   -> reset conversation/task correlation (browser session kept)

Run:  python relay_server.py --port 8765 --driver manual
      python relay_server.py --port 8765 --driver auto [--headed] [--response-timeout 180]
Never binds 0.0.0.0 unless --host is explicitly overridden.
"""
import argparse
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gptid_protocol import (  # noqa: E402
    build_response, redact_secrets, task_matches_response, validate_response, validate_task,
)
from chatgpt_adapter import (  # noqa: E402
    DOM_PROBE_BUDGET_MS, ChatGPTAdapter, parse_received_block,
)

STATE = {
    "relay": "DISCONNECTED",
    "tasks": {},   # task_id -> {task, status, auto_response?}
    "history": [],  # last N task_ids
    "queue": [],    # FIFO task_ids accepted while AUTH_REQUIRED (AUTO only)
    "conversation": {"id": None, "resets": 0},
    "max_history": 5,
}
ADAPTER = None
ADAPTER_LOCK = threading.Lock()
MONITOR_INTERVAL_SECONDS = 10


def set_state(value):
    STATE["relay"] = value


def _diag():
    if ADAPTER is None:
        return {"driver": "none", "browser": "DOWN", "chatgpt": "UNKNOWN"}
    if ADAPTER.driver == "manual":
        return {"driver": "manual", "browser": "N/A", "chatgpt": "USER_MANAGED"}
    snap = ADAPTER.auto.diagnose() if ADAPTER.auto else {"browser": "DOWN", "chatgpt": "UNKNOWN",
                                                           "page_state": "UNKNOWN"}
    out = {"driver": "auto", "browser": snap["browser"], "chatgpt": snap["chatgpt"],
           "browser_engine": snap.get("browser_engine", "?"),
           "tabs": snap.get("tabs", -1),
           "page_state": snap.get("page_state", "UNKNOWN"),
           "nav_outcome": snap.get("nav_outcome", "none"),
           "nav_url": snap.get("nav_url", "")}
    return out


# Markers identifying a TERMINAL browser/page death (vs transient LOADING).
DEAD_MARKERS = ("DEAD:", "session lost", "no live browser session",
                "page does not answer", "zero usable ChatGPT tabs")


def _probe_dead(msg):
    """True when a probe reason reports terminal page death (never transient)."""
    text = str(msg or "")
    if text.startswith("DEAD:"):
        return True
    return any(m in text for m in DEAD_MARKERS[1:])


def _adapter_dead(auto):
    """Adapter truth: is the browser page terminally dead?

    Dead when the adapter already classified UNAVAILABLE/ERROR, or when a
    recorded DEAD marker survives while the adapter is not READY (stale
    last_error can never mask a live READY session).
    """
    if auto.page_state in ("UNAVAILABLE", "ERROR") or auto.chatgpt == "UNAVAILABLE":
        return True
    if auto.chatgpt == "READY" and auto.page_state == "CHATGPT_READY":
        return False
    return _probe_dead(getattr(auto, "last_error", ""))


def sync_relay_state(reason="", adapter=None):
    """One canonical relay/adapter reconciliation. Adapter truth always wins.

    Invariants enforced (never the reverse):
      adapter LOADING      => relay cannot be CHATGPT_READY (downgrade)
      dead page            => relay cannot be CHATGPT_READY (ERROR)
      zero-usable-tabs     => surfaced as dead by the probe, hence ERROR
      composer unusable    => probe reports LOADING, hence not CHATGPT_READY
    Returns DOWNGRADED-ERROR | DOWNGRADED-LOADING | CONSISTENT | SKIP.
    """
    ad = adapter if adapter is not None else ADAPTER
    if ad is None or ad.driver != "auto" or ad.auto is None:
        return "SKIP"
    auto = ad.auto
    if _adapter_dead(auto):
        if ad.state in ("CHATGPT_READY", "BROWSER_READY", "CONNECTED",
                        "BUSY", "WAITING_RESPONSE"):
            ad.state = "ERROR"
        if STATE["relay"] in ("CHATGPT_READY", "CONNECTED", "BUSY",
                              "WAITING_RESPONSE", "BROWSER_READY"):
            set_state("ERROR")
        sys.stderr.write("[GPTID] state downgraded to ERROR (dead page) %s\n"
                         % redact_secrets(reason)[:120])
        return "DOWNGRADED-ERROR"
    if auto.chatgpt == "LOADING" or auto.page_state == "CHATGPT_LOADING":
        if ad.state == "CHATGPT_READY":
            ad.state = "BROWSER_READY"
        if STATE["relay"] == "CHATGPT_READY":
            set_state("BROWSER_READY")
        return "DOWNGRADED-LOADING"
    return "CONSISTENT"


def _drain_queue():
    """Process tasks queued while AUTH_REQUIRED (AUTO only, FIFO, bounded).

    Called by the auth monitor right after the AUTH_REQUIRED → CHATGPT_READY
    transition — no relay restart, browser stays open. Failures are stored
    machine-readable; silent success is impossible (validate + correlate).
    """
    while STATE["queue"]:
        task_id = STATE["queue"][0]
        entry = STATE["tasks"].get(task_id)
        if entry is None:
            STATE["queue"].pop(0)
            continue
        task = entry["task"]
        sys.stderr.write("[GPTID] auto-drain queued task: %s\n" % redact_secrets(task_id))
        with ADAPTER_LOCK:
            ok, result = ADAPTER.send_task(task)
        if ok:
            resp = build_response(task["task_id"], task["session_id"], chatgpt_response=result)
            if validate_response(resp) or not task_matches_response(task, resp):
                entry["status"] = "MALFORMED"
            else:
                entry["status"] = "OK"
                entry["auto_response"] = resp
                set_state("CONNECTED")
                sys.stderr.write("[GPTID] Response received for %s (AUTO, queued)\n"
                                 % redact_secrets(task_id))
                sys.stderr.write("[GPTID] Task completed: %s\n" % redact_secrets(task_id))
        else:
            status, _reason = _split_status(result)
            entry["status"] = status
            if status != "UNAVAILABLE":
                set_state("ERROR")
        STATE["queue"].pop(0)


def _monitor_loop():
    """First-run auth/resume monitor (AUTO only).

    While the browser stays open, re-probes readiness every
    MONITOR_INTERVAL_SECONDS (cadence only — detection semantics and budget
    live in the shared detector). On AUTH_REQUIRED → CHATGPT_READY it flips
    the state (no restart) and auto-drains the queue. On terminal page death
    it DOWNGrades through sync_relay_state — a previous READY is never
    silently retained, so stale LOADING/READY cannot persist. It only ever
    upgrades BROWSER_READY → CHATGPT_READY on a live READY probe; it never
    touches credentials, cookies, or storage.
    """
    while True:
        time.sleep(MONITOR_INTERVAL_SECONDS)
        try:
            if ADAPTER is None or ADAPTER.driver != "auto" or ADAPTER.auto is None:
                continue
            if not ADAPTER.auto.browser_up:
                # Browser genuinely down: adapter truth wins over cached READY.
                sync_relay_state("browser down")
                continue
            with ADAPTER_LOCK:
                ok, _status, _msg = ADAPTER.auto.quick_ready()
            if ok:
                if ADAPTER.state != "CHATGPT_READY":
                    ADAPTER.state = "CHATGPT_READY"
                if STATE["relay"] == "BROWSER_READY":
                    set_state("CHATGPT_READY")
                    sys.stderr.write("[GPTID] CHATGPT_SESSION_READY "
                                     "(auth detected while browser open, no restart)\n")
                if STATE["queue"]:
                    _drain_queue()
            else:
                # Transient LOADING leaves state alone (bounded by cadence);
                # terminal death downgrades. Either way, cached READY can
                # never contradict adapter truth afterwards.
                sync_relay_state(_msg)
        except Exception as e:
            sys.stderr.write("[GPTID] monitor error: %s\n" % redact_secrets(str(e))[:120])


def handle_handshake(adapter):
    """GPTID_HANDSHAKE sequence. Returns the transcript lines."""
    transcript = []
    ok, msg = adapter.start()
    transcript.append("BROWSER_RELAY_CONNECTED" if ok else "STATUS=UNAVAILABLE (%s)" % msg)
    if not ok:
        set_state("ERROR")
        return transcript
    set_state("BROWSER_READY")
    transcript.append("BROWSER_READY (driver=%s)" % adapter.driver)
    if adapter.driver == "manual":
        # MANUAL stops at BROWSER_READY; CHATGPT_READY needs the user.
        transcript.append("AWAITING_USER_CONFIRM (open your ChatGPT Free tab, then send)")
        return transcript
    ok, msg = adapter.confirm_chatgpt_page()
    if ok:
        transcript.append("CHATGPT_PAGE_DETECTED")
        transcript.append("CHATGPT_SESSION_READY")
        transcript.append("READY")
        set_state("CHATGPT_READY")
    elif "still loading" in msg:
        transcript.append("CHATGPT_LOADING (browser alive, page still loading — monitoring continues)")
        set_state("BROWSER_READY")
    elif "USER_ACTION_REQUIRED" in msg:
        transcript.append("CHATGPT_AUTHENTICATION_REQUIRED (USER_ACTION_REQUIRED: "
                          "sign in to ChatGPT manually, then re-run)")
        set_state("BROWSER_READY")
    else:
        transcript.append("STATUS=ERROR (%s)" % msg)
        set_state("ERROR")
    return transcript


class Handler(BaseHTTPRequestHandler):
    server_version = "GPTIDRelay/1.0"

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except Exception:
            length = 0
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except Exception:
            return {"_malformed": True}

    def log_message(self, fmt, *args):  # quiet + secret-safe logging
        try:  # a logging failure must never kill the HTTP response
            line = redact_secrets(fmt % args)
            sys.stderr.write("[GPTID] relay %s\n" % line)
        except Exception:
            pass

    def do_GET(self):
        if self.path == "/health":
            payload = {"ok": True, "relay": "gptid-browser-relay", "state": STATE["relay"]}
            payload.update(_diag())
            self._send_json(200, payload)
        elif self.path == "/status":
            payload = {"state": STATE["relay"],
                       "pending": sum(1 for t in STATE["tasks"].values()
                                      if t["status"] == "WAITING_RESPONSE"),
                       "queued": len(STATE["queue"]),
                       "history": STATE["history"][-STATE["max_history"]:],
                       "conversation_resets": STATE["conversation"]["resets"]}
            payload.update(_diag())
            self._send_json(200, payload)
        elif self.path == "/dom_probe":
            # Structural DOM diagnostic (AUTO only). Counts + visibility only —
            # never page text, cookies, storage, or credentials.
            self._send_json(*_dom_probe([]))
        else:
            self._send_json(404, {"ok": False, "status": "ERROR", "reason": "unknown endpoint"})

    def _store_task(self, task, status):
        STATE["tasks"][task["task_id"]] = {"task": task, "status": status}
        STATE["history"].append(task["task_id"])
        STATE["history"] = STATE["history"][-STATE["max_history"]:]

    def do_POST(self):
        global ADAPTER
        if self.path == "/send":
            task = self._read_json()
            errors = validate_task(task)
            if errors:
                self._send_json(400, {"ok": False, "status": "MALFORMED", "errors": errors})
                return
            if ADAPTER.driver == "auto":
                self._send_auto(task)
                return
            ok, sent = ADAPTER.send_task(task)
            self._store_task(task, "WAITING_RESPONSE")
            set_state("WAITING_RESPONSE")
            sys.stderr.write("[GPTID] Task sent: %s\n" % redact_secrets(task["task_id"]))
            self._send_json(200, {"ok": ok, "task_id": task["task_id"],
                                  "session_id": task["session_id"],
                                  "sent_block": redact_secrets(sent)})
        elif self.path == "/poll":
            payload = self._read_json()
            task_id = payload.get("task_id", "")
            body = payload.get("chatgpt_response", "")
            entry = STATE["tasks"].get(task_id)
            if not entry:
                self._send_json(404, {"ok": False, "status": "ERROR",
                                      "reason": "conversation mismatch: unknown task_id"})
                return
            # AUTO stored round-trip: empty body collects it (no paste needed).
            if not body and entry.get("auto_response"):
                out = dict(entry["auto_response"])
                out["ok"] = True
                self._send_json(200, out)
                return
            # Queued behind AUTH_REQUIRED: report position, never fake a reply.
            if not body and entry.get("status") == "QUEUED":
                try:
                    pos = STATE["queue"].index(task_id) + 1
                except ValueError:
                    pos = 0
                self._send_json(200, {"ok": False, "status": "QUEUED",
                                      "task_id": task_id,
                                      "position": pos,
                                      "reason": "waiting for ChatGPT READY; queued task "
                                                "runs automatically after login"})
                return
            good, parsed = parse_received_block(body)
            if not good:
                self._send_json(400, {"ok": False, "status": "MALFORMED",
                                      "reason": parsed, "task_id": task_id})
                return
            resp = build_response(task_id, entry["task"]["session_id"], chatgpt_response=parsed)
            verr = validate_response(resp)
            if verr or not task_matches_response(entry["task"], resp):
                self._send_json(400, {"ok": False, "status": "MALFORMED",
                                      "errors": verr, "task_id": task_id})
                return
            entry["status"] = "OK"
            set_state("CONNECTED")
            sys.stderr.write("[GPTID] Response received for %s\n" % redact_secrets(task_id))
            out = dict(resp)
            out["ok"] = True
            self._send_json(200, out)
        elif self.path == "/reset":
            STATE["tasks"].clear()
            STATE["history"].clear()
            STATE["queue"].clear()
            STATE["conversation"]["resets"] += 1
            set_state("BROWSER_READY")
            self._send_json(200, {"ok": True, "resets": STATE["conversation"]["resets"]})
        elif self.path == "/dom_probe":
            payload = self._read_json()
            sels = payload.get("selectors", []) if isinstance(payload, dict) else []
            code, out = _dom_probe([s for s in sels if isinstance(s, str)][:40])
            self._send_json(code, out)
        else:
            self._send_json(404, {"ok": False, "status": "ERROR", "reason": "unknown endpoint"})

    def _send_auto(self, task):
        """AUTO send: round-trip immediately when READY, else queue.

        Browser down → UNAVAILABLE (start the relay first). Browser up but
        AUTH_REQUIRED → task is QUEUED (HTTP 200, status QUEUED); the auth
        monitor auto-processes it after login — no restart, no mode switch.
        """
        if ADAPTER.auto is None or not ADAPTER.auto.browser_up:
            self._store_task(task, "UNAVAILABLE")
            self._send_json(200, {"ok": False, "status": "UNAVAILABLE",
                                  "task_id": task["task_id"],
                                  "reason": "browser not running; start the relay first"})
            return
        with ADAPTER_LOCK:
            ready, _s, _m = ADAPTER.auto.quick_ready()
        if not ready and _probe_dead(_m):
            # Terminal page death: never queue behind a dead page (the task
            # could never run) — report UNAVAILABLE and reconcile state.
            self._store_task(task, "UNAVAILABLE")
            sync_relay_state(_m)
            self._send_json(200, {"ok": False, "status": "UNAVAILABLE",
                                  "task_id": task["task_id"],
                                  "reason": _m})
            return
        if ready:
            ADAPTER.state = "CHATGPT_READY"
            if STATE["relay"] == "BROWSER_READY":
                set_state("CHATGPT_READY")
        else:
            # Keep the browser open, expose AUTH_REQUIRED, queue the task.
            self._store_task(task, "QUEUED")
            if task["task_id"] not in STATE["queue"]:
                STATE["queue"].append(task["task_id"])
            if STATE["relay"] != "BROWSER_READY":
                set_state("BROWSER_READY")
            sys.stderr.write("[GPTID] Task queued: %s (AUTH_REQUIRED, position %d)\n"
                             % (redact_secrets(task["task_id"]), len(STATE["queue"])))
            self._send_json(200, {"ok": True, "queued": True, "status": "QUEUED",
                                  "task_id": task["task_id"],
                                  "session_id": task["session_id"],
                                  "position": len(STATE["queue"]),
                                  "reason": "USER_ACTION_REQUIRED: sign in to ChatGPT "
                                            "in the GPTID browser window; queued task "
                                            "runs automatically once READY"})
            return
        sys.stderr.write("[GPTID] Task sent: %s (AUTO)\n" % redact_secrets(task["task_id"]))
        sys.stderr.write("[GPTID] Waiting for response (AUTO browser round-trip)\n")
        set_state("BUSY")
        with ADAPTER_LOCK:
            ok, result = ADAPTER.send_task(task)
        if ok:
            resp = build_response(task["task_id"], task["session_id"], chatgpt_response=result)
            verr = validate_response(resp)
            if verr or not task_matches_response(task, resp):
                entry = {"task": task, "status": "MALFORMED"}
                STATE["tasks"][task["task_id"]] = entry
                self._store_task(task, "MALFORMED")
                set_state("ERROR")
                self._send_json(200, {"ok": False, "status": "MALFORMED",
                                      "task_id": task["task_id"], "errors": verr})
                return
            STATE["tasks"][task["task_id"]] = {"task": task, "status": "OK",
                                               "auto_response": resp}
            STATE["history"].append(task["task_id"])
            STATE["history"] = STATE["history"][-STATE["max_history"]:]
            set_state("CONNECTED")
            sys.stderr.write("[GPTID] Response received for %s (AUTO)\n"
                             % redact_secrets(task["task_id"]))
            sys.stderr.write("[GPTID] Task completed: %s\n" % redact_secrets(task["task_id"]))
            out = {"ok": True, "task_id": task["task_id"], "session_id": task["session_id"],
                   "mode": "auto",
                   "sent_block": "[AUTO round-trip captured %d chars]" % len(result),
                   "auto_response": resp}
            self._send_json(200, out)
        else:
            # result is "STATUS=<S> (reason=<R>)" — surface it machine-readable.
            status, reason = _split_status(result)
            self._store_task(task, status)
            set_state("BROWSER_READY" if status == "UNAVAILABLE" else "ERROR")
            self._send_json(200, {"ok": False, "status": status,
                                  "task_id": task["task_id"], "reason": reason})


def _dom_probe(extra_selectors):
    """Structural DOM probe against the live AUTO page (no restart needed).

    Returns (http_code, payload). Inspects ONLY structure: URL, title,
    readyState, wall class, per-selector count/visibility, frame count,
    top-level tags, PLUS the verdict of the same authoritative
    composer_usable detector the readiness paths use (same semantics,
    diagnostic budget) — so the output proves the signals the real
    detector decides on. NEVER page text, cookies, storage, or credentials.
    POST /dom_probe with {"selectors": [...]} tests custom candidates.
    """
    if ADAPTER is None or ADAPTER.driver != "auto" or ADAPTER.auto is None:
        return 409, {"ok": False, "status": "ERROR",
                     "reason": "dom_probe needs a live AUTO driver"}
    try:
        out = ADAPTER.auto.dom_probe(extra_selectors)
    except Exception as e:
        return 200, {"ok": False, "status": "ERROR",
                     "reason": "probe failed: %s" % str(e)[:160]}
    try:
        with ADAPTER_LOCK:
            usable, sel, detail = ADAPTER.auto._composer_usable(DOM_PROBE_BUDGET_MS)
    except Exception as e:
        usable, sel, detail = False, None, "detector error: %s" % str(e)[:120]
    out["detector"] = "composer_usable(semantic-first)"
    out["composer_usable"] = usable
    out["composer_selector"] = sel
    out["composer_detail"] = detail
    out["readiness_budget_ms"] = DOM_PROBE_BUDGET_MS
    return 200, out


def _split_status(text):
    """Parse 'STATUS=<S> (reason=<R>)...' into (S, R). Defaults to ERROR."""
    try:
        inner = text.split("STATUS=", 1)[1]
        status = inner.split(" ", 1)[0].strip("()")
        reason = inner.split("(reason=", 1)[1].rsplit(")", 1)[0] if "(reason=" in inner else inner
        if status not in ("OK", "UNAVAILABLE", "TIMEOUT", "MALFORMED", "REJECTED", "ERROR"):
            status = "ERROR"
        return status, reason
    except Exception:
        return "ERROR", text


def main(argv=None):
    global ADAPTER
    try:  # never crash logging on non-ASCII page/response text
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="GPTID local browser relay")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--driver", default="auto", choices=("manual", "auto"))
    ap.add_argument("--browser", default="chromium",
                    choices=("firefox", "firefox-nightly", "chromium"),
                    help="AUTO engine (default chromium = Playwright-bundled build)")
    ap.add_argument("--headed", action="store_true",
                    help="AUTO: show the browser window (needed for first manual login)")
    ap.add_argument("--response-timeout", type=int, default=180)
    ap.add_argument("--profile", default="")
    args = ap.parse_args(argv)
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print("[GPTID] WARNING: non-localhost bind requested (%s). Refusing unless GPTID_ALLOW_REMOTE=1."
              % args.host)
        if os.environ.get("GPTID_ALLOW_REMOTE") != "1":
            print("[GPTID] Binding to 127.0.0.1 instead.")
            args.host = "127.0.0.1"
    ADAPTER = ChatGPTAdapter(driver=args.driver,
                             profile_dir=(args.profile or None),
                             headless=(not args.headed),
                             response_timeout_seconds=args.response_timeout,
                             browser_name=args.browser)
    set_state("STARTING")
    print("[GPTID] Starting")
    for line in handle_handshake(ADAPTER):
        print("[GPTID] %s" % line)
    print("[GPTID] Browser relay started on %s:%d (driver=%s)" % (args.host, args.port, ADAPTER.driver))
    if ADAPTER.driver == "auto" and ADAPTER.auto is not None:
        print("[GPTID] %s" % ADAPTER.diagnose_block().replace("\n", " | "))
    if ADAPTER.driver == "auto":
        monitor = threading.Thread(target=_monitor_loop, daemon=True,
                                   name="gptid-auth-monitor")
        monitor.start()
        print("[GPTID] auth monitor started (AUTH_REQUIRED -> READY, queued auto-drain)")
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if ADAPTER is not None:
            ADAPTER.stop()
    print("[GPTID] relay stopped")


if __name__ == "__main__":
    main()
