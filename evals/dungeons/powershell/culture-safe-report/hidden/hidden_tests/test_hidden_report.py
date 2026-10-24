import subprocess
from pathlib import Path
import pytest

DATA = "name;group;grade\r\nAmina;G2;12,5\r\nOmar;G1;10\r\n\r\nLina;G1;15.5\r\nSara;G2;14\r\nYani;G3;11\r\n"
EXPECTED = ["G1: 12.75 (2 students)", "G2: 13.25 (2 students)", "G3: 11.00 (1 students)"]

@pytest.mark.parametrize("culture", ["en-US", "fr-FR"])
def test_report(tmp_path, culture):
    csv = tmp_path / "notes.csv"
    csv.write_bytes(b"\xef\xbb\xbf" + DATA.encode("utf-8"))
    script = str(Path("report.ps1").resolve())
    command = ("[Threading.Thread]::CurrentThread.CurrentCulture = '%s'; "
               "& '%s' -Path '%s'" % (culture, script, csv))
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    assert [l for l in r.stdout.splitlines() if l.strip()] == EXPECTED
