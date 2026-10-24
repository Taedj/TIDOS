import re
from datetime import date

_DATE = re.compile(r"(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})")


def parse_date(text):
    match = _DATE.fullmatch(str(text).strip())
    if not match:
        raise ValueError("expected DD/MM/YYYY, got %r" % text)
    day, month, year = (int(g) for g in match.groups())
    return date(year, month, day)  # raises ValueError for impossible dates


def format_date(value):
    return value.strftime("%d/%m/%Y")
