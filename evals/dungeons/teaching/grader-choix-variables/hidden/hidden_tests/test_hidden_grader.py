import pytest
from grader import check

CHOIX = {"type": "choix", "expected": "RICHE{D}", "options": ["PREMVAR{D}", "RICHE{D}", "AUTRE"]}

def test_choix_renders_variables():
    assert check(CHOIX, "RICHE7", {"D": 7})
    assert check(CHOIX, "  riche7 ", {"D": 7})
    assert not check(CHOIX, "RICHE3", {"D": 7})
    assert not check(CHOIX, "PREMVAR7", {"D": 7})

def test_choix_answer_must_be_an_option():
    rule = {"type": "choix", "expected": "A{D}", "options": ["B{D}"]}
    assert not check(rule, "A1", {"D": 1})

def test_other_types_unchanged():
    assert check({"type": "exacte", "expected": "x={D}"}, " x=4 ", {"D": 4})
    assert not check({"type": "exacte", "expected": "X={D}"}, "x=4", {"D": 4})
    assert check({"type": "contient", "expected": "Total {D}"}, "le total 5 points", {"D": 5})
    assert check({"type": "regex", "expected": "v{D}\\d+"}, "v912", {"D": 9})
    with pytest.raises(ValueError):
        check({"type": "liste"}, "x", {})
