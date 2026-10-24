def assign(students, rooms):
    ids = [s["id"] for s in students]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate student id")
    if any(r["rows"] < 1 or r["cols"] < 1 for r in rooms):
        raise ValueError("rooms need rows and cols >= 1")
    remaining = {}
    for s in students:
        remaining.setdefault(s["group"], []).append(s["id"])
    plan = {}
    for room in rooms:
        for row in range(room["rows"]):
            left = None
            for col in range(room["cols"]):
                if not any(remaining.values()):
                    return plan
                candidates = [g for g, members in remaining.items() if members and g != left]
                if not candidates:
                    left = None          # leave the seat empty
                    continue
                group = max(candidates, key=lambda g: len(remaining[g]))
                plan[remaining[group].pop(0)] = (room["name"], row, col)
                left = group
    if any(remaining.values()):
        raise ValueError("not enough suitable seats")
    return plan
