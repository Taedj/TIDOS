---
description: TIDOS end-to-end for one request - plan, implement, review, verify, learn
argument-hint: <what you want done>
---

Run the TIDOS loop for this request: $ARGUMENTS

1. **Context** - if the TIDOS MCP tools exist, call `tidos_guide` with the request and the project directory;
   otherwise run `python -I <TIDOS>/tidos_session/__main__.py guide "<request>"`. Follow its "define done" step.
2. **Plan** - for anything beyond a one-line change, use the `tidos-architect` subagent and show the plan briefly.
3. **Implement** - make the change yourself in small steps (read before edit).
4. **Verify** - use the `tidos-tester` subagent (or `tidos_verify`) to run the checks; fix until they pass.
5. **Review** - use the `tidos-reviewer` subagent on the diff; fix blocking findings, then re-verify.
6. **Learn** - if this was a strong-model session, leave one piece of advice for weaker models with `tidos_note`
   (or `python -I <TIDOS>/tidos_learn/__main__.py note --project <name> "<advice>"`).
7. **Report** - what changed (files), check output, review result, anything left UNVERIFIED.
