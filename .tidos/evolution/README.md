# TIDOS Evolution Layer Specification (v1.1)

The **TIDOS Evolution Layer** (`.tidos/evolution/`) separates the immutable TIDOS Operating System kernel from dynamic project learnings, user preferences, pattern libraries, and framework suggestions.

---

## Evolution Layer Components

| File | Purpose | Update Trigger |
| :--- | :--- | :--- |
| `LEARNINGS.md` | Post-mortem root cause analysis, mistake prevention rules, and success records. | Post-task evaluation |
| `PATTERNS.md` | Reused solution templates, DTO mappers, and UI widget blueprints. | Verified solution reuse |
| `BEST_PRACTICES.md` | Empirically validated engineering practices with trade-offs. | Continuous observation |
| `METHODOLOGY.md` | User work preferences, coding style, review depth, and workflow habits. | Consistent user behavior |
| `PROJECT_HISTORY.md` | Historical record of completed sessions, major decisions, and milestones. | End of work session |
| `PROJECT_PROFILE.md` | Domain profile, architecture invariants, and active project metadata. | Project initialization |
| `USER_PREFERENCES.md` | Explicit owner choices for styling, tooling, docs, and communication. | User preference directive |
| `SUGGESTIONS.md` | Non-invasive framework enhancement proposals awaiting user review. | OS improvement discovery |
| `APPROVED.md` | User-approved TIDOS upgrade proposals ready for application. | User explicit approval |
| `REJECTED.md` | Rejected proposals preserved to prevent repeated suggestions. | User explicit rejection |
| `ROADMAP.md` | Evolution roadmap for project intelligence and TIDOS upgrades. | Milestone planning |
| `VERSION_HISTORY.md` | SemVer log of TIDOS OS and Evolution Layer releases. | Version release sign-off |

---

## Operating Principle

```
INVARIANT: The TIDOS Operating System (.tidos/kernel.md, workflow.md, roles.md, etc.) 
           is FROZEN and read-only. 
           All dynamic observations, patterns, and suggestions are isolated in .tidos/evolution/.
```
