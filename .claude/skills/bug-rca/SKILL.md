---
name: bug-rca
description: Root-cause a bug: reproduce, isolate, find the cause, fix it, and lock it with a regression test. Use for crashes, wrong results, flaky behavior, 'it does not work'.
---

# Bug root-cause analysis
1. **Reproduce** with exact steps or a failing test/script. No reproduction = no fix yet: ask for steps, logs, data.
2. **Read the error** fully (message, stack trace, line). Open the code at that line and its callers.
3. **Isolate**: smallest input that fails; compare with one that works. If it used to work, `git log -p` /
   `git bisect` on the suspect files.
4. **State the root cause in one sentence** (why it happens, not where it shows).
5. **Fix the cause**, not the symptom (no try/except that hides it, no special case for the one input).
6. **Regression test**: the reproduction becomes a test that fails before the fix and passes after.
7. **Check neighbors**: same pattern elsewhere? (`grep` for it.)
Report: symptom, root cause, fix, test, other places checked.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
