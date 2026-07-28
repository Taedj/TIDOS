# TIDOS Plugin: SQLite Embedded Database

## 1. Detection Rules
- **Signature Files**: `*.db`, `*.sqlite`, `*.sqlite3`
- **Dependencies**: `sqflite`, `sqlite3`, `better-sqlite3`

## 2. Initialization Steps
- Verify local database file path initialization.
- Check SQLite WAL (Write-Ahead Logging) mode status.

## 3. Documentation to Generate
- `SQLITE_SCHEMA.md`: Document local table schemas, PRAGMA flags, and migration steps.

## 4. Best Practices
- Enable Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) for concurrent read/write throughput.
- Enforce foreign keys explicitly (`PRAGMA foreign_keys = ON;`).

## 5. Coding Standards
- Wrap batch inserts or updates inside explicit transactions (`BEGIN TRANSACTION; ... COMMIT;`).
- Store timestamps in UTC ISO-8601 strings or Unix epoch integers.

## 6. Review & Quality Rules
- Validate zero unclosed database connection handles.
- Check schema migration version tracking table (`user_version` or `schema_migrations`).

## 7. Research Topics
- SQLite WASM for Web browsers, Turso libSQL distributed SQLite, Encrypted SQLite (SQLCipher).
