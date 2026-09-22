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

## CHORA Digest — chora-20260911-003 (2026-09-11, CLOSED)

- **Trigger**: MANUAL (TIDOSCHORA), target SMARTRAD next-step plan.
- **Partner**: CHATGPT (Comprehensive, Round 1, 1/1 received, sanitize PASS, channel MALFORMED-tolerant).
- **Claims**: C1 VERIFIED (ahead-1 + ~90 files), C2 governance-consistent, C3 VERIFIED (2% cap / 4-step max / closed-candle / Demo-default in code), C4 sound, C5 efficient (analyze 0 issues, 279 tests PASS).
- **Decision**: Option A — Stabilize & verify current tree → reassess; escalate A→C only on invariant failure. Option B rejected for now.
- **ADR ref**: ADR-chora-20260911-003 (Option A, evidence-backed, validation: analyze+test+commit hygiene).
- **Outcome**: decision_changed=false, useful=true, risks_identified=5, claims_verified=4, claims_rejected=0, implementation_result=PASS.

## CHORA Digest — chora-20260911-004 (2026-09-11, CLOSED without Act)

- **Trigger**: MANUAL (TIDOSCHORA), pasted MEASURE-only telemetry plan (advisor Turn-1 arrived before scope lock; scope locked retroactively).
- **Partner**: CHATGPT (Comprehensive, sanitize PASS, channel MALFORMED-tolerant, embedded "toggle to Act" directive classified untrusted-data, NOT obeyed).
- **Claims**: gate order + all config defaults VERIFIED (`strategy_provider.dart:97-226,1514,1603-1910`); `AuditConventions.minSampleSize=20` VERIFIED; shadow `wasRejectedByFilter/evaluatePendingTrades` VERIFIED; `rejectionBreakdown` EXISTS (`v2_pipeline_backtester.dart:36,55,644`, population parity = Act-check); `lib/domain/telemetry/` free VERIFIED. REJECTED/stale: "29 codes" (actual 26 enum entries in `rejection_reason.dart`), "63 tests passing" (full suite measured 279/279 this session).
- **Decision**: MEASURE-only conditionally approved (read-only, Compass-safe, no behavior change) with preconditions (branch-first per plan §6 vs Hold conflict, fold in corrections). Act NOT authorized — user self-builds in OpenCode.
- **Outcome**: decision_changed=false, useful=true, risks_identified=3, claims_verified=6, claims_rejected=2, implementation_result=HOLD (user-owned).

## CHORA Digest — chora-20260913-005 (2026-09-13, CLOSED — tidy-up applied)

- **Trigger**: UI de-duplication audit (TIDOSUIUX) — remove redundant dashboard surfaces.
- **Verified dead code (0 references, 0 imports, 0 routes, 0 exports, 0 tests, 0 dynamic loads)**: `ai_reasoning_panel.dart`, `gravity_panel.dart`, `history_panel.dart`, `status_panel.dart`, `confidence_gauge.dart`, `signal_prediction.dart` — legacy panels superseded by MarketIntelligencePanel / EnhancedTradeLedger.
- **Action**: 7 unreferenced panel files DELETED (the 6 above + `signal_card.dart`); full-context grep (lib + test, class + file names) confirmed no ingress before removal. SignalCard overlay removed from the chart so the trading zone stays clean; signal direction/grade/calibrated-%/EV render once in the MARKET DATA panel.
- **Constraint**: UI-only. No trading logic, RiskManager, GALE, RegimeGate, EV, payout, stake, telemetry, thresholds, or safety behavior touched.
- **Outcome**: useful=true, implementation_result=PASS (dead-code cleanup + dashboard one-source-per-datum consolidation, see dashboard de-dup map).

## CHORA Digest — chora-20260914-006 (2026-09-14, OPEN — pending shadow soak)

- **Trigger**: MANUAL (authorized "APPROVE FOR IMPLEMENTATION AFTER SPECIFIC CORRECTIONS"), Phase 7 Tiered Recovery — bounded martingale Step-1 relaxation.
- **Partner**: OpenCode (big-pickle), in-session, sanitize PASS.
- **Claims VERIFIED in code**: recovery is CONDITIONAL martingale (loss sets `_activeRecoveryStep = step+1`, but RecoveryEngine resets unless evidence passes); defaults never escalate (`stakeModel=flat`, `rolloutMode=controlled`); model EV is unconditional per-trade EV (never streak-conditional) → Step 1 is UNVALIDATED by design; `recentVsLongTermGap = recent−longTerm`, healthy when ≥ 0 (authorization text was INVERTED — implemented corrected semantics); exposure math base $1/balance $100/payout 0.89 = Step1 $3.25 (3.25%), Step2 $8.02 (8.02%), Step3 $18.15 (18.15%), Step4 blocked.
- **Decision**: G1 deferral ONLY while `recoveryStep1Enabled && step1ProtectionsActive(useEvFilter,useAdxFilter,useRegimeDirectionGate,useWeakRegimeFilter,useMartingaleSequenceCap all ON) && step==1`; G2 evidence wall unchanged; G3 stricter (exact evidence, empEV ≥ 0.05, ADX ≥ 25, drawdown < 0.8%, gap ≥ 0); step ≥ 4 BLOCK; kill-switch OFF restores legacy byte-for-byte; 4 new codes only in the flag branch.
- **Outcome**: decision_changed=false, useful=true, risks_identified=1 (Step-1 statistically unvalidated — telemetry states it explicitly), claims_verified=5, claims_rejected=0, implementation_result=IMPLEMENTED — SHADOW SOAK REQUIRED. No commit.

## GPTID E2E Acceptance — gptid-20260922-001 (2026-09-22, CLOSED — PASS)

- **Trigger**: explicit `GPTID` invocation → `TIDOS GPTID audit` → implement-remediation → final acceptance gate (headed session PID 12728).
- **Audit finding**: claimed readiness fix NOT present (chain-only detection, split 10s/5s budgets, stale LOADING reproduced live: dead page + `tabs=0` reported LOADING while relay claimed CHATGPT_READY).
- **Remediation** (`browser_relay/chatgpt_adapter.py`, `browser_relay/relay_server.py`, `browser_relay/tests/test_gptid_readiness.py`, `scripts/verify_gptid.ps1`): shared semantic-first `composer_usable` detector; unified total budgets; liveness gates; monitor downgrade via `sync_relay_state`; detector-backed `/dom_probe`; 14 regression tests (A–L); +8 validator checks.
- **Verification**: 40/40 existing tests, 14/14 readiness tests, validator 60/60; live honest READY on authenticated composer; honest ERROR after headed-page death (downgrade log verified); headless Cloudflare wall → `AUTHENTICATION_REQUIRED`, stopped, never bypassed.
- **E2E**: exactly ONE bounded REVIEW round-trip on the verified headed session — `gtask-5270055bf900`, 1056 chars captured, correlation=True. Response held as `chatgpt-untrusted`. No retry, no second attempt.
- **Constraints**: no credentials/cookies/tokens accessed; no SMARTRAD/trading/broker/risk/CHORA code touched; no E2E re-run at close-out.
- **Follow-ups tracked (not implemented)**: `gptid.ps1`/`gptid_cli.py` unassisted-start failure (double-Python spawn + 15s window too short for headed launch); PID-file lifecycle hygiene. See `evolution/SUGGESTIONS.md`.
- **Outcome**: useful=true, implementation_result=PASS (acceptance GREEN, complete).
