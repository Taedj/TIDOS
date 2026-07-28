# TIDOS Learning Engine Specification (v3.0)

The **TIDOS Learning Engine** (`learning_engine.md`) defines the continuous self-improvement lifecycle for AI operations.

---

## 1. Core Learning Invariants

```
INVARIANT 1: No feature implementation, refactoring task, or bug fix is complete 
             until a Learning Audit has been conducted.
INVARIANT 2: System files in core/, engines/, personas/, rules/, etc. are PROTECTED. 
             All learnings and patterns are stored strictly in memory/ and evolution/.
```

---

## 2. Learning Output Routing

- **Post-Mortem & Mistake Analysis** -> Appended to `memory/LESSONS.md`
- **Reused Code Blueprints** -> Promoted to `memory/PATTERNS.md` (2+ reuse rule)
- **Validated Engineering Practices** -> Added to `memory/BEST_PRACTICES.md`
- **Observed User Habits** -> Recorded in `memory/METHODOLOGY.md` (3+ occurrence rule)
- **Explicit User Directives** -> Recorded in `memory/PREFERENCES.md` & `memory/USER_PROFILE.md`
- **TIDOS OS Improvement Proposals** -> Appended to `evolution/SUGGESTIONS.md` (Never mutate OS directly)
