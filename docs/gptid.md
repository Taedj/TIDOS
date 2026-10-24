# GPTID Operator Guide (v1.0): local ChatGPT Free browser relay & partner system

> **Status: EXPERIMENTAL — OFF by default (v4.1).**
> - It drives the ChatGPT **web UI** with browser automation. OpenAI's Terms of Use restrict automated access to
>   their services; using GPTID may breach them and can get the account limited. Use it at your own risk.
> - It is fragile by nature (DOM changes, Cloudflare checks) and sends project context to a third party.
> - It only runs when the `gptid` switch is ON in `/TIDOSZIT` → Security (`scripts/gptid.*` refuse otherwise;
>   `status`/`stop` always work).
> - Preferred alternative for a second opinion: a second model through its official API or CLI (see the plan,
>   Phase 7 "second-opinion reviewer"), which is supported, stable and auditable.

GPTID connects TIDOS to your own ChatGPT Free web session through a **local-only**
relay using Google Chrome. No OpenAI API, no API key. You stay logged in; the relay never sees your credentials.
When invoked, GPTID automatically opens Google Chrome to ChatGPT and acts as an engineering partner
on specific user commands (enhancing, correcting, developing, designing, reviewing, chatting), automatically copying
and pasting exchanges between TIDOS and ChatGPT.

## 1. Lifecycle

```text
TIDOS GPTID command (enhance / correct / develop / design / review / chat)
  → Auto-ensures Relay + Headed Chrome running on dedicated profile
  → Formats partner prompt [TIDOS -> CHATGPT] with explicit engineering mandate
  → Sends to chatgpt.com composer & submits automatically
  → Polls and captures response until generation is complete
  → Ingests [CHATGPT -> TIDOS] into TIDOS console / protocol
  → TIDOS validates → TIDOS evaluates → TIDOS decides
```

Statuses: `DISCONNECTED | STARTING | BROWSER_READY | CHATGPT_READY | BUSY |
WAITING_RESPONSE | CONNECTED | ERROR` (`TIDOS GPTID status`).

## 2. Commands (PowerShell shown; `.sh` equivalents exist)

```powershell
# Interactive Continuous Partnership Chat (auto opens Chrome & streams chat back-and-forth)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 chat

# Partner Commands (auto opens Chrome, delivers prompt, captures response)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 enhance -Objective "Enhance login UI with glassmorphism"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 correct -Objective "Correct regex logic in auth validator"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 develop -Objective "Develop token refresh background worker"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 design -Objective "Design resilient state machine for relay"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 review -Objective "Review auth flow"
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 audit -Objective "Audit error handling in Y"

# Relay Lifecycle Controls
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 start
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 test
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 reset
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 stop
```

`TIDOS GPTID connect|reconnect|new-session` map to `start` / `stop+start` / `reset`.

## 3. MANUAL round-trip (default — works with ChatGPT Free today)

1. `TIDOS GPTID start` → relay on `127.0.0.1:8765`, `BROWSER_READY`.
2. `TIDOS GPTID ask -Objective "..." -Mode REVIEW` → prints a `SENT TO CHATGPT:` block.
3. Copy that block into your ChatGPT Free tab (use one dedicated GPTID conversation).
4. Copy ChatGPT's reply, then submit it as the `RECEIVED` body for the printed `task_id`
   (via the relay `/poll` endpoint or the next `TIDOS GPTID` turn).
5. TIDOS validates correlation + shape, marks findings `source: chatgpt-untrusted`,
   evaluates against repo evidence, and decides. Only TIDOS implements.

## 4. AUTO mode (Playwright, Google Chrome dedicated profile)

Runtime: `playwright` 1.63.0 + installed Google Chrome (default engine `channel="chrome"`,
fallback to Playwright Chromium; alternatives: Mozilla Firefox via `--browser firefox`).
Driver: `browser_relay/chatgpt_adapter.py`
(`AutoDriver`: persistent context on `~/.tidos/gptid-profile`, registry-driven selectors,
stop-button + count + tail stability completion, bounded retries, graceful shutdown).

