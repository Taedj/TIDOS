# CHORA Advisor Response Envelope (v3.1 Chat-Channel + legacy compat)

- **Session ID**: `[chora-YYYYMMDD-NNN]`
- **Advisor ID**: `[A1]` (legacy; maps to Partner below)
- **Partner name**: `[CHATGPT]` (chat-channel label `<NAME>`)
- **Channel turn**: `[SENT TO <NAME> / RECEIVED FROM <NAME>]`
- **Perspective**: `[Architecture / Security / ...]`
- **Model label**: `[user-chosen model]`
- **Round**: `[1 / 2]`
- **Received at**: `[YYYY-MM-DD HH:MM]`
- **Prompt hash**: `[sha of rendered prompt / SENT block]`
- **Provenance**: `external-untrusted (human transport, verbatim paste)`

## Raw response (verbatim, unedited — one single md box starting with <NAME>:)

```text
RECEIVED FROM <NAME>:
[<NAME>: ...single fenced box...]
```

Legacy envelope (`paste the external reply exactly as received`) remains
accepted; channel format is the v3.1 default.

## Intake notes

- **Complete against schema**: `[yes / no + missing sections]`
- **Secrets/PII detected**: `[none / redacted + re-issued]`
- **Claims forwarded**: `[C1..Cn to chora_claims]`
