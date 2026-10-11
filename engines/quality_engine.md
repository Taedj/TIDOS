# TIDOS Quality Engine Specification (v4.0)

The **TIDOS Quality Engine** (`quality_engine.md`) defines the mandatory pre-execution cognitive gates, post-execution verification procedures, and Master Definition of Done (DoD) governing all code modifications within a TIDOS-connected workspace.

---

## 0. Pre-Execution Cognitive Gate (Gate 0: Model Equalizer Invariant)

To guarantee that small, lightweight, or quantized models execute with the precision of frontier models, **no file mutation is permitted** until Gate 0 has been satisfied in the reasoning trace:

```text
INVARIANT: The agent must NEVER mutate workspace code based on memory or assumptions.
           Gate 0 must be validated empirically before touching any file.
```

### Gate 0 Verification Requirements:
1. **Empirical Grounding**: The agent must inspect source files via `view_file` or `grep_search` and cite exact file paths and line ranges (`file:///path/to/file#L10-L30`). Hallucinated or assumed file structures are strictly forbidden.
2. **Negative Constraint Definition**: The agent must explicitly state what the change will **NOT** alter (e.g., *"Will not change public method signature; will not modify database schema; will not import external libraries"*).
3. **Atomic Decomposition**: Any change exceeding 30 lines must be decomposed into sequential micro-steps.
4. **Pre-Change Verification Plan**: The agent must identify the exact terminal command (compiler, test, or linter) that will confirm correctness after modification.

---

## 1. Multi-Dimensional Quality Gates (Gates 1–8)

- **Gate 1: Architecture & SOLID Invariants**: Strict Clean Architecture layer separation (`Presentation` -> `Domain` <- `Data` -> `Core`). Dependencies injected via interfaces, single responsibility per module.
- **Gate 2: Code Hygiene & Readability**: Standard naming conventions, zero dead code, zero code duplication, zero lint warnings.
- **Gate 3: Error Handling & Logging**: Typed failure propagation, non-silent error trapping, structured logging, zero hardcoded secrets in logs.
- **Gate 4: Security & Vulnerability Mitigation**: Zero-trust input sanitization, isolated secrets in `.env`, clean dependency CVE health.
- **Gate 5: Performance & Resource Efficiency**: Async non-blocking execution, zero memory leaks, Firestore `.limit()` bounds, Supabase RLS policies.
- **Gate 6: UI, UX & Accessibility Standards**: Design system alignment, responsive layout, WCAG 2.1 AA contrast ratio (4.5:1 min) and semantic tags.
- **Gate 7: Automated Testing**: Passing unit, integration, and regression test suites.
- **Gate 8: Documentation Sync**: Inline docstrings, synchronized `CHANGELOG.md`, `PROJECT_MEMORY.md`, and `TASKS.md`.

---

## 2. Master Definition of Done (DoD)

A task is officially **DONE** when and only when all 11 conditions are true:

```
[✓] 0. Gate 0 Pre-Execution Grounding verified with empirical file citations.
[✓] 1. Implementation fully satisfies user prompt requirements.
[✓] 2. Zero compilation, build, or syntax errors verified via terminal execution.
[✓] 3. Zero static analyzer or lint warnings.
[✓] 4. All automated unit and integration tests pass cleanly with exit code 0.
[✓] 5. Clean Architecture layer separation strictly preserved.
[✓] 6. Security, sanitization, and secret isolation verified.
[✓] 7. Performance and database query bounds (Firestore/Postgres) met.
[✓] 8. UI/UX responsive and WCAG 2.1 AA accessibility compliant.
[✓] 9. Relevant project documentation (CHANGELOG, memory) updated.
[✓] 10. Self-review checklist completed with zero open TODO items.
```
