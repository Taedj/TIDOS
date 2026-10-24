---
name: memory-compactor
description: Clean up TIDOS memory: merge duplicate lessons, drop stale or wrong ones, keep it short and true. Use when memory files grow long or contradict each other.
---

# Memory compactor
Memory lives in `~/.tidos/memory/` (private).
1. Read all memory files; group entries about the same topic.
2. **Merge** duplicates into one entry with the strongest evidence; **delete** entries proven wrong or obsolete
   (check the code - memory can be outdated).
3. Keep each entry: rule, why, how to apply, evidence/date.
4. Never move private details into public files (skills, repo docs).
5. Show the user a summary of what was merged/removed before writing.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
