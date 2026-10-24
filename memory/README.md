# TIDOS User Memory

**Your memory lives in `~/.tidos/memory/` — private, outside every repository.**
The files in this folder are only empty templates, so personal data is never published to GitHub.

Rule for every spec and agent: a path written `memory/<FILE>.md` anywhere in TIDOS means
`~/.tidos/memory/<FILE>.md`. Read and write it there.

| File | Holds |
|---|---|
| `USER_PROFILE.md` | Who the user is: role, domains, languages, daily tools |
| `PREFERENCES.md` | Explicit directives: style, workflow, always / never |
| `PATTERNS.md` | Reusable patterns validated in the user's projects (2+ uses) |
| `LESSONS.md` | Post-mortems: issue, root cause, resolution, lesson, evidence |
| `BEST_PRACTICES.md` | Practices that proved themselves in real projects |
| `PROJECT_HISTORY.md` | Milestones and decisions per project |

START TIDOS migrates automatically: any personal content found in this folder is copied to `~/.tidos/memory/`
(never overwriting what is there) and the repository copy is reset to its template.

Privacy: never store credentials, tokens, passwords or client data in memory.
