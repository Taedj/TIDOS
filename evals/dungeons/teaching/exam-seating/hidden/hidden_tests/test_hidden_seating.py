import pytest
from seating import assign

def check(students, rooms, plan):
    bounds = {r["name"]: (r["rows"], r["cols"]) for r in rooms}
    group = {s["id"]: s["group"] for s in students}
    assert sorted(plan) == sorted(group), "every student seated exactly once"
    seats = {}
    for sid, (room, row, col) in plan.items():
        rows, cols = bounds[room]
        assert 0 <= row < rows and 0 <= col < cols
        assert (room, row, col) not in seats, "seat used twice"
        seats[(room, row, col)] = sid
    for (room, row, col), sid in seats.items():
        right = seats.get((room, row, col + 1))
        assert right is None or group[right] != group[sid], "same group side by side"

def students(spec):
    return [{"id": "%s%d" % (g, i), "group": g} for g, n in spec for i in range(n)]

@pytest.mark.parametrize("spec,rooms", [
    ([("A", 4), ("B", 3), ("C", 3)], [{"name": "R1", "rows": 3, "cols": 4}]),
    ([("A", 4)], [{"name": "R1", "rows": 2, "cols": 3}]),
    ([("A", 3), ("B", 2)], [{"name": "S", "rows": 1, "cols": 2}, {"name": "T", "rows": 2, "cols": 2}]),
    ([("A", 6), ("B", 6)], [{"name": "Amphi", "rows": 3, "cols": 4}]),
])
def test_valid_plans(spec, rooms):
    st = students(spec)
    check(st, rooms, assign(st, rooms))

@pytest.mark.parametrize("spec,rooms", [
    ([("A", 3)], [{"name": "R", "rows": 1, "cols": 3}]),
    ([("A", 2), ("B", 2)], [{"name": "R", "rows": 1, "cols": 3}]),
    ([("A", 1)], [{"name": "R", "rows": 0, "cols": 3}]),
])
def test_impossible(spec, rooms):
    with pytest.raises(ValueError):
        assign(students(spec), rooms)

def test_duplicate_ids():
    with pytest.raises(ValueError):
        assign([{"id": "x", "group": "A"}, {"id": "x", "group": "B"}], [{"name": "R", "rows": 2, "cols": 2}])
