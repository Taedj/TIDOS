---
name: db-migration
description: Change a database or data schema safely (SQL, SQLite, Firestore documents): backward-compatible steps, backup, verify, rollback plan. Use before any schema or data change.
---

# Database / schema migration
1. **Backup or export first**, and confirm with the user before touching production data.
2. **Expand, migrate, contract**: add new fields/tables (old code still works) -> backfill/migrate data ->
   switch reads/writes -> remove the old field later.
3. **Idempotent scripts**: safe to re-run; log counts (rows/documents read, changed, skipped, failed).
4. **Dry run** on a copy or with a `--dry-run` flag; compare counts before writing.
5. **Verify** after: counts match, spot-check records, app works on old and new data.
6. **Rollback plan** written down before running. Firestore: mind read/write costs and batch limits (500).

---
With the TIDOS MCP server: `tidos_recall` for what was learned in this project, `tidos_verify` to run the checks. Report: what changed, the check output, and anything still unverified.
