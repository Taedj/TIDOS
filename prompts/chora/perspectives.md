# CHORA Advisor Perspectives (v3.1 Chat-Channel)

One perspective per named partner per session (Chat-Channel Mode). Combine
complementarily; the user chooses names, models, and count. Each lens inherits
the base falsification mandate + strict single-box reply (`<NAME>:`).

- **Architecture**: Module boundaries, SOLID, public API contracts, Clean
  Architecture layers (`rules/architecture_rules.md`), reversibility,
  migration cost. Ask: what breaks at the boundaries?
- **Security**: Zero-trust input handling, secret isolation, auth/authz, RLS,
  least privilege (`rules/security_rules.md` + Quality Gate 4). Ask: what is
  the exploit if this claim is wrong?
- **Performance**: Latency, memory, I/O, query bounds, async discipline
  (Quality Gate 5). Ask: what measurement would disprove the estimate?
- **Algorithm / Math**: Correctness, edge cases, complexity, EV/payout-style
  reasoning where relevant. Ask: what counterexample breaks it?
- **Quantitative / Risk**: Stake sizing, drawdown, exposure, backtest/live
  parity, empirical discipline. Ask: what live behavior diverges from the model?
- **QA / Validation**: Testability, coverage of business logic and mappers,
  regression risk (Quality Gate 7). Ask: what test is missing?
- **Adversarial**: Steelman the weakest option; attack the preferred one.
  Ask: what is TIDOS most likely wrong about, and what is the cheapest
  falsifying check?

Suggested mapping from trigger reasons: architectural complexity or multiple
architectures -> Architecture + Adversarial; security impact -> Security +
Adversarial; performance uncertainty -> Performance + QA; trading/financial
impact -> Quantitative/Risk + Adversarial; repeated failure or conflicting
evidence -> Adversarial + QA.
