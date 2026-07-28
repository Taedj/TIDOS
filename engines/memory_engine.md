# TIDOS Memory Engine Specification (v3.0)

The **TIDOS Memory Engine** (`memory_engine.md`) governs context window retention, project memory persistence, and cross-session AI model continuity.

---

## 1. 4-Tier Memory Architecture

```
+-----------------------------------------------------------------------+
| 1. WORKING MEMORY (Ephemeral Context Window / Active Session State)   |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 2. PROJECT MEMORY (`PROJECT_MEMORY.md` & Root Project Artifacts)     |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 3. INSTITUTIONAL MEMORY (`memory/` Profile, History, Patterns, etc.)  |
+-----------------------------------------------------------------------+
                                  |
                                  v
+-----------------------------------------------------------------------+
| 4. EVOLUTION LAYER (`evolution/` Suggestions, Approved Upgrades)     |
+-----------------------------------------------------------------------+
```

---

## 2. Memory Tier Details

- **Tier 1 (Working Memory)**: Active conversation window; managed dynamically during a session.
- **Tier 2 (Project Memory)**: Target workspace root files (`PROJECT_MEMORY.md`, `CHANGELOG.md`, `TASKS.md`, `DECISIONS.md`).
- **Tier 3 (Institutional Memory)**: Evolving project intelligence in `memory/` (`USER_PROFILE.md`, `PROJECT_HISTORY.md`, `PREFERENCES.md`, `PATTERNS.md`, `LESSONS.md`, `BEST_PRACTICES.md`).
- **Tier 4 (Evolution Layer)**: OS upgrade proposals in `evolution/` (`SUGGESTIONS.md`, `APPROVED.md`, `REJECTED.md`, `ROADMAP.md`, `VERSION_HISTORY.md`).
