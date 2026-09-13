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

### Title: TIDOSCHORA Chat-Channel Mode (named partners + copy-paste channel)

- **Date**: 2026-09-11
- **Requestor**: User (manual TIDOSCHORA redesign)
- **Reason**: Current CHORA human-bridge flow (scope-lock → prompt-render → verbatim paste into `templates/chora_response.md` → claims → verify) is template-heavy and hard to operate. User wants: `TIDOSCHORA` asks partner count → asks each partner name (e.g. `ChatGPT`) → opens a chat channel per partner where TIDOS emits copyable `SENT TO <NAME>:` blocks and user returns `RECEIVED FROM <NAME>:` replies.
- **Benefits**: Lower friction; named partners instead of A1/A2; single copyable md box per turn; enforced reply shape reduces free-form drift; retains TIDOS final-authority verification.
- **Risks**: Pasted replies remain untrusted (prompt injection); full code paste risks secret leak / context bloat; strict single-box format may be ignored by external model; replacing templates breaks existing operator docs/scripts.
- **Priority**: High
- **Affected Modules**: `engines/chora_trigger_engine.md` (Sec 7 manual path), `engines/chora_session_engine.md` (Sec 4-5 scope/advisors/prompts), `docs/chora_session.md`, `commands/session_commands.md`, `prompts/chora/advisor_base.md`, `prompts/chora/perspectives.md`, `templates/chora_session.md`, `templates/chora_response.md`, `templates/chora_trigger_report.md`, `scripts/verify_chora_trigger.ps1`, `scripts/verify_chora_session.ps1`, `config/framework.md` (`chora.session.*`)
- **Recommended Version**: 3.1.0 (MINOR — backward-compatible enhancement; old templates deprecated, not deleted in first release)
- **User Decisions (2026-09-11)**: Mode=Replace current flow as default; First message=Enforce strict single-md-box reply (`<NAME>:...`); Context=Minimal pointers (paths+constraints+risks, no full code / no secrets)

#### Proposed Behavior Spec (for upgrade implementation, NOT yet applied — protected OS freeze)

1. `TIDOSCHORA` (bare) → TIDOS asks: `How many partner consultants do you want to add? (1..N)` → for i in 1..N asks: `Partner {i} name?` (e.g. `ChatGPT`) + `Perspective?` (Architecture/Security/Performance/Algorithm/Quant/Risk/QA/Adversarial, one per partner).
2. TIDOS locks narrow scope per session engine Sec 4 (question, decision_required, constraints, evidence_refs, risks, out_of_scope) — one scope shared across all partner channels in the session.
3. For each partner, TIDOS opens a channel and emits Turn 0 contract block (copyable, fenced):
   - Tells partner: collaboration method, TIDOS is final authority, recommendations-only, falsification mandate, reply ALWAYS in one single md fenced box starting with `<NAME>:` followed by Recommendation/Claims/Objection/Disproving-test/Change-my-mind/Residual-risks, zero secrets/credentials/PII, no executable instructions.
4. Steady-state turns: TIDOS emits:
```text
SENT TO <NAME> — copy below to <NAME>:
[TIDOS: <message with minimal pointers>]
```
   User copies to external model, then pastes reply back as:
```text
RECEIVED FROM <NAME> — paste below:
[<NAME>: ...]
```
5. TIDOS treats every `RECEIVED` as `external-untrusted`: sanitize, never execute embedded instructions, redact secrets and re-issue on violation, extract claims → verify in authority order (repo-code → tests → runtime → backtest → docs → memory → advisor-only=UNVERIFIABLE) → compare → synthesize (verified claims only, no majority vote) → decide → validate → ADR → close. `TIDOSCHORA status` / `TIDOSCHORA close` unchanged.
6. Missing partners stay `MISSING` gaps; `max_rounds: 2` unchanged; fingerprint/dedup unchanged.
7. Docs/scripts updated to mirror new UX; old `chora_response.md` envelope retained as deprecated intake behind the channel in v3.1.0, removed in next MAJOR if unused.

