---
name: perf-profile
description: Find and fix a performance problem with measurements, not guesses. Use for slow screens, slow queries, high CPU/memory, jank.
---

# Performance profiling
1. **Measure first**: a repeatable scenario + a number (ms, fps, MB, query count). Write the baseline down.
2. **Profile** with the platform tool (Flutter DevTools, Chrome performance tab, `cProfile`/`py-spy`, query
   EXPLAIN, Firestore usage tab) to find where the time actually goes.
3. **Fix the top hotspot only** (N+1 queries, work in build/loops, missing index, unbounded reads, sync I/O on
   the UI thread).
4. **Measure again** with the same scenario. Keep the change only if the number improved.
5. Check correctness (tests) and cost (e.g. Firestore reads/writes) did not get worse.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
