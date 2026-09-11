# TIDOS CHORA Trigger Engine Specification (v3.1)

The **CHORA Trigger Engine** (`engines/chora_trigger_engine.md`) is the entry and escalation
layer that answers one question before consequential work proceeds:

> "Should TIDOS consult external AI advisors before continuing?"

It does NOT replace the CHORA deliberation workflow (advisors, prompts, claims,
verification, synthesis, decision, validation). It decides whether that workflow
should start, and with what urgency. TIDOS remains the final authority: every
external recommendation is verified against repository evidence before commit.

## 1. Position in the architecture

```text
TIDOS task / decision
  |
  v
CHORA TRIGGER ENGINE --> NONE --> continue normally
  |
  +--> RECOMMENDED --> ask user --> YES: start CHORA / NO: continue + record decline
  |
  +--> REQUIRED --> start CHORA, block affected decision until review completes
```

Manual path `TIDOSCHORA` always starts consultation regardless of engine output.

Evaluation points (decision boundaries): Task understanding (Stage 2), Plan
(Stage 3), before high-risk Stage 5 implementation, after failed implementation,
after regression, before irreversible operation, before final high-impact decision.
Status may escalate NONE -> RECOMMENDED -> REQUIRED within one decision scope.
Downgrade requires a meaningful context reset or a new decision scope.

## 2. Trigger levels

Exactly one primary decision: `NONE`, `RECOMMENDED`, or `REQUIRED`.

### NONE

Sufficient evidence, routine task. Continue normally, do not interrupt the user.
Examples: typo fix, local rename, import addition, obvious syntax error,
formatting, localized bug with clear root cause, routine test update,
read-only telemetry/logging/metrics/exports with no production behavior change.

### RECOMMENDED

External consultation could materially improve confidence or reduce
architectural risk. TIDOS continues helping but presents a concise
recommendation with reasons and asks whether to start CHORA.
On NO: record `chora_recommendation_declined` with the decision fingerprint
and do not re-ask unless context materially changes.

### REQUIRED

The decision crosses a high-risk boundary (Section 5). TIDOS must NOT
implement the affected change before CHORA completes. Blocking is
decision-scoped only: unrelated work continues. No silent bypass.

## 3. Reason taxonomy (stable, extensible)

Every non-NONE result cites >= 1 code. New codes may be appended; existing
codes are never renamed or removed:

```text
MANUAL_REQUEST, HIGH_ARCHITECTURAL_COMPLEXITY, MULTIPLE_VALID_ARCHITECTURES,
HIGH_IMPACT_CHANGE, SECURITY_IMPACT, FINANCIAL_IMPACT, TRADING_RISK_IMPACT,
PERSISTENT_DATA_IMPACT, DATABASE_MIGRATION, IRREVERSIBLE_CHANGE,
DIFFICULT_TO_REVERSE, CONFLICTING_EVIDENCE, AMBIGUOUS_REQUIREMENT,
HIGH_UNCERTAINTY, MULTIPLE_PLAUSIBLE_ROOT_CAUSES, REPEATED_FAILURE,
REGRESSION_RISK, LIVE_BACKTEST_DIVERGENCE, PERFORMANCE_UNCERTAINTY,
EXTERNAL_API_UNCERTAINTY, LARGE_CROSS_SYSTEM_CHANGE
```

## 4. Signals (no single confidence score)

Do NOT use model self-confidence or raw file count as primary triggers.
Combine observable signals: impact, uncertainty, reversibility, architectural
complexity, conflicting evidence, failure history, risk domain. File count
alone never triggers. Impact beats raw size (20-file rename can be NONE;
2-file risk-engine change can be REQUIRED).

- Architectural complexity: multiple valid architectures, large refactor,
  cross-module deps, new subsystem, public API redesign, orchestration /
  state-management / plugin-architecture changes.
- Uncertainty (observable only: conflicting evidence, ambiguous requirements,
  multiple plausible root causes, insufficient repo evidence, unknown external
  behavior, uncertain API/performance semantics).
- Conflicting evidence: docs != code, tests != behavior, backtest != live,
  modules with conflicting assumptions, prior decision != current arch.
- Multiple valid options with meaningful consequences -> RECOMMENDED; if
  irreversible/high-risk/expensive-to-reverse -> REQUIRED. Trivial local
  alternatives (List vs Set) stay NONE.
- Repeated failure: same root problem after multiple attempts, repeated test
  failures, fix-causes-regression, repeated reverts, no stable root cause.
  Threshold `chora.repeated_failure_threshold` is configurable (default 3).
- Change surface: files/modules/interfaces/schemas affected, dependency depth,
  test/runtime surface. Weigh impact, not count.
- Reversibility: REVERSIBLE / PARTIALLY_REVERSIBLE / DIFFICULT_TO_REVERSE /
  IRREVERSIBLE. Low impact + irreversible -> usually RECOMMENDED; high impact
  + difficult-to-reverse -> REQUIRED.

## 5. Baseline matrix + REQUIRED overrides

