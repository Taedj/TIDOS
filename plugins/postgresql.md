# TIDOS Plugin: PostgreSQL Database (v3.0)

## 1. Detection Rules
- **Signature Files**: `supabase/migrations/`, `prisma/schema.prisma`, `drizzle.config.ts`, `*.sql` migration files
- **Dependencies**: `pg`, `prisma`, `drizzle-orm`, `psycopg2`

## 2. Initialization Steps
- Verify PostgreSQL connection string configured in environment variables.
- Validate migration file sequence integrity.

## 3. Documentation to Generate
- `DATABASE_SCHEMA.md`: Document ER diagram, table schemas, indexes, and constraint rules.

## 4. Best Practices
- Design schemas in 3rd Normal Form (3NF) unless explicit denormalization is justified.
- Create indexes on all foreign keys and frequently filtered columns.

## 5. Coding Standards
- Use parameterized queries (`$1`, `$2`) exclusively; never inline user input into SQL strings.
- Write idempotent, timestamped migration files with clear `UP` / `DOWN` sections.

## 6. Review & Quality Rules
- Validate zero `SELECT *` queries in production code (specify explicit column lists).
- Verify `LIMIT` / pagination on all unbounded list queries.

## 7. Research Topics
- pgvector for AI embeddings, PostgreSQL 17 JSON improvements, connection pooling (PgBouncer / Supavisor).
