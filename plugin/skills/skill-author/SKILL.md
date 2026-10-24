---
name: skill-author
description: Write a new TIDOS/Claude skill (SKILL.md) from a pattern that worked several times: trigger description, short procedure, checks. Use when the same kind of task keeps coming back.
---

# Skill author
1. **Evidence first**: the pattern succeeded at least 3 times (see playbooks via `tidos_recall`).
2. **Description = trigger**: what it does + when to use it, with the words users actually say.
3. **Body**: numbered procedure, concrete commands and checks, the traps to avoid. Under ~60 lines. Generic
   know-how only - project specifics belong in private playbooks.
4. **Folder**: `.claude/skills/<kebab-name>/SKILL.md` with `name` and `description` front matter.
5. **Validate** (`claude plugin validate` for the plugin copy) and try it on a real request.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
