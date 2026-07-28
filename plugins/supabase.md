# TIDOS Plugin: Supabase & PostgreSQL Backend (v3.0)

## 1. Detection Rules
- **Signature Directory / Files**: `supabase/config.toml`, `supabase/migrations/`
- **Dependencies**: `@supabase/supabase-js`, `supabase_flutter`

## 2. Initialization Steps
- Verify Supabase CLI installation (`supabase status`).
- Check database migration sync state.

## 3. Documentation to Generate
- `SUPABASE_SCHEMA.md`: Document ER diagram, SQL migrations, and RLS policies.

## 4. Best Practices
- Enable Row Level Security (RLS) on **every** table without exception.
- Use `auth.uid()` in RLS policies for tenant data isolation.

## 5. Coding Standards
- Write modular, idempotent SQL migration files (`YYYYMMDDHHMMSS_name.sql`).
- Encapsulate complex relational queries inside database functions (`PL/pgSQL`).

## 6. Review & Quality Rules
- Validate zero tables with `ALTER TABLE name DISABLE ROW LEVEL SECURITY;`.
- Check Realtime channel filters to prevent socket memory bloat.

## 7. Research Topics
- Supabase Edge Functions (Deno), pgvector embeddings, Supabase Auth SSR middleware.
