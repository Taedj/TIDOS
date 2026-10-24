from registry import Course, add_tag

def test_courses_are_independent():
    a, b = Course("AI"), Course("Networks")
    a.enroll("Lina")
    assert a.students == ["Lina"]
    assert b.students == []

def test_explicit_student_list_is_used():
    c = Course("DB", ["Omar"])
    c.enroll("Sara")
    assert c.students == ["Omar", "Sara"]

def test_add_tag_does_not_leak():
    assert add_tag("a") == ["a"]
    assert add_tag("b") == ["b"]
    assert add_tag("c", ["x"]) == ["x", "c"]
