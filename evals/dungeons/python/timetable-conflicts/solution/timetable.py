from itertools import combinations


def _minutes(hhmm):
    hours, minutes = hhmm.strip().split(":")
    return int(hours) * 60 + int(minutes)


def find_conflicts(sessions):
    conflicts = set()
    for a, b in combinations(sessions, 2):
        if a["day"] != b["day"]:
            continue
        if a["room"] != b["room"] and a["teacher"] != b["teacher"]:
            continue
        if _minutes(a["start"]) < _minutes(b["end"]) and _minutes(b["start"]) < _minutes(a["end"]):
            conflicts.add(tuple(sorted((a["id"], b["id"]))))
    return sorted(conflicts)
