"""TIDOS daily quest: run every health check and write a dated report (regressions flagged).

  python scripts/daily_quest.py            -> ~/.tidos/reports/<date>.md, exit 1 on any failure

Checks: unit/security tests, spec validator, plugin sync, dungeon validation (every task fails untouched and
passes with its solution), brain import + playbook refresh, and the TIDOS status. Schedule it yourself if you want
it daily, e.g. Windows:  schtasks /Create /SC DAILY /ST 09:00 /TN TIDOS-daily /TR "python <TIDOS>\\scripts\\daily_quest.py"
"""
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tidos_session.detect import tidos_home  # noqa: E402

CHECKS = [
    ("tests", ["-m", "pytest", "-q", "-p", "no:cacheprovider", "tests", "browser_relay/tests"]),
    ("specs", ["scripts/validate_specs.py"]),
    ("plugin sync", ["scripts/build_plugin.py", "--check"]),
    ("dungeons valid", ["-I", "tidos_evals/__main__.py", "validate"]),
    ("learning refresh", ["-I", "tidos_learn/__main__.py", "distill", "--quiet"]),
    ("status", ["-I", "tidos_learn/__main__.py", "status"]),
]


def last_line(text):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    return lines[-1][:160] if lines else ""


def main():
    stamp = datetime.now(timezone.utc)
    rows, details, failed = [], [], []
    for name, args in CHECKS:
        try:
            proc = subprocess.run([sys.executable] + args, cwd=ROOT, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=1800)
            code, out = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired:
            code, out = 124, "timed out"
        rows.append("| %s | %s | %s |" % (name, "PASS" if code == 0 else "**FAIL**", last_line(out).replace("|", "/")))
        if code:
            failed.append(name)
            details.append("### %s\n```\n%s\n```" % (name, out[-2500:]))
        if name == "status":
            details.insert(0, "```\n%s\n```" % out.strip())
    report = "\n".join(["# TIDOS daily quest - %s" % stamp.strftime("%Y-%m-%d %H:%M UTC"), "",
                        "**Result:** %s" % ("all clear" if not failed else "REGRESSION in " + ", ".join(failed)), "",
                        "| Check | Result | Last line |", "|---|---|---|"] + rows + ["", "## Details"] + details) + "\n"
    folder = os.path.join(tidos_home(), "reports")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, stamp.strftime("%Y-%m-%d") + ".md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(report)
    print(report.split("## Details")[0])
    print("Report: %s" % path)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
