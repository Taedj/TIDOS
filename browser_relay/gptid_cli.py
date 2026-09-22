"""GPTID CLI: lifecycle + task packaging over the local relay (stdlib only).

Usage:
  python gptid_cli.py status [--port N]
  python gptid_cli.py start [--port N] [--driver manual|auto]
  python gptid_cli.py stop
  python gptid_cli.py test [--port N]
  python gptid_cli.py ask --objective "..." --mode REVIEW [--port N]
  python gptid_cli.py reset [--port N]
  python gptid_cli.py review-auto --change-json '{"change_id":"...","kind":"..."}'
    [--questions "q1;q2"] [--context "..."] [--dry-run] [--ledger PATH]
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gptid_protocol import build_context_package, build_task, redact_secrets, validate_task  # noqa: E402
from gptid_review import (  # noqa: E402
    ReviewLedger, build_review_task, decide_review, readiness_ok,
    untrusted_envelope, verification_checklist,
)

PID_FILE = os.path.join(os.path.expanduser("~"), ".tidos", "gptid-relay.pid")

# Persistent relay log. The relay child MUST NOT inherit an unread PIPE from
# the CLI: once the CLI exits after a successful start, the pipe's read end
# disappears and every later relay stderr/stdout write raises broken-pipe —
# killing HTTP responses inside log_request (which runs before any response
# byte). A real file survives CLI exit, so serving can never wedge this way,
# and diagnostics persist across launches (append, never truncate).
RELAY_LOG = os.path.join(os.path.expanduser("~"), ".tidos", "gptid-relay.log")


def _relay_log_handle():
    """Open the persistent relay log (append). DEVNULL only as last resort."""
    try:
        parent = os.path.dirname(RELAY_LOG)
        if parent:
            os.makedirs(parent, exist_ok=True)
        return open(RELAY_LOG, "a", buffering=1)
    except Exception:
        try:
            return open(os.devnull, "w")
        except Exception:
            return None


def _relay_log_tail(chars=1500):
    try:
        with open(RELAY_LOG, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            size = fh.tell()
            fh.seek(max(0, size - 8192))
            return fh.read().decode("utf-8", "replace")[-chars:]
    except Exception:
        return ""

# How long an unassisted start waits for /health before giving up.
# Headed Chromium launch + navigation + classification needs 45-75s, so the
# old fixed 15s window failed healthy startups. Bounded and configurable.
DEFAULT_STARTUP_TIMEOUT = 120
STARTUP_POLL_SECONDS = 2


def _read_pidfile():
    """Return the recorded PID as int, or None when missing/unparseable."""
    try:
        with open(PID_FILE, "r", encoding="utf-8") as fh:
            return int(fh.read().strip().split()[0])
    except Exception:
        return None


def _remove_pidfile_if(pid):
    """Remove the PID file only when it still points at `pid`. Never blind."""
    try:
        with open(PID_FILE, "r", encoding="utf-8") as fh:
            current = int(fh.read().strip().split()[0])
    except Exception:
        return False
    if current != pid:
        return False
    try:
        os.remove(PID_FILE)
        return True
    except Exception:
        return False


def _pid_alive(pid):
    """True when a process with `pid` exists (identity NOT implied)."""
    try:
        if os.name == "nt":
            import ctypes
            handle = ctypes.windll.kernel32.OpenProcess(0x00100000, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def _proc_cmdline(pid):
    """Best-effort command line for `pid` (stdlib only). None when unknown."""
    try:
        if os.name == "nt":
            for cmd in (
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Process -Filter \"ProcessId=%d\" "
                 % pid + ").CommandLine"],
                ["wmic", "process", "where", "ProcessId=%d" % pid,
                 "get", "CommandLine", "/format:value"],
            ):
                try:
                    out = subprocess.run(cmd, capture_output=True, text=True,
                                         timeout=15)
                    txt = (out.stdout or "").strip()
                    if txt:
                        return txt
                except Exception:
                    continue
            return None
        with open("/proc/%d/cmdline" % pid, "rb") as fh:
            return fh.read().replace(b"\0", b" ").decode("utf-8", "replace")
    except Exception:
        return None


def _is_relay_process(pid):
    """True only when `pid` provably runs relay_server.py. Unknown => False."""
    try:
        cmd = _proc_cmdline(pid)
    except Exception:
        return False
    return bool(cmd) and "relay_server" in cmd


def _terminate(pid):
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                           capture_output=True)
        else:
            os.kill(pid, 15)
    except Exception:
        pass


def _url(port, path):
    return "http://127.0.0.1:%d%s" % (port, path)


def _get(port, path, timeout=5):
    try:
        with urllib.request.urlopen(_url(port, path), timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return False, str(e)


def _post(port, path, payload, timeout=10):
    try:
        req = urllib.request.Request(_url(port, path),
                                     data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return False, str(e)


def cmd_status(port):
    ok, data = _get(port, "/status")
    if not ok:
        print("[GPTID] status=DISCONNECTED (relay unreachable: %s)" % redact_secrets(data))
        return 1
    mode = str(data.get("driver", "?")).upper()
    print("GPTID MODE: %s" % mode)
    print("BROWSER: %s (%s)" % (data.get("browser", "?"), data.get("browser_engine", "?")))
    print("CHATGPT: %s" % data.get("chatgpt", "?"))
    print("RELAY: %s (pending=%s queued=%s resets=%s)" % (
        data.get("state"), data.get("pending"), data.get("queued", 0),
        data.get("conversation_resets")))
    return 0


def cmd_start(port, driver, headed=False, response_timeout=180, browser_name="chromium",
              startup_timeout=DEFAULT_STARTUP_TIMEOUT):
    ok, _ = _get(port, "/health", timeout=2)
    if ok:
        print("[GPTID] relay already running on port %d" % port)
        return 0
    # A PID file pointing at a dead or non-relay process must not block a
    # fresh launch — but a live relay process is never disturbed here.
    if not _reap_stale_pidfile(port):
        return 1
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    # Single spawn: argv[0] is the interpreter EXACTLY once, followed by the
    # relay script and its flags. (The old code prepended a second
    # [sys.executable, "-u"], so Python received the interpreter binary as
    # the "script" and the child always died instantly.)
    cmd = [sys.executable, "-u", os.path.join(HERE, "relay_server.py"),
           "--port", str(port), "--driver", driver, "--browser", browser_name,
           "--response-timeout", str(response_timeout)]
    if headed:
        cmd.append("--headed")
    logfh = None
    try:
        logfh = _relay_log_handle()
        proc = subprocess.Popen(cmd,
                                stdout=(logfh if logfh is not None
                                        else subprocess.DEVNULL),
                                stderr=subprocess.STDOUT,
                                text=True)
    except Exception as e:
        print("[GPTID] STATUS=UNAVAILABLE (reason=spawn failed: %s)"
              % redact_secrets(str(e))[:160])
        return 1
    finally:
        try:
            if logfh is not None:
                logfh.close()  # child keeps its own dup'd OS handle
        except Exception:
            pass
    with open(PID_FILE, "w") as fh:
        fh.write(str(proc.pid))
    # Bounded readiness polling (not a fixed 15s assumption): the relay only
    # serves /health after its own handshake, which needs 45-75s headed.
    deadline = time.time() + max(1, int(startup_timeout))
    while time.time() < deadline:
        if proc.poll() is not None:
            tail = redact_secrets(_relay_log_tail())[-1200:]
            print("[GPTID] STATUS=UNAVAILABLE (reason=relay exited during "
                  "startup)%s" % (" | %s" % tail if tail else ""))
            _remove_pidfile_if(proc.pid)
            return 1
        ok, _ = _get(port, "/health", timeout=2)
        if ok:
            print("[GPTID] Starting")
            print("[GPTID] Browser relay started on 127.0.0.1:%d (driver=%s)" % (port, driver))
            return 0
        time.sleep(STARTUP_POLL_SECONDS)
    print("[GPTID] STATUS=UNAVAILABLE (reason=relay did not become healthy "
          "within %ds)" % int(startup_timeout))
    # Cleanup covers ONLY the child owned by this launch (identity re-checked
    # so an unrelated PID-reusing process can never be harmed).
    _stop_owned(proc)
    _remove_pidfile_if(proc.pid)
    return 1


def _reap_stale_pidfile(port):
    """Pre-launch PID hygiene. Returns True when launching may proceed."""
    pid = _read_pidfile()
    if pid is None:
        return True
    if _pid_alive(pid) and _is_relay_process(pid):
        print("[GPTID] relay process alive (PID %d) but not serving port %d; "
              "not starting a second relay" % (pid, port))
        return False
    if _pid_alive(pid):
        print("[GPTID] stale PID file (PID %d is not a relay process); "
              "clearing it, launch proceeds" % pid)
    else:
        print("[GPTID] stale PID file (PID %d not running); clearing it, "
              "launch proceeds" % pid)
    _remove_pidfile_if(pid)
    return True


def _stop_owned(proc):
    """Terminate a child spawned by this launch after identity re-check."""
    try:
        pid = proc.pid
    except Exception:
        return
    if proc.poll() is not None:
        return
    if not _is_relay_process(pid):
        print("[GPTID] owned child PID %d no longer identifies as the relay; "
              "not terminating (possible PID reuse)" % pid)
        return
    _terminate(pid)
    for _ in range(5):
        time.sleep(1)
        if proc.poll() is not None:
            break


def cmd_stop(port=8765):
    pid = _read_pidfile()
    if pid is None:
        ok, _ = _get(port, "/health", timeout=2)
        if ok:
            print("[GPTID] relay live on port %d with no PID record; "
                  "refusing blind kill (manage it via OS tools)" % port)
            return 1
        print("[GPTID] relay not running (no PID record)")
        return 0
    if not _pid_alive(pid):
        _remove_pidfile_if(pid)
        print("[GPTID] relay not running (stale PID %d cleared)" % pid)
        return 0
    if _is_relay_process(pid):
        _terminate(pid)
        print("[GPTID] relay stopped (PID %d)" % pid)
        _remove_pidfile_if(pid)
        return 0
    # Alive but provably NOT the relay: possible PID reuse. Never kill it.
    ok, _ = _get(port, "/health", timeout=2)
    _remove_pidfile_if(pid)
    if ok:
        print("[GPTID] REFUSED: PID %d is not a relay process and a relay is "
              "live on port %d (possible PID reuse); nothing terminated, "
              "stale PID record cleared" % (pid, port))
        return 1
    print("[GPTID] stale PID %d belongs to a non-relay process; not "
          "terminated, PID record cleared" % pid)
    return 0


def cmd_test(port, response_timeout=240):
    ok, data = _get(port, "/health", timeout=5)
    if not ok:
        print("[GPTID] STATUS=UNAVAILABLE (reason=relay unreachable; start it first)")
        return 1
    task = build_task(objective="Review this short test message and return three "
                                "software-engineering observations.",
                      mode="REVIEW", context="E2E acceptance probe (harmless).",
                      questions=["Observation 1?", "Observation 2?", "Observation 3?"])
    errs = validate_task(task)
    if errs:
        print("[GPTID] protocol self-check FAILED: %s" % errs)
        return 1
    ok, sent = _post(port, "/send", task, timeout=response_timeout)
    if not ok:
        print("[GPTID] STATUS=UNAVAILABLE (reason=send failed: %s)" % redact_secrets(sent))
        return 1
    print("[GPTID] Task sent: %s" % task["task_id"])
    if sent.get("queued"):
        print("[GPTID] queued (position %s): waiting for ChatGPT READY — "
              "sign in to ChatGPT in the GPTID browser window; "
              "the queued task runs automatically, no restart." % sent.get("position"))
        deadline = time.time() + response_timeout
        while time.time() < deadline:
            time.sleep(10)
            ok, polled = _post(port, "/poll", {"task_id": task["task_id"]}, timeout=30)
            if not ok:
                print("[GPTID] STATUS=UNAVAILABLE (reason=poll failed: %s)"
                      % redact_secrets(polled))
                return 1
            if polled.get("status") == "QUEUED":
                print("[GPTID] still queued (position %s), waiting..."
                      % polled.get("position"))
                continue
            if polled.get("ok") and polled.get("status") == "OK":
                corr = (polled.get("task_id") == task["task_id"]
                        and polled.get("session_id") == task["session_id"])
                print("[GPTID] Response received (AUTO, %d chars, correlation=%s)"
                      % (len(polled.get("chatgpt_response", "")), corr))
                print("[GPTID] Task completed: %s" % task["task_id"])
                print(redact_secrets(polled.get("chatgpt_response", ""))[:2000])
                return 0 if corr else 1
            print("[GPTID] STATUS=%s (reason=%s)"
                  % (polled.get("status"), redact_secrets(polled.get("reason", ""))))
            return 1
        print("[GPTID] still queued after %ds — complete the ChatGPT login, then re-run test."
              % response_timeout)
        return 1
    if sent.get("mode") == "auto" and sent.get("auto_response"):
        resp = sent["auto_response"]
        corr = (resp.get("task_id") == task["task_id"]
                and resp.get("session_id") == task["session_id"])
        print("[GPTID] Response received (AUTO, %d chars, correlation=%s)"
              % (len(resp.get("chatgpt_response", "")), corr))
        print("[GPTID] Task completed: %s" % task["task_id"])
        print(redact_secrets(resp.get("chatgpt_response", ""))[:2000])
        return 0 if (corr and resp.get("status") == "OK") else 1
    if not sent.get("ok", True):
        print("[GPTID] STATUS=%s (reason=%s)" % (sent.get("status"), redact_secrets(sent.get("reason", ""))))
        if sent.get("status") == "UNAVAILABLE":
            print("[GPTID] CHATGPT: AUTHENTICATION_REQUIRED — sign in manually, then re-run test.")
        return 1
    print("[GPTID] Waiting for response (MANUAL: paste the SENT block into ChatGPT, "
          "then POST the reply to /poll)")
    print(redact_secrets(sent.get("sent_block", "")))
    print("[GPTID] NOTE: live ChatGPT round-trip needs manual user interaction — "
          "no success fabricated.")
    return 0


def cmd_ask(port, mode, objective, context_parts):
    context, included, dropped = build_context_package(context_parts or {})
    task = build_task(objective=objective, mode=mode, context=context)
    errs = validate_task(task)
    if errs:
        print("[GPTID] task invalid: %s" % errs)
        return 1
    ok, sent = _post(port, "/send", task)
    if not ok:
        print("[GPTID] STATUS=UNAVAILABLE (reason=%s)" % redact_secrets(sent))
        return 1
    print("[GPTID] Task sent: %s (session %s, context: %s)" % (
        task["task_id"], task["session_id"], ",".join(included) or "none"))
    print(redact_secrets(sent.get("sent_block", "")))
    return 0


def cmd_review_auto(port, change_json, questions_text, context_text,
                    dry_run=False, ledger_path="", response_timeout=120):
    """TIDOS auto-REVIEW: decide -> readiness gate -> at most ONE send.

    Never blocks TIDOS on GPTID trouble (exit 0 + recorded SKIP) unless the
    change declares user_required (hard requirement -> exit 2 when the
    review cannot be obtained). Exactly one /send attempt: no retry loop.
    """
    try:
        change = json.loads(change_json or "{}")
        if not isinstance(change, dict):
            raise ValueError("change descriptor must be a JSON object")
    except Exception as e:
        print("[GPTID] review-auto: invalid --change-json: %s" % redact_secrets(str(e)))
        return 2
    change_id = str(change.get("change_id", "") or "")
    questions = [q.strip() for q in (questions_text or "").split(";") if q.strip()]
    ledger = ReviewLedger(path=(ledger_path or None))

    invoke, _reason, log_line = decide_review(change)
    print("[GPTID] %s" % log_line)
    if not invoke:
        if change_id:
            ledger.record(change_id, {"status": "SKIPPED", "reason": _reason})
        return 0
    if change_id and ledger.already_reviewed(change_id):
        print("[GPTID] GPTID REVIEW: SKIPPED — already reviewed (change_id=%s, "
              "unchanged state gets no second review)" % redact_secrets(change_id))
        return 0
    if dry_run:
        return 0

    ok, health = _get(port, "/health", timeout=5)
    if not ok:
        msg = "relay unreachable"
        print("[GPTID] GPTID REVIEW: SKIPPED — GPTID unavailable (%s); "
              "TIDOS continues normally" % redact_secrets(str(health))[:120])
        if change_id:
            ledger.record(change_id, {"status": "SKIPPED", "reason": msg})
        return 2 if change.get("user_required") else 0
    ready, why = readiness_ok(health)
    print("[GPTID] %s" % ("GPTID REVIEW: READY" if ready
                          else "GPTID REVIEW: SKIPPED — GPTID unavailable (%s)" % why))
    if not ready:
        if change_id:
            ledger.record(change_id, {"status": "SKIPPED", "reason": why})
        return 2 if change.get("user_required") else 0

    parts = {"CURRENT_TASK": context_text} if context_text else {}
    try:
        task = build_review_task(change, context_parts=parts, questions=questions)
    except Exception as e:
        print("[GPTID] review task invalid: %s" % redact_secrets(str(e)))
        return 2
    print("[GPTID] GPTID REVIEW: SUBMITTED (task %s)" % task["task_id"])
    sent_ok, sent = _post(port, "/send", task, timeout=response_timeout)
    if not sent_ok:
        print("[GPTID] GPTID REVIEW: SKIPPED — send failed (%s); no retry"
              % redact_secrets(str(sent))[:160])
        if change_id:
            ledger.record(change_id, {"status": "SEND_FAILED",
                                      "task_id": task["task_id"]})
        return 2 if change.get("user_required") else 0
    if isinstance(sent, dict) and sent.get("mode") == "auto" and sent.get("auto_response"):
        resp = sent["auto_response"]
        correlated = (resp.get("task_id") == task["task_id"]
                      and resp.get("session_id") == task["session_id"])
        env = untrusted_envelope(task,
                                 chatgpt_response=resp.get("chatgpt_response", ""),
                                 status="OK" if correlated else "MALFORMED",
                                 failure_reason="" if correlated else "correlation mismatch")
        print("[GPTID] GPTID REVIEW: CAPTURED (%d chars, correlation=%s)"
              % (len(env["chatgpt_response"]), correlated))
        print("[GPTID] GPTID REVIEW: UNTRUSTED RESULT (source=%s, task=%s, "
              "session=%s, %s)" % (env["source"], env["task_id"],
                                   env["session_id"], env["timestamp"]))
        for line in verification_checklist()[1:]:
            print("[GPTID] verify: %s" % line)
        if change_id:
            ledger.record(change_id, {"status": env["status"],
                                      "task_id": task["task_id"],
                                      "session_id": task["session_id"]})
        return 0 if correlated else 1
    # MANUAL bridge (or queued): hand the SENT block to the user, record, stop.
    # No retry loop — the user completes the round-trip out of band.
    print(redact_secrets((sent or {}).get("sent_block", "")))
    print("[GPTID] GPTID REVIEW: SUBMITTED (MANUAL bridge — paste into ChatGPT, "
          "poll later; no auto-retry)")
    if change_id:
        ledger.record(change_id, {"status": "SUBMITTED",
                                  "task_id": task["task_id"],
                                  "session_id": task["session_id"]})
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gptid")
    ap.add_argument("command", choices=("status", "start", "stop", "test", "ask",
                                        "review", "audit", "reset", "review-auto"))
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--driver", default="auto", choices=("manual", "auto"))
    ap.add_argument("--browser", default="chromium",
                    choices=("firefox", "firefox-nightly", "chromium"))
    ap.add_argument("--headed", action="store_true",
                    help="AUTO: show the browser window (first manual login)")
    ap.add_argument("--response-timeout", type=int, default=180)
    ap.add_argument("--mode", default="REVIEW")
    ap.add_argument("--objective", default="")
    ap.add_argument("--context", default="")
    ap.add_argument("--change-json", default="{}")
    ap.add_argument("--questions", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ledger", default="")
    ap.add_argument("--startup-timeout", type=int, default=DEFAULT_STARTUP_TIMEOUT)
    args = ap.parse_args(argv)
    if args.command == "status":
        return cmd_status(args.port)
    if args.command == "start":
        return cmd_start(args.port, args.driver, headed=args.headed,
                         response_timeout=args.response_timeout,
                         browser_name=args.browser,
                         startup_timeout=args.startup_timeout)
    if args.command == "stop":
        return cmd_stop(args.port)
    if args.command == "test":
        return cmd_test(args.port, response_timeout=args.response_timeout + 60)
    if args.command == "reset":
        ok, data = _post(args.port, "/reset", {})
        print("[GPTID] reset: %s" % redact_secrets(json.dumps(data)))
        return 0 if ok else 1
    if args.command in ("ask", "review", "audit"):
        mode = {"ask": args.mode, "review": "REVIEW", "audit": "AUDIT"}[args.command]
        parts = {"CURRENT_TASK": args.context} if args.context else {}
        return cmd_ask(args.port, mode, args.objective or "(no objective given)", parts)
    if args.command == "review-auto":
        return cmd_review_auto(args.port, args.change_json, args.questions,
                               args.context, dry_run=args.dry_run,
                               ledger_path=args.ledger,
                               response_timeout=args.response_timeout + 60)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
