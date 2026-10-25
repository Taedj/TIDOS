# Evolution Suggestions

This file tracks non-invasive improvement proposals for TIDOS. All suggestions are reviewed before any protected system files are modified.

## Suggestion Template

```markdown
### Title: [Short descriptive name]

- **Reason**: Why this change is needed
- **Benefits**: What improvements it brings
- **Risks**: Potential downsides or breaking changes
- **Priority**: Critical / High / Medium / Low
- **Affected Modules**: Which directories/files would be affected
- **Recommended Version**: Target SemVer version
```

## Submitted Suggestions


---

### Suggestion Format Example

### Title: Add MCP Server Support

- **Reason**: Many AI agents support MCP protocol for tool-based context hydration
- **Benefits**: Direct OS context injection without manual file reads
- **Risks**: Requires new dependency and maintenance
- **Priority**: Medium
- **Affected Modules**: `engines/`, `docs/tools/`, `scripts/`
- **Recommended Version**: 2.1.0

---

### Title: TIDOSTRADE Persona (Binary Options Trading Intelligence)

- **Date**: 2026-09-13
- **Requestor**: User (explicit `TIDOSTRADE` invocation request)
- **Reason**: SMARTRAD binary-options system needs a dedicated evidence-driven quant/research/audit persona inside TIDOS, invocable via `TIDOSTRADE` keyword.
- **Benefits**: Standardized 1-minute expiry forecasting discipline; per-strategy performance intelligence; ensemble/regime weighting; pipeline-suffocation detection; payout-aware EV gating; backtest/anti-overfit rigor; TIDOS-governed change control.
- **Risks**: Trading-risk domain (requires strict evidence verification for live-trading decisions); no guaranteed wins; small-sample overconfidence; backtest-vs-live divergence. Mitigated by Safety Boundary (§30) + TIDOS final-authority workflow (§29).
- **Priority**: High
- **Affected Modules**: `personas/tidostrade.md` (NEW), `personas/README.md` (index), `commands/session_commands.md` (trigger registration)
- **Recommended Version**: 3.3.0 (MINOR — additive persona, no breaking change)
- **Status**: Implemented 2026-09-13 via explicit user-commanded upgrade (Protected OS Freeze override authorized by user request).

---

### Title: TIDOSUIUX Persona (Universal UI/UX, Product Design & Interface Engineering)

- **Date**: 2026-09-13
- **Requestor**: User (explicit `TIDOSUIUX` creation handoff; NO commit authorized)
- **Reason**: TIDOS needs a domain-agnostic, reusable UI/UX specialist persona (UX research, interaction design, design systems, accessibility, responsive/adaptive, UI engineering incl. Flutter/web/desktop) invocable via `TIDOSUIUX`, operating under TIDOS final authority.
- **Benefits**: Standardized audit lifecycle (DISCOVER→VERIFY); screen-by-screen analysis discipline; design-decision quality gate (problem/evidence/impact/trade-off/confidence); alternatives with migration risk; governed implementation control (no silent changes to business logic/security/data/APIs).
- **Risks**: Subjective redesign churn; fabricated usability/accessibility claims. Mitigated by §§13/20 (evidence + confidence levels, anti-patterns) and §22 implementation control.
- **Priority**: High
- **Affected Modules**: `personas/tidosuiux.md` (NEW), `personas/README.md` (index), `commands/session_commands.md` (trigger registration)
- **Recommended Version**: 3.3.0 (MINOR — additive persona, no breaking change)
- **Status**: Implemented locally 2026-09-13; UNCOMMITTED per explicit handoff governance (§§1, 26–27). Commit only on separate explicit authorization.

---

### Title: TIDOS Persona Router (smart auto-selection of personas)

- **Date**: 2026-09-13
- **Requestor**: User (explicit choice: Auto-router)
- **Reason**: Persona selection is 100% manual keyword today (`TIDOSTRADE`, `TIDOSUIUX`). User wants TIDOS to smartly use the right persona in any mounted project. Precedent: Plugin Engine already auto-mounts `plugins/*.md` from Bootstrap stack detection — personas have no equivalent.
- **Proposed behavior**:
  1. Explicit keyword always wins (user override; backward compatible).
  2. Otherwise score each persona from a registry (`personas/registry.md`): request intent signals + Bootstrap stack detection + target project context (e.g., SMARTRAD workspace weights trading signals).
  3. Score above threshold → auto-activate + announce (`TIDOS persona active: <NAME> — <reason>.`).
  4. Score below threshold / tie → ask user (suggest-only fallback).
  5. Initial signal map: trading/backtest/strategy/payout/candle → TIDOSTRADE; UI/UX/design/accessibility/screen/layout/responsive → TIDOSUIUX; else `roles.md` specialists via workflow Stage 4.
