import random
import pytest
from semver import sort_versions

SPEC = ["1.0.0-alpha", "1.0.0-alpha.1", "1.0.0-alpha.beta", "1.0.0-beta", "1.0.0-beta.2",
        "1.0.0-beta.11", "1.0.0-rc.1", "1.0.0"]

def test_spec_example_order():
    shuffled = SPEC[:]
    random.Random(7).shuffle(shuffled)
    assert sort_versions(shuffled) == SPEC

def test_numeric_parts():
    assert sort_versions(["1.10.0", "2.0.0", "1.9.0", "1.9.10", "1.9.2"]) == \
        ["1.9.0", "1.9.2", "1.9.10", "1.10.0", "2.0.0"]

def test_build_metadata_ignored_but_kept_and_stable():
    assert sort_versions(["1.0.0+b2", "1.0.0-rc.1+x", "1.0.0+b1"]) == ["1.0.0-rc.1+x", "1.0.0+b2", "1.0.0+b1"]

def test_does_not_mutate():
    data = ["2.0.0", "1.0.0"]
    sort_versions(data)
    assert data == ["2.0.0", "1.0.0"]

@pytest.mark.parametrize("bad", ["1.0", "01.0.0", "1.0.0-", "1.0.0-01", "v1.0.0", "a.b.c", "1.0.0+"])
def test_invalid(bad):
    with pytest.raises(ValueError):
        sort_versions(["1.0.0", bad])
