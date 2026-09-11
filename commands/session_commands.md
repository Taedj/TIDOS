# TIDOS Session Commands & Invocation Protocols (v3.2)

This document defines standard directives and session triggers understood by AI agents operating under TIDOS v3.1 governance:

---

## 1. Startup & Synchronization Directives
- **`START TIDOS` / `Mount TIDOS` / `Load TIDOS`**: Triggers automatic TIDOS sync from GitHub (`cd .tidos && git pull`), then executes the full 9-step boot sequence, hydrates core, engines, rules, user profile, and outputs Startup Report.
- **`Upgrade TIDOS` / `Update TIDOS`**: Triggers explicit version upgrade workflow, applying queued proposals from `evolution/APPROVED.md` to system files and incrementing SemVer tag in `VERSION.md`.

---

## 2. Execution Directives
- **`TIDOSCHORA`**: Manual external-advisor consultation — Chat-Channel Mode (v3.1 default). Bypasses the CHORA Trigger Engine matrix (`manual_request == true -> CHORA`), then: asks partner count (1..N) → asks each partner name (e.g. `CHATGPT`) + perspective → locks narrow scope → opens one copyable chat channel per partner (`SENT TO <NAME>:` / `RECEIVED FROM <NAME>:`). Turn-0 contract enforces single-md-box replies starting with `<NAME>:`; every `RECEIVED` is `external-untrusted`, verified in authority order before synthesis/decision. Follows `engines/chora_trigger_engine.md` Sections 7-8 for scope, advisor perspectives, explanation, memory, and persistence. Sub-commands: `start` (create session from trigger handoff), `scope` (lock question/constraints/evidence), `status` (report state/round/claims/channels), `close` (record decision/ADR/outcome). Session rules live in `engines/chora_session_engine.md`; operator steps in `docs/chora_session.md`. Legacy `templates/chora_response.md` envelope retained as deprecated intake behind the channel.
- **`Review Code`**: Triggers Stage 6 Self-Review evaluating target files against Gates 1–8 in `engines/quality_engine.md`.
- **`Generate Plan`**: Triggers Stage 3 Implementation Planning, creating structured atomic step breakdowns and file scope declarations.
- **`Conduct Audit`**: Triggers Master Quality Audit evaluating codebase readiness against the Definition of Done.
- **`Reflect Session`**: Triggers Stage 10 session sign-off, appending structured session reflection to `memory/PROJECT_HISTORY.md`.