- **Benefits**: Zero-friction persona use in every mounted project; deterministic and auditable (scores + reasons announced); manual keywords keep working.
- **Risks**: Mis-routing (mitigated: announcement + explicit override + ask-on-ambiguity); registry drift as personas are added (mitigated: each persona spec declares its own `## Routing Signals` block); protected-file edits (mitigated: additive only, evolution workflow with explicit approval).
- **Priority**: High
- **Affected Modules**: `personas/registry.md` (NEW), `engines/workflow_engine.md` (Stage 2/Stage 4 routing step, additive), `commands/session_commands.md` (auto-route directive, additive), `personas/tidostrade.md` + `personas/tidosuiux.md` (`## Routing Signals` blocks, additive). No kernel/rules/roles changes.
- **Recommended Version**: 3.3.0 (MINOR — additive, backward compatible)
- **Acceptance**: routing matrix green (sample requests → expected persona, incl. override + ambiguous-ask cases); activation announcement present; manual keywords unaffected.
- **Status**: PROPOSED 2026-09-13. Awaiting explicit user approval before implementation. Note: TIDOSUIUX change set still uncommitted; router builds on working tree.

---

### Title: TIDOS Update Gate (update-on-start with memory-safe force)

- **Date**: 2026-09-13
- **Requestor**: User (explicit update-system request; safety variant: memory-safe force)
- **Reason**: `START TIDOS` documents only a plain `git pull` in `.tidos` — no force, no version check, no offline handling, submodule-mode only. User wants every session to force-sync with GitHub before work begins.
- **Proposed behavior (Step 0, before the 9-step boot)**: locate TIDOS (`.tidos` → central/multi-root dir → local copy) → `git fetch` + compare `HEAD` vs remote → behind: memory-safety check then `git reset --hard` → report before→after version in Startup Report → boot. Rules: abort (never wipe) on uncommitted `memory/`/`evolution/` changes; never block boot when network/remote unreachable (warn + continue local); local-copy mode (no `.git`) skips with warning.
- **Benefits**: Every project always works on current TIDOS; deterministic startup version reporting; zero silent loss of institutional memory.
- **Risks**: Force-sync discards uncommitted OS-file edits (intended — central is source of truth); `reset --hard` briefly disrupts concurrent edits (mitigated: run at session start only).
- **Priority**: High
- **Affected Modules**: `scripts/update.ps1` + `scripts/update.sh` (NEW, non-protected dir), `commands/session_commands.md` (`START TIDOS` bullet), `TIDSTART.md` (Step 0 note), `scripts/README.md` (index)
- **Recommended Version**: 3.3.0 (MINOR — additive gate, backward compatible)
- **Acceptance**: already-current / behind-updated / uncommitted-memory-blocked / offline-continue paths verified; Startup Report shows version transition.
- **Status**: Implemented locally 2026-09-13 via explicit user approval (safety variant + wiring both approved). Live-tested already-current path (`8c29e0d`, exit 0). UNCOMMITTED — commit only on separate explicit authorization.

---

### Title: TIDOS Framework Firebase Auth (Google Sign-In + Email/Password)

- **Date**: 2026-09-13
- **Requestor**: User (explicit; authorized full Firebase actions)
- **Reason**: TIDOS needs first-party authentication for its users across projects. Firebase project `tidos-framework` created via CLI; providers Google + email/password.
- **Delivered**: `config/firebase.md` (canonical project/app metadata — public web config only), `scripts/auth_verify.ps1` + `scripts/auth_verify.sh` (REST: sign-in, token verify, status), `docs/firebase_auth.md` (setup, security, troubleshooting), `TIDOS AUTH` directive (`commands/session_commands.md`), optional Step 0 note (`TIDSTART.md`).
- **Blocker (external)**: Firebase provisions a fresh project's Auth service + enables providers only from the console — no CLI/API equivalent exists, `gcloud` absent, `login:ci` needs a browser. Exact console steps are documented in `docs/firebase_auth.md` §2 (get-started → enable Email/Password → enable Google).
- **Risks**: Public web API key in repo is safe by design (client-side); service-account/OAuth secrets stay in `.env`/vault. Tokens are untrusted + never logged. Auth never blocks offline boot.
- **Priority**: High
- **Affected Modules**: `config/firebase.md`, `scripts/auth_verify.ps1`, `scripts/auth_verify.sh`, `docs/firebase_auth.md`, `commands/session_commands.md`, `TIDSTART.md`
- **Recommended Version**: 3.3.0 (MINOR)
- **Status**: Framework integration implemented locally 2026-09-13. Console enable pending (user browser action). UNCOMMITTED — commit only on separate explicit authorization.

