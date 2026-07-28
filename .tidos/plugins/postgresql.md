# TIDOS Plugin: PostgreSQL Relational Database

## 1. Detection Rules
- **Signature Files**: `schema.sql`, `migrations/`, `prisma/schema.prisma` containing `postgresql`
- **Keywords**: `postgres`, `pg`, `psql`

## 2. Initialization Steps
- Verify database connection config.
- Check active database migration state.

## 3. Documentation to Generate
- `DATABASE_SCHEMA.md`: Document ER diagrams, foreign key relationships, and index topologies.

## 4. Best Practices
- Maintain 3NF relational normalization for core business tables.
- Add B-tree composite indexes on frequently filtered/joined foreign key columns.

## 5. Coding Standards
- Write idempotent, versioned SQL migration scripts (`V1__initial.sql`).
- Use parameterized queries or ORM mappers to prevent SQL injection vulnerabilities.

## 6. Review & Quality Rules
- Reject unindexed full-table scan queries on production collections.
- Verify foreign key constraints with explicit `ON DELETE` cascade / restrict rules.

## 7. Research Topics
- PostgreSQL 16 performance features, `pgvector` embedding indexes, Connection pooling with PgBouncer.
