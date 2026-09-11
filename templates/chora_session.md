# CHORA Session Record (v3.2 Chat-Channel)

- **Session ID**: `[chora-YYYYMMDD-NNN]`
- **Status**: `[OPEN / AWAITING_RESPONSES / VERIFYING / SYNTHESIZED / DECIDED / CLOSED]`
- **Mode**: `[chat-channel (default) / legacy-templates (deprecated)]`
- **Round**: `[1 / 2]`
- **Trigger ref**: `[trigger report path + decision + reasons]`
- **Fingerprint**: `[objective + files + scope + options + constraints]`
- **Created / Closed**: `[YYYY-MM-DD / YYYY-MM-DD]`

## 1. Locked scope

- **Question**: `[one focused question]`
- **Decision required**: `[Option A vs B vs ...]`
- **Constraints**: `[verified limits]`
- **Evidence refs**: `[file paths, test names, measurements — no secrets]`
- **Risks**: `[known risks]`
- **Out of scope**: `[excluded topics]`

## 2. Advisors / Partners (Chat-Channel)

| ID | Partner name | Perspective | Model label | Prompt hash | Channel | Status |
|----|--------------|-------------|-------------|-------------|---------|--------|
| `[A1]` | `[CHATGPT]` | `[Architecture]` | `[user-chosen model]` | `[sha]` | `[SENT TO <NAME> / RECEIVED FROM <NAME>]` | `[PENDING / RESPONDED / MISSING]` |

Legacy `Advisor ID / Model label` fields retained for compat; `Partner name`
is the channel label (`<NAME>`).

## 3. Links

- **Responses**: `[chora_response paths]`
- **Claims**: `[chora_claims path]`
- **Synthesis**: `[chora_synthesis path]`
- **ADR**: `[decisions.md ADR id]`

## 4. Turn ledger (v3.2 bounded)

| Turn | Direction | Partner | Chars | Validation | Summary |
|------|-----------|---------|-------|------------|---------|
| `[T0]` | `[SENT TO <NAME>]` | `[<NAME>]` | `[n <= 8000]` | `[VALID / MALFORMED]` | `[one-line pointer summary]` |

Overflow policy `truncate-and-summarize`; full history never replayed verbatim.
Preserve session/participant/direction/claims/decision for audit.
