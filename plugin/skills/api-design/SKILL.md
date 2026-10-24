---
name: api-design
description: Design or change an API (HTTP, function, class, Firestore schema) so it is clear, consistent and hard to misuse. Use before adding endpoints or public functions.
---

# API design
1. **Write the call site first**: how will callers use it? Names should read naturally there.
2. **Inputs**: required vs optional, types, validation, units. Reject bad input early with clear errors.
3. **Outputs and errors**: one consistent shape; error codes/messages callers can act on; no silent nulls.
4. **Consistency** with existing APIs in the project (naming, pagination, dates, ids, casing).
5. **Compatibility**: adding is safe; removing/renaming needs a deprecation path and a version note.
6. **Security**: who may call it, what data it exposes, rate limits, audit.
7. Document it with one example request/response and add tests for success + each error.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
