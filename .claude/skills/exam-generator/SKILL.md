---
name: exam-generator
description: Generate exams or quizzes with answer keys and automatic verification: coverage of objectives, unambiguous questions, per-student variants, export formats. Use for tests, quizzes, Moodle GIFT exports.
---

# Exam generator
1. **Blueprint**: learning objectives x difficulty; count questions per objective.
2. **Questions**: one unambiguous correct answer (or an explicit list of accepted answers); plausible distractors;
   no "all of the above" unless intended.
3. **Answer key generated from the same source** as the questions (never typed separately).
4. **Variants** (shuffled order, numeric parameters): compute each variant's key by code and verify it.
5. **Verify**: every question has exactly one key; re-solve numeric questions by code; spell-check; check the
   export parses back (e.g. GIFT/CSV round-trip).
6. Print/export formats tested with the target tool (Moodle import preview, PDF render).

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
