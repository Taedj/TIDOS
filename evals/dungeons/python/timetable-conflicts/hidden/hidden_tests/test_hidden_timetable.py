from timetable import find_conflicts

def s(id, day, start, end, room, teacher):
    return dict(id=id, day=day, start=start, end=end, room=room, teacher=teacher)

def test_room_and_teacher_conflicts():
    sessions = [
        s(1, "sun", "8:00", "9:30", "A1", "Zitouni"),
        s(2, "sun", "9:00", "10:30", "A1", "Benali"),      # room overlap with 1
        s(3, "sun", "9:30", "11:00", "B2", "Zitouni"),     # back-to-back with 1 -> no
        s(4, "sun", "10:00", "11:30", "C3", "Zitouni"),    # teacher overlap with 3
        s(5, "mon", "8:00", "9:30", "A1", "Zitouni"),      # other day
    ]
    assert find_conflicts(sessions) == [(1, 2), (3, 4)]

def test_string_time_trap():
    # "9:40" > "10:00" as strings; numerically 9:40 < 10:00
    sessions = [s(7, "tue", "9:40", "11:10", "R", "X"), s(3, "tue", "10:00", "11:30", "R", "Y")]
    assert find_conflicts(sessions) == [(3, 7)]

def test_contained_and_identical():
    sessions = [s(1, "wed", "08:00", "12:00", "R", "X"), s(2, "wed", "09:00", "10:00", "Q", "X"),
                s(3, "wed", "08:00", "12:00", "R", "Z")]
    assert find_conflicts(sessions) == [(1, 2), (1, 3)]

def test_empty():
    assert find_conflicts([]) == []
