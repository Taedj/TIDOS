import pytest
from cache import LRUCache

def test_eviction_order():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    assert c.get("a") == 1          # a is now most recent
    c.put("c", 3)                   # evicts b
    assert "b" not in c and c.get("b") is None
    assert c.get("a") == 1 and c.get("c") == 3
    assert len(c) == 2

def test_update_refreshes():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2); c.put("a", 10); c.put("c", 3)   # evicts b
    assert c.get("a") == 10 and "b" not in c

def test_contains_does_not_refresh():
    c = LRUCache(2)
    c.put("a", 1); c.put("b", 2)
    assert "a" in c
    c.put("c", 3)                   # a is still least recent -> evicted
    assert "a" not in c and "b" in c

def test_default_and_capacity():
    c = LRUCache(1)
    assert c.get("x", 42) == 42
    c.put("x", None)
    assert "x" in c and c.get("x", 5) is None
    for bad in (0, -1, 1.5, "2"):
        with pytest.raises(ValueError):
            LRUCache(bad)
