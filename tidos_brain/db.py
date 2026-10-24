"""TIDOS brain storage: SQLite database living OUTSIDE any repository.

Default location: ~/.tidos/brain.db (override with TIDOS_BRAIN_DB).
The update gate never touches it, and it is never committed or synced.
"""
import os
import sqlite3

SCHEMA_VERSION = 1

# Version 1: traces (sessions/tasks/tool_calls/verifications/live_events) are
# filled now; playbooks/facts/models/evals/xp_events/security_log are created
# empty for later phases so the schema stays stable.
MIGRATIONS = {
    1: """
    CREATE TABLE sessions (
        id          TEXT PRIMARY KEY,
        source      TEXT NOT NULL,              -- claude-code | gemini-cli | opencode | api
        model       TEXT,
        cwd         TEXT,
        project     TEXT,
        git_branch  TEXT,
        title       TEXT,
        transcript  TEXT,
        started_at  TEXT,
        ended_at    TEXT,
        imported_at TEXT
    );
    CREATE TABLE tasks (
        id            INTEGER PRIMARY KEY,
        session_id    TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
        seq           INTEGER NOT NULL,          -- order inside the session
        prompt        TEXT,                      -- sanitized + truncated
        model         TEXT,
        started_at    TEXT,
        ended_at      TEXT,
        task_type     TEXT,                      -- filled by the classifier (Phase 5)
        stack         TEXT,
        tool_calls    INTEGER DEFAULT 0,
        tool_errors   INTEGER DEFAULT 0,
        files_edited  INTEGER DEFAULT 0,
        verify_runs   INTEGER DEFAULT 0,
        verify_passed INTEGER,                   -- NULL = never verified, 0/1 = last verify result
        corrected     INTEGER DEFAULT 0,         -- next user prompt was a correction
        input_tokens  INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        score         REAL,
        outcome       TEXT,                      -- success | failure | unknown
        UNIQUE (session_id, seq)
    );
    CREATE TABLE tool_calls (
        id         INTEGER PRIMARY KEY,
        task_id    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        ts         TEXT,
        tool       TEXT NOT NULL,
        kind       TEXT,                         -- read | search | edit | exec | delegate | web | other
        summary    TEXT,                         -- sanitized command / path / pattern
        is_error   INTEGER DEFAULT 0
    );
    CREATE TABLE verifications (
        id         INTEGER PRIMARY KEY,
        task_id    INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
        ts         TEXT,
        command    TEXT,
        passed     INTEGER NOT NULL
    );
    CREATE TABLE live_events (
        id          INTEGER PRIMARY KEY,
        ts          TEXT NOT NULL,
        session_id  TEXT,
        source      TEXT,
        event       TEXT NOT NULL,               -- SessionStart | UserPromptSubmit | PostToolUse | Stop | SessionEnd
        tool        TEXT,
        summary     TEXT,
        is_error    INTEGER DEFAULT 0,
        cwd         TEXT
    );
    CREATE TABLE playbooks (
        id           INTEGER PRIMARY KEY,
        task_type    TEXT NOT NULL,
        stack        TEXT,
        path         TEXT,
        source_models TEXT,
        uses         INTEGER DEFAULT 0,
        successes    INTEGER DEFAULT 0,
        rank         TEXT DEFAULT 'E',
        status       TEXT DEFAULT 'draft',       -- draft | active | archived
        created_at   TEXT,
        updated_at   TEXT
    );
    CREATE TABLE facts (
        id          INTEGER PRIMARY KEY,
        kind        TEXT NOT NULL,               -- lesson | preference | pattern | best_practice
        text        TEXT NOT NULL,
        trigger     TEXT,
        confidence  REAL DEFAULT 0.5,
        uses        INTEGER DEFAULT 0,
        pinned      INTEGER DEFAULT 0,
        created_at  TEXT,
        last_used_at TEXT
    );
    CREATE TABLE models (
        name        TEXT PRIMARY KEY,
        provider    TEXT,
        tier        TEXT                          -- small | medium | frontier
    );
    CREATE TABLE evals (
        id          INTEGER PRIMARY KEY,
        suite       TEXT NOT NULL,
        task_name   TEXT NOT NULL,
        model       TEXT,
        with_tidos  INTEGER,
        passed      INTEGER,
        duration_s  REAL,
        cost_usd    REAL,
        run_at      TEXT
    );
    CREATE TABLE xp_events (
        id          INTEGER PRIMARY KEY,
        ts          TEXT NOT NULL,
        domain      TEXT,
        delta       INTEGER NOT NULL,
        reason      TEXT,
        task_id     INTEGER REFERENCES tasks(id) ON DELETE SET NULL
    );
    CREATE TABLE security_log (
        id          INTEGER PRIMARY KEY,
        ts          TEXT NOT NULL,
        event       TEXT NOT NULL,               -- login_ok | login_fail | lockout | sanitizer_block | update_refused
        detail      TEXT
    );
    CREATE INDEX idx_tasks_session ON tasks(session_id);
    CREATE INDEX idx_tool_calls_task ON tool_calls(task_id);
    CREATE INDEX idx_live_events_ts ON live_events(ts);
    """,
}


def default_path():
    return os.environ.get("TIDOS_BRAIN_DB") or os.path.join(os.path.expanduser("~"), ".tidos", "brain.db")


def connect(path=None):
    """Open (and migrate) the brain database."""
    path = path or default_path()
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")  # hooks and the dashboard read/write concurrently
    migrate(conn)
    return conn


def migrate(conn):
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    for version in range(current + 1, SCHEMA_VERSION + 1):
        with conn:
            conn.executescript(MIGRATIONS[version])
            conn.execute("PRAGMA user_version = %d" % version)
    return conn
