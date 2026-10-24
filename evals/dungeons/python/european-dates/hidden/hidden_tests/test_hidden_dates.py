from datetime import date
import pytest
from dates import format_date, parse_date

@pytest.mark.parametrize("text", ["25/12/2026", "25-12-2026", "25.12.2026", "  25/12/2026 "])
def test_separators(text):
    assert parse_date(text) == date(2026, 12, 25)

def test_day_first_and_short_forms():
    assert parse_date("1/2/2026") == date(2026, 2, 1)
    assert parse_date("03/04/2026") == date(2026, 4, 3)

@pytest.mark.parametrize("bad", ["31/02/2026", "hello", "2026/12/25", "", "13/13/2026"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        parse_date(bad)

def test_format():
    assert format_date(date(2026, 2, 1)) == "01/02/2026"
    assert format_date(parse_date("9.7.2026")) == "09/07/2026"
