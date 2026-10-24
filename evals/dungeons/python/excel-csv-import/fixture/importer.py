def load_students(path):
    with open(path) as f:
        rows = [line.strip().split(",") for line in f][1:]
    return [{"name": r[0], "group": r[1], "grade": float(r[2])} for r in rows]