Conceptual baseline (transparent rules, not a black box):

```text
                    IMPACT
             LOW      MEDIUM     HIGH
LOW UNC.     NONE     NONE       RECOMMENDED
MED UNC.     NONE     RECOMMENDED REQUIRED
HIGH UNC.    RECOMMENDED REQUIRED REQUIRED
```

REQUIRED override (any one fires when the change materially affects behavior):

- Security/auth/authz/credentials/encryption, payments/financial logic,
  trading/risk logic incl. Section 9 list, persistent user data, DB migration,
  destructive FS ops, production deploy, irreversible migration.
- HIGH impact + (IRREVERSIBLE or DIFFICULT_TO_REVERSE).
- Safety-critical conflicting evidence; safety-critical repeated failure.
- Trading rule (Section 9) behavior-changing risk change.

Do NOT trigger on directory names alone; evaluate actual behavioral impact.

## 6. RECOMMENDED rules (non-exhaustive)

- 3+ genuinely viable architectures with long-term consequences.
- Moderate uncertainty + moderate/high impact; conflicting evidence (non-safety).
- Large cross-system change; performance/external-API uncertainty with impact.
- Repeated failure at threshold on non-safety system.
- Adversarial review: TIDOS has a preferred design but viable alternatives
  remain (prompt advisors to falsify, not agree).
- Gated experiment that is isolated, flagged, rollback-safe is at most
  RECOMMENDED (trading-risk experiments still follow Section 9).

## 7. Manual request, scope, advisors, trading rules (v3.1 Chat-Channel Mode)

- Manual: `TIDOSCHORA` always consults, bypassing the matrix. Conceptually
  `manual_request == true -> CHORA`. Default UX is Chat-Channel: ask partner
  count (1..N) → ask each partner name (e.g. `CHATGPT`) + one perspective per
  partner → open one copyable channel per partner (`SENT TO <NAME>:` /
  `RECEIVED FROM <NAME>:`). Turn-0 contract enforces replies ALWAYS in one
  single md fenced box starting with `<NAME>:`.
- Scope: every CHORA start defines a narrow consultation question with
  verified constraints, repository evidence, known risks, and the exact
  decision required. Never "review my whole project". One scope shared across
  all partner channels in the session. Minimal pointers only (paths +
  constraints + risks, no full code / no secrets).
- Advisor selection: suggest perspectives by problem type (Architecture,
  Security, Performance, Algorithm/Math, Quantitative/Risk, QA/Validation)
  and encourage complementary multi-advisor coverage. User chooses models
  and count; do not manufacture disagreement. Partner name is the channel
  label (`<NAME>`); perspective is the lens (`prompts/chora/perspectives.md`).
- Trading systems: trade entry/rejection, risk limits, stake sizing,
  martingale, drawdown protection, EV, payout filters, execution safety,
  backtest/live parity, empirical learning are HIGH impact. Behavior-changing
  live-trading changes -> REQUIRED. Purely behavior-neutral logging/format /
  read-only telemetry/tests-without-production-change stay NONE.
- Read-only measurement (counters, telemetry, exports, logs, metrics,
  diagnostics) is NONE unless it alters production behavior, persistence,
  security, or performance materially (MEASURE FIRST preserved).
- Consultation value over frequency: recommend only when expected
  risk-reduction + quality-gain + uncertainty-reduction exceeds user/time cost.
  Declined RECOMMENDED records `user_action: DECLINED` and stays silent on
  the same fingerprint.

## 8. Machine-readable explanation, UX, memory, persistence

Every non-NONE evaluation emits:

```yaml
chora_trigger:
  decision: RECOMMENDED  # or REQUIRED
  reasons: [MULTIPLE_VALID_ARCHITECTURES, HIGH_CHANGE_IMPACT]
  evidence: ["3 viable approaches identified", "4 modules affected"]
  risk: MEDIUM
  uncertainty: MEDIUM
  reversibility: PARTIALLY_REVERSIBLE
```

UX:

```text
==============================
CHORA RECOMMENDED
==============================
Reason: <reasons + evidence>
Risk / Uncertainty / Reversibility: <levels>
Recommended perspectives: Architecture, Adversarial review
Start CHORA? [Y/N]
```

```text
==============================
CHORA REQUIRED
==============================
Reason: <high-risk subsystem + material behavior change>
TIDOS will not implement this decision until external review
has been completed and verified.
Starting CHORA...
```

Memory (history + outcome, current repo evidence always wins over history):

```yaml
chora_trigger_history: {task, trigger_decision, reasons, evidence, user_action,
  consultation_completed, final_decision, validation_result}
chora_outcome: {decision_changed, useful, risks_identified, claims_verified,
  claims_rejected, implementation_result}
```

Persistence/dedup: fingerprint = task objective + files + scope + options +
constraints. Same fingerprint + no material change -> no auto re-trigger.
REQUIRED state persists across restarts/sessions via existing session/memory
mechanisms until the review completes; no silent override. Consult
`scripts/verify_chora_trigger.ps1` for the executable mirror of these rules.


