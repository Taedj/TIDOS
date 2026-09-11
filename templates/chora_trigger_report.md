# CHORA Trigger Evaluation Report

- **Date**: `[YYYY-MM-DD]`
- **Task**: `[Task objective]`
- **Decision fingerprint**: `[objective + files + scope + options + constraints]`
- **Evaluation point**: `[Task understanding / Plan / Pre-implementation / Post-failure / Post-regression / Pre-irreversible / Final decision]`

## 1. Engine decision

- **Decision**: `[NONE / RECOMMENDED / REQUIRED / MANUAL]`
- **Consultation started**: `[yes / no / pending user approval]`

```yaml
chora_trigger:
  decision: [NONE | RECOMMENDED | REQUIRED]
  reasons: [[REASON_CODE]]
  evidence: ["[Observable evidence]"]
  risk: [LOW | MEDIUM | HIGH]
  uncertainty: [LOW | MEDIUM | HIGH]
  reversibility: [REVERSIBLE | PARTIALLY_REVERSIBLE | DIFFICULT_TO_REVERSE | IRREVERSIBLE]
```

## 2. Signals observed

- **Impact**: `[LOW / MEDIUM / HIGH]` — `[why]`
- **Uncertainty**: `[LOW / MEDIUM / HIGH]` — `[observable condition only]`
- **Reversibility**: `[level]`
- **Viable options**: `[count and consequence]`
- **Failure history**: `[attempts versus threshold]`

## 3. User action and outcome

- **User action**: `[APPROVED / DECLINED / N-A]`
- **Consultation completed**: `[yes / no]`
- **Decision changed**: `[yes / no]`
- **Risks identified**: `[count]`
- **Claims verified / rejected**: `[n / m]`
- **Implementation result**: `[PASS / FAIL]`
