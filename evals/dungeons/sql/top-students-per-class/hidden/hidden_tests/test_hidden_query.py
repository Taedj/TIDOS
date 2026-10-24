import sqlite3
from pathlib import Path

def run(setup):
    conn = sqlite3.connect(":memory:")
    conn.executescript(setup)
    return conn.execute(Path("query.sql").read_text(encoding="utf-8")).fetchall()

SCHEMA = Path("school.sql").read_text(encoding="utf-8").split("INSERT")[0]

def test_ties_and_dense_rank():
    rows = run(SCHEMA + """
        INSERT INTO students VALUES (1,'Ali','X'),(2,'Bea','X'),(3,'Cid','X'),(4,'Dan','X'),(5,'Eve','X'),
                                    (6,'Fay','Y'),(7,'Gus','Y');
        INSERT INTO grades VALUES (1,'m',18),(2,'m',16),(2,'m',16),(3,'m',16),(4,'m',14),(5,'m',10),
                                  (6,'m',12.333),(6,'m',12),(7,'m',5);
    """)
    assert rows == [("X", "Ali", 18.0, 1), ("X", "Bea", 16.0, 2), ("X", "Cid", 16.0, 2),
                    ("X", "Dan", 14.0, 3), ("Y", "Fay", 12.17, 1), ("Y", "Gus", 5.0, 2)]

def test_students_without_grades_excluded():
    rows = run(SCHEMA + """
        INSERT INTO students VALUES (1,'Ali','X'),(2,'Bob','X');
        INSERT INTO grades VALUES (1,'m',11);
    """)
    assert rows == [("X", "Ali", 11.0, 1)]
