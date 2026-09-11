# CHORA Session Record

- **Session ID**: `[chora-YYYYMMDD-NNN]`
- **Status**: `[OPEN / AWAITING_RESPONSES / VERIFYING / SYNTHESIZED / DECIDED / CLOSED]`
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

## 2. Advisors

| ID | Perspective | Model label | Prompt hash | Status |
|----|-------------|-------------|-------------|--------|
| `[A1]` | `[Architecture]` | `[user-chosen model]` | `[sha]` | `[PENDING / RESPONDED / MISSING]` |

## 3. Links

- **Responses**: `[chora_response paths]`
- **Claims**: `[chora_claims path]`
- **Synthesis**: `[chora_synthesis path]`
- **ADR**: `[decisions.md ADR id]`
