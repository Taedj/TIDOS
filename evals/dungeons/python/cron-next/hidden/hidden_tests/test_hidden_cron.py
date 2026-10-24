from datetime import datetime
import pytest
from cron import next_run

@pytest.mark.parametrize("expr,after,expected", [
    ("*/15 * * * *", datetime(2026, 10, 24, 10, 7, 30), datetime(2026, 10, 24, 10, 15)),
    ("0 9 * * 1-5", datetime(2026, 10, 23, 18, 0), datetime(2026, 10, 26, 9, 0)),
    ("30 8 1 * *", datetime(2026, 10, 1, 8, 30), datetime(2026, 11, 1, 8, 30)),
    ("0 0 29 2 *", datetime(2026, 3, 1), datetime(2028, 2, 29)),
    ("0 12 13 * 5", datetime(2026, 10, 24), datetime(2026, 10, 30, 12, 0)),
    ("0 0 * * 7", datetime(2026, 10, 24), datetime(2026, 10, 25)),
    ("5,10-12/2 3 * * *", datetime(2026, 10, 24, 3, 10), datetime(2026, 10, 24, 3, 12)),
    ("0 22/1 * 12 *", datetime(2026, 10, 24), datetime(2026, 12, 1, 22, 0)),
    ("59 23 31 12 *", datetime(2026, 12, 31, 23, 59), datetime(2027, 12, 31, 23, 59)),
])
def test_next_run(expr, after, expected):
    assert next_run(expr, after) == expected

def test_dom_restricted_dow_star_needs_dom():
    assert next_run("0 0 13 * *", datetime(2026, 10, 24)) == datetime(2026, 11, 13)

@pytest.mark.parametrize("bad", ["60 * * * *", "* * *", "*/0 * * * *", "5-1 * * * *", "* * 0 * *",
                                 "* * * 13 *", "* * * * 8", "a * * * *", "0 0 30 2 *"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        next_run(bad, datetime(2026, 1, 1))
