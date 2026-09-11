# CHORA Claims & Verification

- **Session ID**: `[chora-YYYYMMDD-NNN]`
- **Round**: `[1 / 2]`

Remember: `advisor statement != verified project fact`.

| Claim | Advisor | Statement | Kind | Touches | Authority | Method / Command | Result | Status |
|-------|---------|-----------|------|---------|-----------|------------------|--------|--------|
| `[C1]` | `[A1]` | `[one assertion]` | `[fact-checkable / testable / opinion / unsafe-if-wrong]` | `[files]` | `[repo-code / tests / runtime / backtest / docs / memory / advisor-only / assumption]` | `[inspection / test cmd / measurement]` | `[evidence summary]` | `[PENDING / VERIFIED / REJECTED / UNVERIFIABLE / SUPERSEDED]` |

## Rules

- Verify in authority order; stop at first decisive level.
- Security claims also pass Gate 4 + `rules/security_rules.md`.
- `advisor-only` / `assumption` authority can never yield `VERIFIED`.
- Log every verification command (cf. `templates/review_report.md` §3).
