# GPTID Browser Relay (`browser_relay/`)

Local-only Windows bridge: `TIDOS → GPTID → Browser Relay → user's ChatGPT Free web session → GPTID → TIDOS`.

No OpenAI API. No API key. The relay never handles passwords, tokens, or cookies —
it drives (or guides) a browser the user already authenticated themselves.

## Layout

| File | Conceptual component | Notes |
|---|---|---|
| `gptid_protocol.py` | task protocol | task/response schemas, ids, validation, secret redaction, context limits. Stdlib only. |
| `relay_server.py` | health_monitor + retry_manager + state machine | stdlib `http.server`, `127.0.0.1` default, `/health` `/status` `/send` `/poll` `/reset`. |
| `chatgpt_adapter.py` | browser_manager + chatgpt_adapter + message_sender + response_reader + completion_detector | Optional Playwright driver; `MANUAL` human-bridge fallback when unavailable. |
| `selector_registry.json` | selector_registry | Central DOM selector abstraction (versioned, fallback lists). |
| `gptid_cli.py` | UI/control CLI | `start/stop/status/test/ask/review/audit` — used by `scripts/gptid.ps1`. |
| `tests/test_gptid_protocol.py` | deterministic unit tests | stdlib `unittest`, no browser, no network. |

## Modes

- `AUTO` — Playwright-controlled Chromium on a dedicated local profile
  (`~/.tidos/gptid-profile`). The user signs into ChatGPT once, manually, in that
  profile. The relay reuses it afterwards. Unavailable unless `playwright` is installed.
- `MANUAL` (default) — human bridge, same philosophy as the CHORA channel:
  TIDOS emits a copyable `SENT TO CHATGPT:` block, the user pastes it into their
  ChatGPT Free tab, pastes the reply back as `RECEIVED FROM CHATGPT:`. No DOM scraping.

## Security

- Localhost bind by default (`relay_host: 127.0.0.1`). No public exposure.
- Never logs or transmits: cookies, passwords, tokens, `api_key=`, SSIDs, broker secrets.
- `gptid_protocol.redact_secrets()` runs on every task build, every response ingest,
  and every log line. Violations → `REJECTED` + re-issue, never forwarded.
- CAPTCHA/auth bypass is out of scope: if ChatGPT shows a login wall or CAPTCHA,
  the relay reports `STATUS=UNAVAILABLE (reason=auth-wall/captcha)` and stops.

## Quick start (Windows PowerShell)

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 start
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 test
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/gptid.ps1 stop
```

## State machine

`DISCONNECTED → STARTING → BROWSER_READY → CHATGPT_READY → BUSY → WAITING_RESPONSE → CONNECTED → (ERROR)`.
`MANUAL` mode reports `CHATGPT_READY` only after the user confirms the ChatGPT tab is open;
it never fabricates page detection.
