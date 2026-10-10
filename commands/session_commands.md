# TIDOS Session Commands & Invocation Protocols (v3.2)

This document defines standard directives and session triggers understood by AI agents operating under TIDOS v3.1 governance:

---

## 0. Help & Command Selection
- **`TIDOSHELP`**: Always outputs the complete TIDOS command list with one-line explanations so the user can choose what to run next. On trigger, present EVERY directive below grouped by section (Startup / Execution), then ask the user which one to execute. The help output is a selection menu, not a work task.

## 1. Startup & Synchronization Directives
- **`START TIDOS` / `Mount TIDOS` / `Load TIDOS`**: Step 0 Mandatory Force-Update Gate first (`scripts/update.ps1` on Windows, `scripts/update.sh` on Linux/macOS — fetches `origin/main`, auto-connects missing remotes, force-resets and force-syncs all cloned/submodule TIDOS checkouts while preserving user memory, never blocks when offline), reporting before→after version. Then Step 0.5 Google Authentication Gate (strictly blocks if unauthenticated). Executes full 9-step boot sequence, hydrates core, engines, rules, user profile, and outputs Startup Report.
- **`Upgrade TIDOS` / `Update TIDOS`**: Triggers explicit version upgrade workflow, applying queued proposals from `evolution/APPROVED.md` to system files and incrementing SemVer tag in `VERSION.md`.

---

## 2. Execution Directives
- **`TIDOS AUTH`**: Firebase authentication directive (`docs/firebase_auth.md`, project `config/firebase.md`). Mandatory at boot (Step 0.5, `TIDSTART.md`): `TIDOS AUTH session` → `auth_verify.ps1/.sh -Session` (strictly blocks boot if unauthenticated; TIDOS cannot be used without Google auth). `TIDOS AUTH google` / `TIDOS AUTH login` → opens browser window to sign in/up via Google (Gmail) and saves session to `~/.tidos`. `TIDOS AUTH status` → check auth & session state. `TIDOS AUTH logout` → disconnect and remove session. `TIDOS AUTH verify <idToken>` → verify a foreign ID token.
- **Persona Auto-Route (default)**: TIDOS scores every request against `personas/registry.md` during workflow Stage 2 and auto-activates the best-fit persona with an announced reason. Explicit `TIDOSTRADE` / `TIDOSUIUX` keywords override the router. Ties and low scores fall back to asking the user.
- **`TIDOS PERSONA FACTORY`**: `Persona Factory Engine` (`engines/persona_factory_engine.md`). Scans for stack-gap / recurring-domain signals (2+ sources); if no active persona covers them, AUTO-GENERATES a new persona spec (`personas/tidos<domain>.md`), registers its routing row in `personas/registry.md`, logs the entry in `evolution/SUGGESTIONS.md`, and auto-syncs all three to `origin/main` via `scripts/factory_sync.ps1/.sh`. OS Freeze exception (user-approved): new persona files only — never edits/deletes existing personas; staged paths are limited to the persona trio.
- **`STOP FACTORY`**: Suspends the Persona Factory for the rest of the current boot (no detection or generation); resumes next boot.
- **`TIDOSTRADE`**: Activates the Binary Options Trading Intelligence persona (`personas/tidostrade.md`) for SMARTRAD research, audit, backtest, and adaptive-strategy work. On trigger: confirm activation, recover SMARTRAD context read-only, enforce next-expiry horizon discipline and Safety Boundary, use §31 output format, propose behavior changes via §29 workflow (TIDOS final authority).
- **`TIDOSUIUX`**: Activates the Universal UI/UX, Product Design & Interface Engineering persona (`personas/tidosuiux.md`) for domain-agnostic UX/UI audit, design-system, accessibility, and responsive work. On trigger: confirm activation, recover target project context read-only without assuming the domain, use §24 output format with severity + decision-quality blocks, propose changes via §21 workflow (TIDOS final authority).
- **`TIDOS GPTID`**: Local ChatGPT browser partnership directive (`docs/gptid.md`, engine `engines/gptid_relay_engine.md`, persona `personas/tidosgptid.md`). Automatically opens Chrome to ChatGPT and acts as an engineering partner, automatically copying and pasting the chat back and forth between TIDOS and ChatGPT. Partner commands:
  - `TIDOS GPTID enhance -Objective <obj>`: Enhance code, optimize performance, propose refactorings.
  - `TIDOS GPTID correct -Objective <obj>`: Correct bugs, debug issues, provide verified fixes.
  - `TIDOS GPTID develop -Objective <obj>`: Develop features, build components, write implementations.
  - `TIDOS GPTID design -Objective <obj>`: Design architecture, UI/UX systems, schema models.
  - `TIDOS GPTID review -Objective <obj>`: Review code, inspect quality, evaluate risks.
  - `TIDOS GPTID chat`: Interactive continuous conversation between TIDOS and ChatGPT in Chrome.
  - `TIDOS GPTID start / stop / status / reset / test`: Relay lifecycle and health controls.
- **`Review Code`**: Triggers Stage 6 Self-Review evaluating target files against Gates 1–8 in `engines/quality_engine.md`.
- **`Generate Plan`**: Triggers Stage 3 Implementation Planning, creating structured atomic step breakdowns and file scope declarations.
- **`Conduct Audit`**: Triggers Master Quality Audit evaluating codebase readiness against the Definition of Done.
- **`Reflect Session`**: Triggers Stage 10 session sign-off, appending structured session reflection to `memory/PROJECT_HISTORY.md`.
