import subprocess
from pathlib import Path

def run(src, dst):
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                           str(Path("backup.ps1").resolve()), "-Source", str(src), "-Destination", str(dst)],
                          capture_output=True, text=True, timeout=120)

def test_spaces_brackets_apostrophes(tmp_path):
    src = tmp_path / "My Docs [2026] l'ecole"
    (src / "sub dir").mkdir(parents=True)
    for name in ("a b.txt", "c[1].txt", "d'e.txt"):
        (src / name).write_text("x")
    (src / "skip.md").write_text("x")
    (src / "sub dir" / "nested.txt").write_text("x")
    dst = tmp_path / "Back Up [new]" / "out folder"
    r = run(src, dst)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().splitlines()[-1] == "Copied 3 files"
    assert sorted(p.name for p in dst.iterdir()) == ["a b.txt", "c[1].txt", "d'e.txt"]

def test_single_and_zero_files(tmp_path):
    src = tmp_path / "one file"; src.mkdir()
    (src / "only.txt").write_text("x")
    assert run(src, tmp_path / "o1").stdout.strip().splitlines()[-1] == "Copied 1 files"
    empty = tmp_path / "empty dir"; empty.mkdir()
    assert run(empty, tmp_path / "o2").stdout.strip().splitlines()[-1] == "Copied 0 files"
