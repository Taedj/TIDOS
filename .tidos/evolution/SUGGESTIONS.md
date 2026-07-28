# TIDOS Framework Improvement Suggestions

This file captures proposed improvements to the TIDOS Operating System itself. The agent **never modifies frozen OS files directly**. Instead, improvement ideas are appended here for user review.

---

## Suggestion Protocol

```
INVARIANT: Suggestions are PROPOSALS ONLY. 
           The Operating System is FROZEN and read-only.
           Changes are applied only when the user explicitly commands:
           "Upgrade TIDOS", "Update TIDOS", "Create TIDOS vX.X", or "Apply approved improvements."
```

---

## Suggestion Format

```markdown
### SUG-[NNN]: [Suggestion Title]

- **Date**: [YYYY-MM-DD]
- **Priority**: [Low | Medium | High | Critical]
- **Status**: [Proposed | Approved | Rejected | Applied]

#### Problem
[What limitation, gap, or friction exists in the current TIDOS OS.]

#### Proposed Solution
[Concrete description of the change or addition.]

#### Benefits
- [Benefit 1]
- [Benefit 2]

#### Risks
- [Risk or trade-off 1]

#### Affected Modules
- [List of .tidos/ files or folders impacted]

#### Estimated Impact
[Low | Medium | High — How much does this improve the framework?]

#### Recommended Version
[e.g., TIDOS v1.2.0]
```

---

## Suggestion Log

*No suggestions yet. Proposals will be appended here as TIDOS is used in real projects.*
