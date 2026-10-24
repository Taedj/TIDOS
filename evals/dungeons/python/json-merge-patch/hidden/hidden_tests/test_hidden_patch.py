import copy
import pytest
from patching import merge_patch

RFC = [
    ({"a": "b"}, {"a": "c"}, {"a": "c"}),
    ({"a": "b"}, {"b": "c"}, {"a": "b", "b": "c"}),
    ({"a": "b"}, {"a": None}, {}),
    ({"a": "b", "b": "c"}, {"a": None}, {"b": "c"}),
    ({"a": ["b"]}, {"a": "c"}, {"a": "c"}),
    ({"a": "c"}, {"a": ["b"]}, {"a": ["b"]}),
    ({"a": {"b": "c"}}, {"a": {"b": "d", "c": None}}, {"a": {"b": "d"}}),
    ({"a": [{"b": "c"}]}, {"a": [1]}, {"a": [1]}),
    (["a", "b"], ["c", "d"], ["c", "d"]),
    ({"a": "b"}, ["c"], ["c"]),
    ({"a": "foo"}, None, None),
    ({"a": "foo"}, "bar", "bar"),
    ({"e": None}, {"a": 1}, {"e": None, "a": 1}),
    ([1, 2], {"a": "b", "c": None}, {"a": "b"}),
    ({}, {"a": {"bb": {"ccc": None}}}, {"a": {"bb": {}}}),
]

@pytest.mark.parametrize("target,patch,expected", RFC)
def test_rfc7396_examples(target, patch, expected):
    assert merge_patch(copy.deepcopy(target), copy.deepcopy(patch)) == expected

def test_inputs_not_modified():
    target = {"a": {"b": 1, "c": [1]}, "d": 2}
    patch = {"a": {"b": None, "x": {"y": 1}}, "d": None}
    t0, p0 = copy.deepcopy(target), copy.deepcopy(patch)
    result = merge_patch(target, patch)
    assert result == {"a": {"c": [1], "x": {"y": 1}}}
    assert target == t0 and patch == p0
    result["a"]["c"].append(2)
    assert target["a"]["c"] == [1]
