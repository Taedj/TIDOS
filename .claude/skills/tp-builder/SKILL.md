---
name: tp-builder
description: Build or transpose practical-work (TP) exercises with per-student variants and an auto-grading engine, verified for every variant. Use for teaching material with automatic grading.
---

# TP builder (per-student variants + auto-grading)
1. **Variants**: answers depend on a student variable (e.g. last digit D of the student id). Define the expected
   answer for EVERY value (D = 0..9) explicitly.
2. **Rule types**: check which grading rule types interpolate `{variables}` in your engine and which do not;
   use an interpolating type for variant-dependent text answers. Never assume.
3. **Verify by execution**: for each variant, feed the perfect answers -> full marks (e.g. 20/20 for D = 0..9),
   and feed known wrong answers ("traps") -> they must lose points.
4. **Transposing to another course/track**: scripted, asserted replacements (the old text must exist, structure
   counts unchanged), never a blind copy; then rerun the full verification.
5. Builder self-checks: slide/block counts, every question has a rule, no empty options.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
