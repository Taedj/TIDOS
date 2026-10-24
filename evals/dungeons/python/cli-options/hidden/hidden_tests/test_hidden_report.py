import json, subprocess, sys

def run(tmp_path, *args):
    data = tmp_path / "d.json"
    data.write_text(json.dumps([{"name": "A", "grade": 10}, {"name": "B", "grade": 18},
                                {"name": "C", "grade": 12.5}, {"name": "D", "grade": 7}]))
    return subprocess.run([sys.executable, "report.py", str(data), *args], capture_output=True, text=True)

def test_default_unchanged(tmp_path):
    r = run(tmp_path)
    assert r.returncode == 0
    assert r.stdout.splitlines() == ["B: 18", "C: 12.5", "A: 10", "D: 7"]

def test_limit(tmp_path):
    assert run(tmp_path, "--limit", "2").stdout.splitlines() == ["B: 18", "C: 12.5"]

def test_min_grade(tmp_path):
    assert run(tmp_path, "--min-grade", "10").stdout.splitlines() == ["B: 18", "C: 12.5", "A: 10"]

def test_both(tmp_path):
    assert run(tmp_path, "--min-grade", "10", "--limit", "1").stdout.splitlines() == ["B: 18"]

def test_bad_limit(tmp_path):
    assert run(tmp_path, "--limit", "0").returncode == 2
    assert run(tmp_path, "--limit", "abc").returncode == 2
