import pytest
from shop import ProductService

def test_update_visible_through_any_spelling():
    s = ProductService()
    s.add_product(" ab-1 ", "Pen", 10)
    assert s.get_product("AB-1")["price"] == 10
    assert s.get_product("ab-1 ")["price"] == 10       # warm the cache with another spelling
    s.update_price("Ab-1", 12)
    for spelling in ("AB-1", " ab-1", "ab-1 ", "aB-1"):
        assert s.get_product(spelling)["price"] == 12

def test_codes_normalized_and_replaced():
    s = ProductService()
    s.add_product("x1", "Old", 1)
    s.get_product("X1")
    s.add_product(" X1 ", "New", 2)
    s.add_product("ab-1", "Pen", 3)
    assert [(p["code"], p["name"], p["price"]) for p in s.list_products()] == \
        [("AB-1", "Pen", 3), ("X1", "New", 2)]
    assert s.get_product("x1")["name"] == "New"

def test_unknown():
    s = ProductService()
    assert s.get_product("nope") is None
    with pytest.raises(KeyError):
        s.update_price("nope", 1)