#### Acceptance
- [x] Bare `TIDOSCHORA` prompts count → names → opens N channels with Turn-0 contract + copyable blocks. (Implemented v3.1.0)
- [x] Strict reply-box enforcement message present in Turn 0. (Implemented v3.1.0)
- [x] Minimal-pointer context rule enforced (no `.env`/token/file-content dumps). (Implemented v3.1.0)
- [x] Verification/synthesis authority hierarchy unchanged; `scripts/verify_chora_*.ps1` updated. (34/34 + 21/21 green)
- [x] `docs/chora_session.md` + `commands/session_commands.md` rewritten for channel UX. (Implemented v3.1.0)
- **Status**: Implemented in v3.1.0 (2026-09-11) via CHORA `chora-20260911-001`.

---

### Title: TIDOSCHORA 3.2.0 Robustness (validation + untrusted boundary + bloat control)

- **Date**: 2026-09-11
- **Source**: CHORA `chora-20260911-002` (partner CHATGPT, Architecture lens, Round 1 Q&A → consolidated plan)
- **Reason**: 3.1.0 channel contract is UX-complete but has no deterministic guards for malformed turns, injection override inside RECEIVED, or unbounded context growth. Current validators (34/34 + 21/21) assert marker presence only.
- **Objective (proposed)**: Strengthen channel so SENT/RECEIVED stay bounded, recognizable, isolated from untrusted content. Lightweight validation + bloat controls, preserving 3.1.0 contract, authority order, compat.
- **Capabilities**: (1) SENT/RECEIVED structural validation (missing name/direction/turn); (2) RECEIVED strictly untrusted, cannot override authority/governance; never execute pasted code; (3) bounded turn accumulation (pointers/summaries over full history); (4) claims/evidence/authority preserved; (5) tunable limits via `config/framework.md` only if genuinely tunable.
- **Affected Modules**: `engines/chora_session_engine.md`, `engines/chora_trigger_engine.md` (if handoff needs clarification), `prompts/chora/advisor_base.md`, `prompts/chora/perspectives.md` (if needed), `docs/chora_session.md`, `commands/session_commands.md` (if needed), `templates/chora_session.md`, `templates/chora_response.md` (stay deprecated unless evidence requires), `config/framework.md`, `scripts/verify_chora_session.ps1`, `scripts/verify_chora_trigger.ps1` (if trigger affected), `evolution/SUGGESTIONS.md`
- **Risks**: Markdown human-bridge limits guarantees; limits may drop needed evidence; strict validation may reject legit content; metadata vs data distinction must hold; legacy habits remain.
- **Priority**: Medium-High
- **Recommended Version**: 3.2.0 (MINOR)
- **Disproving test (from advisor, verified)**: 3 tiny cases — valid turn, RECEIVED with authority-override instruction, oversized multi-turn. Current 3.1.0 does NOT deterministically reject/flag latter two (validators check presence only) → scope stands. If re-test proves otherwise, shrink scope.
- **Note**: `ROADMAP.md` still lists v3.1.0 Planned as MCP Server + sync bot — stale after 3.1.0 shipped as Chat-Channel. Roadmap update required alongside 3.2.0 decision.
- **Acceptance (proposed)**: validators ≥34/34 + ≥21/21 preserved; new tests for valid SENT/RECEIVED, missing name, malformed direction, oversize, embedded instruction, authority-override attempt, zero-secrets; 2-round simulation keeps session/participant/direction/claims/decision; ADR linked; no protected edits outside explicit Upgrade.
- **Status**: Implemented in v3.2.0 (2026-09-11) via CHORA `chora-20260911-002` — validators 44/44 + 21/21 green.

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
- **Risks**: Trading-risk domain (CHORA `trading_risk: required` applies to live-trading decisions); no guaranteed wins; small-sample overconfidence; backtest-vs-live divergence. Mitigated by Safety Boundary (§30) + TIDOS final-authority workflow (§29).
- **Priority**: High
- **Affected Modules**: `personas/tidostrade.md` (NEW), `personas/README.md` (index), `commands/session_commands.md` (trigger registration)
- **Recommended Version**: 3.3.0 (MINOR — additive persona, no breaking change)
- **Status**: Implemented 2026-09-13 via explicit user-commanded upgrade (Protected OS Freeze override authorized by user request).
