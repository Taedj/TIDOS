import pytest
from retrying import retry

def make(failures, exc=ConnectionError):
    state = {"calls": 0}
    def fn():
        """doc"""
        state["calls"] += 1
        if state["calls"] <= failures:
            raise exc("fail %d" % state["calls"])
        return "ok"
    return fn, state

def test_backoff_and_success():
    sleeps = []
    fn, state = make(2)
    wrapped = retry(times=4, exceptions=ConnectionError, base_delay=0.5, sleep=sleeps.append)(fn)
    assert wrapped() == "ok" and state["calls"] == 3
    assert sleeps == [0.5, 1.0]

def test_reraises_last_and_no_final_sleep():
    sleeps = []
    fn, state = make(10)
    wrapped = retry(times=3, exceptions=(ConnectionError, TimeoutError), base_delay=1, sleep=sleeps.append)(fn)
    with pytest.raises(ConnectionError, match="fail 3"):
        wrapped()
    assert state["calls"] == 3 and sleeps == [1, 2]

def test_other_exceptions_not_retried():
    sleeps = []
    fn, state = make(1, exc=ValueError)
    wrapped = retry(times=5, exceptions=ConnectionError, sleep=sleeps.append)(fn)
    with pytest.raises(ValueError):
        wrapped()
    assert state["calls"] == 1 and sleeps == []

def test_metadata_and_methods():
    fn, _ = make(0)
    wrapped = retry(sleep=lambda s: None)(fn)
    assert wrapped.__name__ == "fn" and wrapped.__doc__ == "doc"
    class Api:
        def __init__(self):
            self.n = 0
        @retry(times=2, sleep=lambda s: None)
        def ping(self, x):
            self.n += 1
            if self.n == 1:
                raise OSError("once")
            return x * 2
    assert Api().ping(21) == 42

@pytest.mark.parametrize("times", [0, -1, 1.5])
def test_invalid_times(times):
    with pytest.raises(ValueError):
        retry(times=times)
