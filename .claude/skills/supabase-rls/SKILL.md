---
name: supabase-rls
description: Supabase/Postgres row-level security: enable RLS, write policies per role and operation, test them. Use when adding tables or changing data access in Supabase.
---

# Supabase RLS
1. **Enable RLS on every table** exposed to clients (`alter table ... enable row level security`).
2. **Policies per operation** (select/insert/update/delete) using `auth.uid()`; `with check` for writes.
3. **Never use the service_role key in client code**; it bypasses RLS.
4. **Test** as anon, as owner and as another user (SQL with `set role` / `request.jwt.claims`, or API tests).
5. Index columns used in policies (e.g. `user_id`) to keep them fast.

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
