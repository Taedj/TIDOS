import inspect, warnings
import pytest
import school
from school import service

def test_fetch_user():
    from school import fetch_user
    assert fetch_user(1) == "Lina"
    with pytest.raises(KeyError):
        fetch_user(99)

def test_alias_warns():
    from school import get_user
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        assert get_user(2) == "Omar"
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)

def test_internal_code_uses_new_name():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        assert school.welcome_message(1) == "Welcome, Lina!"
    assert "get_user" not in inspect.getsource(service)
