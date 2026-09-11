# CHORA Comparison & Synthesis

- **Session ID**: `[chora-YYYYMMDD-NNN]`
- **Round**: `[1 / 2]`
- **Status**: `[SYNTHESIZED / DECIDED]`

## 1. Comparison (verified claims only)

- **Agreements**: `[claims all verified advisors support]`
- **Disagreements**: `[claim-level conflicts with evidence pointers]`
- **Gaps**: `[missing advisors, unverifiable claims, untested options]`

Advisor count never outweighs evidence weight.

## 2. TIDOS synthesis

- **Recommended option**: `[Option + why verified evidence wins]`
- **Rejected options**: `[Option + decisive evidence against]`
- **Vetoes applied**: `[Quality Gates / architecture / security invariants]`
- **Residual risks**: `[what remains uncertain]`

## 3. TIDOS decision

- **Chosen option**: `[Option]`
- **Rationale**: `[evidence-backed, authority-ordered]`
- **ADR ref**: `[decisions.md ADR id]`
- **Validation plan**: `[tests / measurements / review commands]`
- **Round 2**: `[not-needed / needed + narrowed question + new evidence required]`

## 4. Outcome (for memory digest)

```yaml
chora_outcome:
  decision_changed: [true | false]
  useful: [true | false]
  risks_identified: [n]
  claims_verified: [n]
  claims_rejected: [n]
  implementation_result: [PASS | FAIL]
```
