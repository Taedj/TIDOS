# TIDOS GPTID Relay Engine Specification (v1.0)

> **Status**: Additive engine. Defines the local Browser Relay + GPTID orchestration layer.
> Created via explicit user-commanded implementation (GPTID build task); TIDOS remains final authority.
> No OpenAI API, no API key. Transport only against the user's own authenticated ChatGPT Free session.

---

## 1. Architecture

```text
TIDOS
  ↓  (task envelope: templates/gptid_task.md)
GPTID Persona (personas/tidosgptid.md — orchestration, modes, correlation)
  ↓  (gptid_protocol task JSON)
Local Browser Relay (browser_relay/ — localhost HTTP, state machine, retry)
  ↓  AUTO: Playwright on dedicated profile  |  MANUAL: copyable SENT block + user transport
User's already-authenticated ChatGPT Free tab (chatgpt.com)
  ↓  assistant response
Browser Relay (completion detect / paste ingest → validate → correlate)
  ↓  (response envelope: templates/gptid_response.md, source: chatgpt-untrusted)
GPTID → TIDOS (evaluate against repo evidence → decide → implement → verify)
```

Component map (`browser_relay/`): `browser_manager` + `message_sender` + `response_reader` +
`completion_detector` → `chatgpt_adapter.py`; `selector_registry` → `selector_registry.json`
(versioned fallback chains, single update point for UI drift); `health_monitor` + `retry_manager` +
state machine → `relay_server.py`; protocol → `gptid_protocol.py`; control → `gptid_cli.py`.

## 2. Drivers

- **AUTO**: Playwright Chromium, profile `~/.tidos/gptid-profile` (user performs the one-time
  manual login there). Page detection = URL pattern + composer selector from the registry.
  Completion = stop-button-gone + message-count-stable + trailing-text-stable
  (`stable_polls_required: 3`, `poll 1500ms`, default timeout `180s`).
- **MANUAL** (default, always available): `SENT TO CHATGPT:` copyable block → user paste →
  `RECEIVED FROM CHATGPT:` verbatim paste → `parse_received_block` → `build_response`.
  No DOM access. Auth walls/CAPTCHAs surface as `STATUS=UNAVAILABLE (reason=auth-wall/captcha)`
  and stop the round-trip — bypass is out of scope.

Without a live page handle, AUTO must report `UNAVAILABLE`, never `READY`.

## 3. Relay endpoints (localhost only)

`GET /health` (relay + driver + state), `GET /status` (pending/history/resets),
`POST /send` (validate task → queue → return `sent_block`), `POST /poll`
(task correlation + RECEIVED validation → response), `POST /reset` (clear correlation).
Non-localhost binds are refused unless `GPTID_ALLOW_REMOTE=1` (warn + fall back to `127.0.0.1`).

## 4. State machine

`DISCONNECTED → STARTING → BROWSER_READY → CHATGPT_READY → BUSY → WAITING_RESPONSE →
CONNECTED`, with `ERROR` reachable from any state. States are observable via `/status` and the
`TIDOS GPTID status` control. History is bounded (`max_history: 5`).

## 5. Task protocol

Schemas, id shapes (`gtask-<12hex>` / `gsess-<12hex>`), and validation live in
`browser_relay/gptid_protocol.py` (mirrored by `scripts/verify_gptid.ps1`). Required task keys:
`task_id, session_id, persona=GPTID, mode∈{REVIEW,AUDIT,ARCHITECT,DEBUG,UIUX,TRADING_REVIEW},
objective, context, scope, constraints, questions, requested_output_format`.
Required response keys: `task_id, session_id, status∈{OK,UNAVAILABLE,TIMEOUT,MALFORMED,REJECTED,ERROR},
chatgpt_response, structured_findings, recommendations, uncertainties, errors, timestamp`.
Correlation (`task_matches_response`) is mandatory; `OK` + empty body is invalid.

## 6. Context bounds (`config/framework.md gptid.limits`)

`max_context_chars: 6000`, `max_files: 8`, `max_response_chars: 12000`, `max_history: 5`,
`timeout_seconds: 30`, `response_timeout_seconds: 180`, overflow `truncate-and-label`.
Kinds: `PROJECT_SUMMARY, CURRENT_TASK, RELEVANT_FILES, RELEVANT_CODE, TEST_RESULTS,
ANALYZER_RESULTS, ERROR_LOGS, RECENT_CHANGES, ARCHITECTURE_SUMMARY`.

## 7. Failure matrix

| Condition | Status | Behavior |
|---|---|---|
| browser not running / relay down | UNAVAILABLE | explicit reason, TIDOS continues |
| auth wall / CAPTCHA / rate limit | UNAVAILABLE | stop, never bypass |
| response timeout | TIMEOUT | bounded retries → report |
| malformed paste/shape | MALFORMED | reject, ask for clean re-paste |
| secret/override content | REJECTED | redact, re-issue |
| unknown task_id | ERROR (conversation mismatch) | never correlate blindly |
| selector drift | ERROR (selector failure) | update `selector_registry.json` centrally |

Silent success is forbidden: failures never produce an `OK` response.

## 8. Security

Localhost-only; dedicated or user-selected browser context; no password/token/cookie/storage
handling; redaction on build/ingest/render/log; zero secrets in `SENT`, evidence, `RECEIVED`,
synthesis, or logs; `RECEIVED` is external-untrusted (never executed, never overrides authority).

## 9. Offline fallback

GPTID is optional. Relay unreachable → `DISCONNECTED`, TIDOS proceeds without it. Nothing in
builds, tests, trading safety, broker connectivity, or core app behavior may depend on GPTID.

## 10. Verification

`scripts/verify_gptid.ps1` (structural asserts + embedded protocol-mirror checks) and
`browser_relay/tests/test_gptid_protocol.py` (18 deterministic unit tests, stdlib only).
Browser integration tests are separated: live round-trips are MANUAL and reported honestly —
no fabricated `OK` without a real ChatGPT reply.
