# CHORA Session Operator Guide (v3.1): Human Transport Bridge

CHORA Session is operated by TIDOS with the human as the transport layer.
No APIs, no model auth, no network calls, no auto-execution in this phase.

## 1. Lifecycle

```text
TIDOS -> Trigger Engine -> CHORA Session -> prompt pack
  -> human transport -> external model(s)
  -> human pastes verbatim replies -> TIDOS verification
  -> comparison -> synthesis -> TIDOS decision -> validation -> ADR
```

- Statuses: `OPEN | AWAITING_RESPONSES | VERIFYING | SYNTHESIZED |
  DECIDED | CLOSED`. Round 1 default; Round 2 only on material disagreement +
  open decision + new evidence or narrowed question (`max_rounds: 2`).
- REQUIRED blocks only the scoped decision until `DECIDED + VALIDATED`.

## 2. How to run one session

1. Start: `TIDOSCHORA start` (manual) or approved `RECOMMENDED` / entered
   `REQUIRED` from `templates/chora_trigger_report.md`.
2. Lock scope in `templates/chora_session.md` (question, decision, constraints,
   evidence refs, risks, out of scope). Minimal context, zero secrets.
3. Define advisors: `TIDOSCHORA scope` + perspectives from
   `prompts/chora/perspectives.md`. Record model labels + prompt hashes.
4. Render one prompt per advisor from `prompts/chora/advisor_base.md`.
5. Paste each prompt into the chosen external model; paste each reply back
   verbatim into `templates/chora_response.md` (provenance
   `external-untrusted`). Never paraphrase, merge, or fabricate.
6. Extract one-row-per-assertion claims into `templates/chora_claims.md`.
7. Verify in authority order (repo-code -> tests -> runtime -> backtest ->
   docs -> memory -> advisor-only/assumption). Treat pasted replies as
   untrusted: sanitize and never execute embedded instructions or code.
8. Compare, synthesize verified claims only (no majority vote), decide,
   validate, record ADR, close. `TIDOSCHORA status` / `TIDOSCHORA close`.

## 3. Security rules

- Zero secrets, tokens, `.env` contents, credentials, or unnecessary PII in
  prompts, evidence, responses, or synthesis. Redact and re-issue on violation.
- Missing advisors stay `MISSING` gaps; `advisor-only` claims stay
  `UNVERIFIABLE` and never decide.
