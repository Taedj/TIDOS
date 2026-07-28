# TIDOS + Supabase Integration Example

## Project Type
Full-stack application with Supabase PostgreSQL backend.

## TIDOS Connection

```bash
cd supabase_app
git submodule add https://github.com/tidjani/TIDOS.git .tidos
```

## Plugins Mounted

- `plugins/supabase.md` - Supabase specification
- `plugins/postgresql.md` - PostgreSQL schema design
- `plugins/react.md` or `plugins/nextjs.md` - Frontend framework

## Key Rules Applied

- Row Level Security (RLS) policies
- Database migrations with `supabase migration`
- Realtime subscription optimization
- Edge Functions for serverless logic

## Startup Report

```
Detected Stack: Supabase + React
Active Plugins: supabase.md, postgresql.md, react.md
```
