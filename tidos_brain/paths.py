"""Path helpers for RECORDED paths: traces made on Windows are also read on Linux/macOS (CI, another machine),
where os.path does not treat a backslash as a separator."""
import re


def leaf(path):
    """Last component of a Windows or POSIX path: 'D:\\work\\Dev\\demo' and '/home/u/demo' -> 'demo'."""
    parts = [p for p in re.split(r"[\\/]+", path or "") if p]
    return parts[-1] if parts else ""
