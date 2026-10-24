---
name: tdd-loop
description: Test-driven change loop: write a failing test for the behavior, make it pass with the smallest change, refactor, repeat. Use for new behavior or a bug that can be pinned by a test.
---

# TDD loop
1. **Pin the behavior.** Write ONE test for the next small piece of behavior, with exact expected values from the
   request (inputs, outputs, edge cases: empty, None/null, boundaries, invalid input).
2. **See it fail** for the right reason (assertion, not a typo or import error). If it passes, it tests nothing.
3. **Smallest change** that makes it pass. No extra features.
4. **Run the whole relevant suite**, not only the new test.
5. **Refactor** with the tests green; run them again.
6. Repeat until every requirement has a test.
Never: edit a test to make it pass, mark tests skipped, or call it done with a red suite.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
