# Lessons Learned

## TIDOS v3.0 Multi-Project Ecosystem

- **Issue**: Hardcoded repository URL scattered across documentation
- **Root Cause**: No centralized configuration file
- **Resolution**: Added `config/framework.md` as single source of truth for repository metadata
- **Lesson**: Centralize configuration early to avoid update cascading across dozens of files
- **Applied**: TIDOS v3.0 config-driven architecture

## TIDOS v2.0 Centralized Refactoring

- **Issue**: TIDOS previously lived inside each project as `.tidos/`, leading to fragmentation
- **Root Cause**: No centralized version control or update mechanism
- **Resolution**: Refactored to standalone Git repository with consumption protocols
- **Lesson**: Platform frameworks must be versioned and centrally maintained to prevent drift
- **Applied**: TIDOS v2.0 centralized architecture with Git submodule/symlink/injection support

## General

| Date | Lesson | Context | Validation |
|------|--------|---------|------------|
| - | - | - | - |

## GPTID readiness remediation + E2E acceptance (2026-09-22, VERIFIED)

- **Issue**: GPTID readiness detection was registry-selector-chain-only with per-selector timeouts, and the relay cached `CHATGPT_READY` independently of adapter truth — a dead page (tabs=0) still reported LOADING/READY (false persistent LOADING).
- **Resolution**: one shared `find_usable_composer` detector (semantic-first: `textarea` → `contenteditable` → `role=textbox`, then registry fallback; usable = visible + enabled + editable, never `disabled`/`aria-disabled`); one total wall-clock budget per operation (`READINESS 10s` / `MONITOR 5s`, no per-selector multiplication); liveness gates (page answers, tab exists) before READY; monitor downgrade via canonical `sync_relay_state` (adapter truth wins; dead → ERROR, LOADING → never cached READY); `/dom_probe` reports the same detector verdict.
- **Evidence**: 40/40 existing unit tests, 14/14 new readiness tests (A–L), validator 60/60; live: honest READY on authenticated composer, honest ERROR within ~1 min of headed-page death (twice), `AUTHENTICATION_REQUIRED` (never bypassed) on Cloudflare-challenged headless; ONE bounded REVIEW E2E passed (`gtask-5270055bf900`, 1056 chars, correlation=True), response treated as `chatgpt-untrusted`; no retry, no second E2E.
- **Lesson**: readiness composites must DERIVE from a single detector/liveness source — independently cached READY states always diverge; budgets must cap the whole operation, not each candidate.
- **Constraints honored**: no credentials/cookies/tokens accessed; no SMARTRAD/trading/broker/risk/CHORA code touched (repo-local: only `browser_relay/`, `scripts/verify_gptid.ps1`, memory/evolution written).
