---
name: refactor-safely
description: Restructure code without changing behavior: checks before and after, small steps, public API kept. Use for renames, extractions, moving code, cleanup.
---

# Safe refactor
1. **Baseline**: run the checks first and save the result. No tests on the code you will touch? Write
   characterization tests that capture current behavior first.
2. **One mechanical step at a time** (rename, extract, move). Run the checks after each step.
3. **Keep public names and signatures**. If a rename is required, keep the old name as a deprecated alias.
4. **Find every caller** with a search before changing a signature (code, tests, docs, scripts, configs).
5. **No behavior changes mixed in**. Bugs you notice: write them down, fix them in a separate change.
6. **Compare**: same check results as the baseline; diff reads as pure restructuring.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