**Update 2026-09-13 (committed `953ce67`, then extended)**: Console steps completed (Email/Password verified live via `INVALID_LOGIN_CREDENTIALS`). Per user feature request, auth is now a **MANDATORY boot gate** (TIDSTART.md Step 0.5): `-Session` remember-me check; exit 1 blocks boot and the user must **Login** or **Register** (email/password only, in-session, min 6-char password); verification email auto-sent; refresh token persisted to `~/.tidos/tidos-session.json` (outside repo, never committed); `-Logout` clears it; exit 2/network failure warns and continues (auth never hard-blocks when Firebase unreachable/unconfigured). UNCOMMITTED — commit only on separate explicit authorization.

---

### Title: TIDOSHELP (always-on command list menu)

- **Date**: 2026-09-13
- **Requestor**: User (explicit: "always when we write TIDOSHELP give me all the command list with explanations to choose between them")
- **Behavior**: `TIDOSHELP` → always output EVERY directive from `commands/session_commands.md`, grouped (Startup / Execution), each with a one-line explanation, then ask the user which to execute. Treated as a selection menu, never as a work task.
- **Deliverable**: `# Section 0: Help & Command Selection` added to `commands/session_commands.md`.
- **Protected File Note**: `commands/` is OS-protected; this additive directive was written per explicit user request.
- **Priority**: High
- **Recommended Version**: 3.3.0 (MINOR)
- **Status**: Implemented locally 2026-09-13. UNCOMMITTED — commit only on separate explicit authorization.

---

### Title: TIDOS Persona Factory (self-learning persona generation + central-brain auto-sync)
- **Date**: 2026-09-13
- **Requestor**: User (explicit: let TIDOS create/develop personas per project, learn from users across projects, gather everything in the central GitHub brain)
- **Approvals**: OS Freeze exception GRANTED by user ("yes approve persona factory", 2026-09-13) — the factory may add NEW files to protected `personas/` and push to `origin/main`. Decisions via Q&A: fully automatic generation, auto-sync to GitHub, triggers = both stack-gap + recurring-domain.
- **Deliverables**: `engines/persona_factory_engine.md` (engine spec), `scripts/factory_sync.ps1` + `factory_sync.sh` (3-path commit+push, no force), `TIDOS PERSONA FACTORY` / `STOP FACTORY` directives (`commands/session_commands.md`), `personas/registry.md` §5 factory rules, `config/framework.md` `persona_factory` block, `docs/persona_factory.md` operator guide.
- **Safety**: new-file-only (never edits/deletes existing personas); one run per boot; factory_sync stages exactly persona+registry+evolution; never force-push; TIDOS remains final authority; generated personas are advisors.
- **Priority**: High
- **Recommended Version**: 3.3.0 (MINOR)
- **Status**: Implemented locally 2026-09-13. UNCOMMITTED — commit/push only on separate explicit authorization.

---

### Title: GPTID — ChatGPT Free Local Browser Relay Persona (no API, no key)

