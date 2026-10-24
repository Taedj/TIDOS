import pytest
from grades import final_grade

def test_rounding_quarter_half_up():
    assert final_grade([12.125], [1]) == 12.25
    assert final_grade([12.12], [1]) == 12.0
    assert final_grade([10, 15], [1, 1]) == 12.5
    assert final_grade([11, 14, 9], [2, 1, 1]) == 11.25   # 45/4 = 11.25
    assert final_grade([13, 8], [3, 1]) == 11.75          # 47/4

def test_absence_counts_zero():
    assert final_grade([None, 16], [1, 1]) == 8.0

@pytest.mark.parametrize("marks,weights", [
    ([10], [1, 1]), ([10], [-1]), ([10, 12], [0, 0]), ([21], [1]), ([-1], [1])])
def test_invalid(marks, weights):
    with pytest.raises(ValueError):
        final_grade(marks, weights)
