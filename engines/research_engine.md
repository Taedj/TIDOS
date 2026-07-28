# TIDOS Research Engine Specification (v3.0)

The **TIDOS Research Engine** (`research_engine.md`) defines the continuous technology evaluation and non-invasive proposal framework.

---

## 1. Advisory Research Invariant

```
INVARIANT: The Research Engine generates recommendations ONLY. 
           It must NEVER apply code, configuration, or dependency changes 
           automatically without explicit user instruction and approval.
```

---

## 2. 4-Factor Recommendation Assessment Framework

1. **BENEFIT**: Specific improvements to performance, developer velocity, maintainability, security, or UX.
2. **RISK**: Migration complexity, breaking changes, license restrictions, or dependency deprecation risks.
3. **COMPATIBILITY**: Alignment with host OS, target language versions, existing DB schemas, and Clean Architecture rules.
4. **ESTIMATED VALUE**: Quantified trade-off rating (Low / Medium / High / Game-Changer) balancing implementation effort against business impact.

Proposals are appended to `evolution/SUGGESTIONS.md`.
