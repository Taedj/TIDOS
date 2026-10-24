import pytest
from limiter import SlidingWindowLimiter

class Clock:
    def __init__(self):
        self.t = 0.0
    def __call__(self):
        return self.t

def test_limit_and_retry_after():
    c = Clock()
    lim = SlidingWindowLimiter(3, 10, clock=c)
    assert [lim.allow("x") for _ in range(4)] == [True, True, True, False]
    assert lim.retry_after("x") == pytest.approx(10.0)
    c.t = 5
    assert lim.allow("x") is False
    assert lim.retry_after("x") == pytest.approx(5.0)
    c.t = 9.999
    assert lim.allow("x") is False
    c.t = 10                           # rejected calls were not recorded
    assert [lim.allow("x") for _ in range(4)] == [True, True, True, False]

def test_sliding_not_fixed_window():
    c = Clock()
    lim = SlidingWindowLimiter(3, 10, clock=c)
    for t in (0, 1, 2):
        c.t = t
        assert lim.allow("k")
    c.t = 10
    assert lim.allow("k")              # event at 0 expired
    c.t = 10.5
    assert not lim.allow("k")          # 1, 2, 10 still inside
    assert lim.retry_after("k") == pytest.approx(0.5)
    c.t = 11
    assert lim.allow("k")

def test_keys_independent_and_zero_retry():
    c = Clock()
    lim = SlidingWindowLimiter(1, 5, clock=c)
    assert lim.retry_after("a") == 0
    assert lim.allow("a") and not lim.allow("a")
    assert lim.allow("b")

@pytest.mark.parametrize("limit,window", [(0, 1), (1, 0), (1.5, 1), (2, -3), (True, 1)])
def test_invalid(limit, window):
    with pytest.raises(ValueError):
        SlidingWindowLimiter(limit, window)