First run (one-time manual login — the user authenticates, GPTID never handles credentials):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 start -Headed
# A GPTID Chromium window opens on the dedicated profile.
# Sign in to ChatGPT Free in THAT window, once.
# The relay keeps the browser open, exposes AUTH_REQUIRED, and the auth
# monitor flips AUTH_REQUIRED → CHATGPT_READY automatically (no restart).
# Tasks sent meanwhile are QUEUED and auto-drain once READY.
# Afterwards headless works: scripts/gptid.ps1 start  (AUTO is the default)
```

Headless thereafter (`start -Driver auto`). If a login wall or CAPTCHA appears, the relay
reports `STATUS=UNAVAILABLE (reason=USER_ACTION_REQUIRED)` and pauses — bypass is out of
scope. Diagnostics (`TIDOS GPTID status`):

```text
GPTID MODE: AUTO
BROWSER: READY
CHATGPT: READY
RELAY: CONNECTED
```

or when authentication is needed:

```text
GPTID MODE: AUTO
BROWSER: READY
CHATGPT: AUTHENTICATION_REQUIRED
```

AUTO failure never silently switches to MANUAL (`auto_fallback_to_manual: false`); MANUAL
remains available via `start` (default driver) as a fully working fallback.

## 5. Security rules

- ChatGPT login/CAPTCHA walls stop the round-trip (`UNAVAILABLE`) — never bypassed.
- Never paste secrets, `.env` contents, tokens, SSIDs, or broker keys into ChatGPT.
  Redaction rejects violations; re-issue clean.
- Relay binds localhost only. Logs carry ids and states — never cookies, tokens, or storage.
- Prefer the dedicated GPTID conversation; `TIDOS GPTID reset` clears correlation anytime.

## 6. SMARTRAD boundary

GPTID may review SMARTRAD code/architecture/UI/telemetry/risk but never changes it and never
issues trading instructions. Every recommendation flows through TIDOS evaluation and the
standard verify gates before anything is implemented.

## 7. Automatic REVIEW policy (TIDOS-side, optional)

`browser_relay/gptid_review.py` lets TIDOS decide per task whether an external REVIEW is
materially useful — GPTID stays a transport; TIDOS stays the sole decision/implementation
authority and ChatGPT output stays `source: chatgpt-untrusted`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 review-auto `
  -ChangeJson '{"change_id":"<id>","kind":"architecture","summary":"...","scope":["..."],"lines_changed":120}' `
  -Questions "Edge cases?;Omissions?" -Context "..." [-DryRun] [-Ledger PATH]
# equivalent direct CLI call:
# python browser_relay/gptid_cli.py review-auto --change-json '{...}' [--dry-run]
```

- **Decide** (`decide_review`): invoke for significant kinds (architecture, cross-cutting,
  large ≥200-line change, audit-requested, unresolved debug, multi-approach, material
  uncertainty, UI consistency, closeout review); skip trivial/format/docs/one-line/routine
  work and repeat requests for unchanged state.
- **Gate** (`readiness_ok` on relay `/health`): browser + ChatGPT + page_state READY,
  tabs > 0, no contradiction. Unavailable → recorded SKIP, TIDOS continues (exit 2 only
  when the change declares `user_required`, i.e. review is a hard requirement).
- **Bound**: at most ONE send per `change_id` (file ledger `~/.tidos/gptid-reviews.json`);
  exactly one `/send` attempt per run — no retry, no review loops.
- **Result**: envelope with `source: chatgpt-untrusted` + ids + timestamp; TIDOS marks each
  finding VERIFIED (with repo evidence) / REJECTED / PARTIALLY VERIFIED. Nothing in this
  layer writes workspace files — there is deliberately no apply path.
- **Logs**: `GPTID REVIEW: SKIPPED — … | REQUESTED — … | READY | SUBMITTED | CAPTURED |
  UNTRUSTED RESULT`. Never credentials/cookies/tokens.
