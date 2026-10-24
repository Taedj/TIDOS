# TIDOS Reusable Document Templates (`templates/`)

The `templates/` directory contains 18 protected, reusable Markdown document templates for TIDOS (v3.0).

---

## Directory Components

- [prd.md](/templates/prd.md): Product Requirements Document template.
- [architecture.md](/templates/architecture.md): Clean Architecture blueprint template.
- [roadmap.md](/templates/roadmap.md): Product milestone roadmap template.
- [tasks.md](/templates/tasks.md): Task execution backlog template.
- [changelog.md](/templates/changelog.md): Keep-a-Changelog template.
- [decisions.md](/templates/decisions.md): Architectural Decision Record (ADR) template.
- [lessons.md](/templates/lessons.md): RCA post-mortem log template.
- [project_memory.md](/templates/project_memory.md): High-level project state digest template.
- [review_report.md](/templates/review_report.md): Code self-review report template.
- [quality_report.md](/templates/quality_report.md): Master quality audit scorecard template.
- [release_checklist.md](/templates/release_checklist.md): Pre-deployment sign-off checklist template.
- [known_issues.md](/templates/known_issues.md): Defect and technical debt registry template.
- [pattern_library.md](/templates/pattern_library.md): Reusable code pattern template.
- [gptid_task.md](/templates/gptid_task.md): GPTID task dispatch template (objective, mode, context, constraints).
- [gptid_response.md](/templates/gptid_response.md): GPTID browser relay response intake template (untrusted source envelope).

---

## Protection Rule

```
INVARIANT: All files in templates/ are PROTECTED system files and read-only.
           Templates are generic and contain zero project-specific hardcoded data.
```
