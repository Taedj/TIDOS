# TIDOS Session Commands & Invocation Protocols (v3.0)

This document defines standard directives and session triggers understood by AI agents operating under TIDOS v3.0 governance:

---

## 1. Startup & Synchronization Directives
- **`START TIDOS` / `Mount TIDOS` / `Load TIDOS`**: Triggers automatic TIDOS sync from GitHub (`cd .tidos && git pull`), then executes the full 9-step boot sequence, hydrates core, engines, rules, user profile, and outputs Startup Report.
- **`Upgrade TIDOS` / `Update TIDOS`**: Triggers explicit version upgrade workflow, applying queued proposals from `evolution/APPROVED.md` to system files and incrementing SemVer tag in `VERSION.md`.

---

## 2. Execution Directives
- **`Review Code`**: Triggers Stage 6 Self-Review evaluating target files against Gates 1–8 in `engines/quality_engine.md`.
- **`Generate Plan`**: Triggers Stage 3 Implementation Planning, creating structured atomic step breakdowns and file scope declarations.
- **`Conduct Audit`**: Triggers Master Quality Audit evaluating codebase readiness against the Definition of Done.
- **`Reflect Session`**: Triggers Stage 10 session sign-off, appending structured session reflection to `memory/PROJECT_HISTORY.md`.
