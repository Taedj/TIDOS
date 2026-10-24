def find_conflicts(sessions):
    conflicts = []
    for a in sessions:
        for b in sessions:
            if a is b or a["day"] != b["day"] or a["room"] != b["room"]:
                continue
            if a["start"] <= b["end"] and b["start"] <= a["end"]:
                conflicts.append((a["id"], b["id"]))
    return conflicts
