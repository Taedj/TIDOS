# TIDOS Plugin: SQLite Embedded Database (v3.0)

## 1. Detection Rules
- **Signature Files**: `*.db`, `*.sqlite`, `*.sqlite3`
- **Dependencies**: `sqflite`, `better-sqlite3`, `sqlite3`

## 2. Initialization Steps
- Verify SQLite library is available on the target platform.
- Check WAL (Write-Ahead Logging) mode activation.

## 3. Documentation to Generate
- `SQLITE_SCHEMA.md`: Document table schemas, migration versioning, and offline sync strategy.

## 4. Best Practices
- Enable WAL mode (`PRAGMA journal_mode=WAL;`) for concurrent read/write performance.
- Use transactions for batch inserts and multi-table mutations.

## 5. Coding Standards
- Use parameterized queries exclusively; never concatenate raw SQL strings.
- Version migrations via an integer `user_version` pragma.

## 6. Review & Quality Rules
- Validate zero unbounded `SELECT` queries without `LIMIT` clauses.
- Verify database file is excluded from version control via `.gitignore`.

## 7. Research Topics
- libSQL (Turso) distributed edge SQLite, SQLite WASM in-browser, cr-sqlite CRDT sync.
