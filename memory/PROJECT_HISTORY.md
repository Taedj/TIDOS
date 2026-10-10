# Project History

## Active Projects

| Project | Stack | Start Date | Status |
|---------|-------|------------|--------|
| TIDOS v3.0 | Markdown, Git | 2026-07-28 | Active |

## Completed Projects

| Project | Stack | Duration | Key Takeaways |
|---------|-------|----------|---------------|
| - | - | - | - |

## Notes

- This file is populated automatically as projects are worked on with TIDOS.
- Each entry records the project name, detected technology stack, start date, and key architectural decisions.



## GPTID E2E Acceptance — gptid-20260922-001 (2026-09-22, CLOSED — PASS)

- **Trigger**: explicit `GPTID` invocation → `TIDOS GPTID audit` → implement-remediation → final acceptance gate (headed session PID 12728).
- **Audit finding**: claimed readiness fix NOT present (chain-only detection, split 10s/5s budgets, stale LOADING reproduced live: dead page + `tabs=0` reported LOADING while relay claimed CHATGPT_READY).
- **Remediation** (`browser_relay/chatgpt_adapter.py`, `browser_relay/relay_server.py`, `browser_relay/tests/test_gptid_readiness.py`, `scripts/verify_gptid.ps1`): shared semantic-first `composer_usable` detector; unified total budgets; liveness gates; monitor downgrade via `sync_relay_state`; detector-backed `/dom_probe`; 14 regression tests (A–L); +8 validator checks.
- **Verification**: 40/40 existing tests, 14/14 readiness tests, validator 60/60; live honest READY on authenticated composer; honest ERROR after headed-page death (downgrade log verified); headless Cloudflare wall → `AUTHENTICATION_REQUIRED`, stopped, never bypassed.
- **E2E**: exactly ONE bounded REVIEW round-trip on the verified headed session — `gtask-5270055bf900`, 1056 chars captured, correlation=True. Response held as `chatgpt-untrusted`. No retry, no second attempt.
- **Constraints**: no credentials/cookies/tokens accessed; no SMARTRAD/trading/broker/risk code touched; no E2E re-run at close-out.
- **Follow-ups tracked (not implemented)**: `gptid.ps1`/`gptid_cli.py` unassisted-start failure (double-Python spawn + 15s window too short for headed launch); PID-file lifecycle hygiene. See `evolution/SUGGESTIONS.md`.
- **Outcome**: useful=true, implementation_result=PASS (acceptance GREEN, complete).