- **Date**: 2026-09-21
- **Requestor**: User (explicit GPTID build task)
- **Reason**: TIDOS needs an optional local bridge to the user's ChatGPT Free web session for second-opinion review/audit/architecture/debug without any OpenAI API usage or key.
- **Deliverables**: `personas/tidosgptid.md` (persona, trigger `GPTID`, 6 modes), `engines/gptid_relay_engine.md` (relay spec), `browser_relay/` (`gptid_protocol.py`, `relay_server.py`, `chatgpt_adapter.py`, `selector_registry.json`, `gptid_cli.py`, `tests/test_gptid_protocol.py`), `docs/gptid.md`, `scripts/gptid.ps1`/`.sh`, `scripts/verify_gptid.ps1`, `templates/gptid_task.md` + `gptid_response.md`; additive registry/README/commands/config wiring (`GPTID` row, `TIDOS GPTID` directive, `gptid:` config block); workflow explicit-keyword list extended.
- **Safety**: localhost-only relay; dedicated/user-selected browser context; no password/token/cookie handling; redaction on build/ingest/render/log; CAPTCHA/auth bypass out of scope (`UNAVAILABLE`); ChatGPT output is external-untrusted; TIDOS remains sole implementation authority; SMARTRAD review-only boundary; optional channel (TIDOS fully functional offline).
- **Priority**: High
- **Affected Modules**: `personas/`, `engines/`, `browser_relay/` (NEW), `docs/gptid.md` (NEW), `scripts/gptid.*` + `verify_gptid.ps1` (NEW), `templates/gptid_*` (NEW), `config/framework.md` (`gptid:` block), `commands/session_commands.md` (`TIDOS GPTID`)
- **Recommended Version**: 3.3.0 (MINOR — additive, backward compatible)
- **Status**: Implemented 2026-09-21 — verification pending (`scripts/verify_gptid.ps1` + E2E probe).

**Update 2026-09-22 (ACCEPTANCE PASS, session `gptid-20260922-001`)**: readiness remediation implemented + verified (shared semantic-first detector, unified budgets, liveness gates, monitor downgrade, detector-backed `/dom_probe`); 40/40 + 14/14 tests, validator 60/60; ONE bounded REVIEW E2E passed (`gtask-5270055bf900`, correlation=True, `chatgpt-untrusted`).

---

### Title: GPTID follow-up — unassisted `start` failure (RESOLVED upstream, verified 2026-10-11)

- **Date**: 2026-09-22
- **Observed**: `scripts/gptid.ps1 start` → `gptid_cli.py cmd_start` never brings the relay up unassisted. Two defects identified during the acceptance session: (1) `cmd_start` spawns `Popen([sys.executable, "-u"] + cmd)` where `cmd[0]` is already the interpreter → the interpreter binary is passed as a script argument and the child exits immediately; (2) the 15s health window (`30 × 0.5s`) is too short for headed Chromium launch + navigation + classification (observed 45–75s), so even a healthy launch reports `STATUS=UNAVAILABLE (reason=relay did not become healthy)`. Workaround used: direct `relay_server.py` launch with PID recorded manually.
- **Proposed scope**: fix argv construction (single interpreter), extend/parameterize the health window (e.g. 120s for headed), reuse don't respawn when a live relay already answers.
- **Priority**: Medium
- **Affected Modules**: `browser_relay/gptid_cli.py` (`cmd_start`), optionally `scripts/gptid.ps1` (pass-through timeout)
- **Status**: RESOLVED upstream — both defects fixed in current `cmd_start` (single-interpreter `cmd` + `DEFAULT_STARTUP_TIMEOUT = 120` + "already running" reuse). Verified 2026-10-11: multiple unassisted headed starts succeeded tonight; unit tests 89/89. No change needed.

---

### Title: GPTID follow-up — relay PID-file lifecycle hygiene (RESOLVED upstream, verified 2026-10-11)

- **Date**: 2026-09-22
- **Observed**: `~/.tidos/gptid-relay.pid` (outside repo) pointed at manually launched relay PIDs during acceptance (PID 4836/6952/12728) rather than a CLI-managed lifecycle; `stop` kills whatever PID is recorded without verifying it is a relay; stale PID files survive dead processes.
- **Proposed scope**: `stop`/`start` verify the recorded PID is a live `relay_server.py` process before kill/reuse; stale PID invalidated with a warning; document PID ownership in `docs/gptid.md`.
- **Priority**: Low
- **Affected Modules**: `browser_relay/gptid_cli.py` (`cmd_start`, `cmd_stop`), `docs/gptid.md`
- **Status**: RESOLVED upstream — `_is_relay_process` identity checks in `cmd_stop` (refuses blind kill, PID-reuse safe), `_reap_stale_pidfile` on start, `_stop_owned` with re-check. Verified 2026-10-11 live: CONNECTED → owned-PID stop → DISCONNECTED → fresh headed start; stale PID 9536 cleared without harm. No change needed.

