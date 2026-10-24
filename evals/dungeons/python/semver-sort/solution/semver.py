import re

_IDENT = r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
_SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
                     r"(?:-(%s(?:\.%s)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$" % (_IDENT, _IDENT))


def _key(version):
    match = _SEMVER.match(version)
    if not match:
        raise ValueError("invalid semantic version: %r" % version)
    major, minor, patch = (int(g) for g in match.group(1, 2, 3))
    pre = match.group(4)
    if pre is None:
        pre_key = (1,)
    else:
        pre_key = (0, tuple((0, int(p), "") if p.isdigit() else (1, 0, p) for p in pre.split(".")))
    return (major, minor, patch, pre_key)


def sort_versions(versions):
    keys = {v: _key(v) for v in versions}
    return sorted(versions, key=keys.__getitem__)
