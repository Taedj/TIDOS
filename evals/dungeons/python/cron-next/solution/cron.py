from datetime import datetime, timedelta

_RANGES = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]


def _field(text, low, high):
    values = set()
    for part in text.split(","):
        step = 1
        base = part
        if "/" in part:
            base, step_text = part.split("/", 1)
            if not step_text.isdigit() or int(step_text) == 0:
                raise ValueError("bad step in %r" % part)
            step = int(step_text)
        if base == "*":
            start, end = low, high
        elif "-" in base:
            a, b = base.split("-", 1)
            if not (a.isdigit() and b.isdigit()):
                raise ValueError("bad range %r" % part)
            start, end = int(a), int(b)
            if start > end:
                raise ValueError("reversed range %r" % part)
        elif base.isdigit():
            start = int(base)
            end = high if "/" in part else start
        else:
            raise ValueError("bad field %r" % part)
        if start < low or end > high:
            raise ValueError("out of range %r" % part)
        values.update(range(start, end + 1, step))
    return values


def next_run(expression, after):
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("expected 5 fields")
    minutes, hours, doms, months, dows = (_field(f, lo, hi) for f, (lo, hi) in zip(fields, _RANGES))
    dows = {0 if d == 7 else d for d in dows}
    dom_star, dow_star = fields[2].startswith("*"), fields[4].startswith("*")

    def day_matches(day):
        dom_ok = day.day in doms
        dow_ok = (day.weekday() + 1) % 7 in dows
        if dom_star or dow_star:
            return dom_ok and dow_ok
        return dom_ok or dow_ok

    start = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
    day = start.date()
    for _ in range(366 * 8 + 2):
        if day.month in months and day_matches(day):
            for hour in sorted(hours):
                for minute in sorted(minutes):
                    candidate = datetime(day.year, day.month, day.day, hour, minute, tzinfo=after.tzinfo)
                    if candidate >= start:
                        return candidate
        day += timedelta(days=1)
    raise ValueError("no matching time within 8 years")