---

### Title: TIDOSMOBILE Persona (Mobile & Flutter Systems Architecture Specialist)

- **Date**: 2026-10-11
- **Requestor**: Persona Factory v2.0 (auto-synthesized via live web-research)
- **Reason**: Detected prominent multi-project Flutter / Android footprint across workspace (`Proflimit`, `SMARTRAD`, `ZTAP`, `CrownVerse`, `MaYdi3ch`, `dentaltid`). Uncovered stack gap in `personas/registry.md`.
- **Benefits**: Specialized expert scaffolding for Flutter 3+, Dart, Android API 35, Gradle 8.5+, Java 21, and iOS. Includes explicit negative constraints to prevent memory leaks (controller disposal) and build mismatches (AGP / Gradle matrix).
- **Deliverables**: `personas/tidosmobile.md`, `personas/registry.md`, `personas/README.md`.
- **Priority**: High
- **Recommended Version**: 4.0.0
- **Status**: Implemented & Registered 2026-10-11 via Persona Factory v2.0.

---

### Title: GPTID follow-up — extractor captures SENT echo instead of assistant reply (RESOLVED)

- **Date**: 2026-10-11
- **Observed**: With relay `CHATGPT_READY`, two bounded `ask --mode UIUX` round-trips (`gtask-8b41d8347d3d` 346 chars, `gtask-8d3358c213e2` 695 chars, correlation=True both) returned the `[TIDOS via GPTID]` SENT task template verbatim instead of an assistant review — completion detector appears to fire on the SENT bubble rendering (stop-button-gone + stable text) before any assistant message streams.
- **Root Cause**: Selector chain relied on bare `[class*='whitespace-pre-wrap']` which matched user bubbles (including our sent prompt). Scoping by `data-message-author-role` failed because modern ChatGPT removed that attribute.
- **Resolution (v4.0.1)**:
  1. Updated `selector_registry.json` (v1.0.2) with modern ChatGPT assistant selectors: `article:has(button[aria-label*='Copy']) .markdown`, `article div.markdown`, `article [class*='markdown']`, `div.markdown`, `.markdown`, and `article .prose`. Removed bare `[class*='whitespace-pre-wrap']`.
  2. Updated `chatgpt_adapter.py` so `_assistant_count()` iterates through the entire fallback chain instead of hardcoded index 0.
  3. Updated `_last_assistant_text()` to scan elements backwards and reject any element starting with `SENT_ECHO_PREFIX` (`[TIDOS via GPTID`).
  4. Updated `wait_completion()` and `extract_response()` to guard against echoes and treat them as invalid.
- **Priority**: High
- **Affected Modules**: `browser_relay/chatgpt_adapter.py`, `browser_relay/selector_registry.json`
- **Status**: Implemented & Verified 2026-10-11 (v4.0.1).
- **Follow-up 2026-10-11 (live-DOM correction, committed v1.0.3)**:
  - Live `/dom_probe` on the real thread (`UIUX Task`, wall=ok) proved v4.0.1's article/markdown/role/testid selectors ALL match 0 nodes in this DOM (`article`=0, `.markdown`=0, `[data-message-author-role]`=0) — yet 8 `button[aria-label*='Copy']` + 16 `div[class*='message']` + 29 `main p` exist. The v4.0.1 echo guards DO work (honest `TIMEOUT` instead of false `OK`), but its selectors cannot extract here.
  - Working structure found by probe ladder: turns are `div[class*='turn']` (12 live, 28 `p`), original fallback #2 was right all along. Registry bumped to **v1.0.3** (uncommitted): prepended `div[class*='turn']:has(button[aria-label*='Copy'])`, `:has(Copier)` variant, bare `div[class*='turn']` — echo guards disambiguate user vs assistant turns.
  - **Live proof**: `ask --mode UIUX gtask-9ae8770a7af6` → `CAPTURED (2652 chars, correlation=True)` — first genuine ChatGPT review (3 UX observations + 2 accessibility notes + ranked fix list), evaluated by TIDOS against `tableau_de_bord.py` evidence (see `Prog Info/log.md` 2026-10-11). Unit tests 89/89 OK on v1.0.3.
  - Commit only on explicit authorization (`browser_relay/selector_registry.json` v1.0.2 → v1.0.3) — authorized & committed 2026-10-11, push pending user action.
