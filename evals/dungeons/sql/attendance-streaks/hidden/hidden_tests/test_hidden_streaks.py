import sqlite3
from pathlib import Path

SCHEMA = Path("school.sql").read_text(encoding="utf-8").split("INSERT")[0]

def run(rows):
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.executemany("INSERT INTO attendance VALUES (?,?,?)", rows)
    return conn.execute(Path("query.sql").read_text(encoding="utf-8")).fetchall()

def days(student, spec):
    return [(student, d, p) for d, p in spec]

def test_streaks():
    rows = (
        days(1, [("2026-01-01", 1), ("2026-01-02", 1), ("2026-01-03", 1), ("2026-01-04", 0),
                 ("2026-01-05", 1), ("2026-01-06", 1)])
        + days(2, [("2026-01-01", 1), ("2026-01-02", 1), ("2026-01-05", 1), ("2026-01-06", 1),
                   ("2026-01-07", 1)])                                   # missing 3-4 breaks it
        + days(3, [("2026-01-31", 1), ("2026-02-01", 1), ("2026-02-02", 1), ("2026-02-03", 1)])
        + days(4, [("2026-03-01", 1), ("2026-03-02", 1), ("2026-03-04", 1), ("2026-03-05", 1)])
        + days(5, [("2026-01-01", 0), ("2026-01-02", 0)])                  # never present
        + days(6, [("2026-05-10", 1)])
    )
    assert run(rows) == [(3, 4, "2026-01-31"), (1, 3, "2026-01-01"), (2, 3, "2026-01-05"),
                         (4, 2, "2026-03-01"), (6, 1, "2026-05-10")]

def test_unordered_inserts():
    rows = days(9, [("2026-06-03", 1), ("2026-06-01", 1), ("2026-06-02", 1)])
    assert run(rows) == [(9, 3, "2026-06-01")]
