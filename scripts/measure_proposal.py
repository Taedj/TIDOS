"""Measure what an implemented proposal does to TIDOS's guidance, before you merge it (plan 10.1).

  python scripts/measure_proposal.py --id N [--agent opencode:opencode/big-pickle] [--min-difficulty B]

The same agent runs the same dungeons in GUIDE mode twice, each from a clean git worktree:
  base   = the code the proposal's branch started from
  after  = the proposal's branch
Only the TIDOS code differs (your private playbooks and rules are the same for both), so the pass-rate
difference is the proposal's effect. Results are stored under their own labels ("<agent> [#N base]" /
"<agent> [#N after]"), never mixed with the leaderboard, and the delta is saved on the proposal:
the Evolution tab shows it next to the Merge decision. Nothing is merged, pushed or deleted.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tidos_brain import db  # noqa: E402
from tidos_learn import evolve  # noqa: E402

INSTRUMENT = ["tidos_evals", os.path.join("evals", "dungeons")]  # held constant: a proposal changing them is not measured here


def git(args, cwd=ROOT):
    proc = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def raid(worktree, agent, min_difficulty, label, budget):
    """Run the worktree's own eval runner; returns (run_id, output tail)."""
    argv = [sys.executable, "-I", os.path.join(worktree, "tidos_evals", "__main__.py"), "run", "--agent", agent,
            "--tidos", "guide", "--min-difficulty", min_difficulty, "--label", label, "--budget", str(budget)]
    proc = subprocess.run(argv, cwd=worktree, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    out = proc.stdout + proc.stderr
    print(out[-2500:], flush=True)
    m = re.search(r"^Run (\S+):", out, re.M)
    return (m.group(1) if m else None), out


def rates(conn, run_id):
    rows = conn.execute("SELECT suite || '/' || task_name t, AVG(passed) p FROM evals WHERE run_id = ? AND "
                        "COALESCE(error, '') NOT LIKE 'contaminated%' GROUP BY t", (run_id,)).fetchall()
    return {r["t"]: r["p"] for r in rows}


def main(args=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int, required=True)
    ap.add_argument("--agent", default="opencode:opencode/big-pickle")
    ap.add_argument("--min-difficulty", default="B", choices=list("EDCBAS"))
    ap.add_argument("--budget", type=float, default=0.25, help="max USD per Claude attempt")
    a = ap.parse_args(args)
    item = next((i for i in evolve.load() if i["id"] == a.id), None)
    if not item or not item.get("branch"):
        print("Proposal #%d has no implemented branch to measure." % a.id)
        return 1
    branch = item["branch"]
    code, base = git(["merge-base", "HEAD", branch])
    if code:
        print("Branch %s not found: %s" % (branch, base))
        return 1
    tmp = tempfile.mkdtemp(prefix="tidos-measure-")
    trees = {"base": os.path.join(tmp, "base"), "after": os.path.join(tmp, "after")}
    try:
        for name, ref in (("base", base), ("after", branch)):
            code, out = git(["worktree", "add", "-q", "--detach", trees[name], ref])
            if code:
                print("Cannot create the %s worktree: %s" % (name, out))
                return 1
            # the measuring instrument (eval runner + dungeons) is today's, identical for both runs:
            # only the guidance code that the proposal changed differs
            for part in INSTRUMENT:
                src, dst = os.path.join(ROOT, part), os.path.join(trees[name], part)
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        results = {}
        for name in ("base", "after"):
            print("== %s (%s)" % (name, base[:8] if name == "base" else branch), flush=True)
            run_id, _ = raid(trees[name], a.agent, a.min_difficulty, "%s [#%d %s]" % (a.agent, a.id, name), a.budget)
            if not run_id:
                print("The %s run produced no results." % name)
                return 1
            results[name] = run_id
        conn = db.connect()
        try:
            before, after = rates(conn, results["base"]), rates(conn, results["after"])
        finally:
            conn.close()
        common = sorted(set(before) & set(after))
        if not common:
            print("No task finished in both runs: nothing to compare.")
            return 1
        b = 100.0 * sum(before[t] for t in common) / len(common)
        f = 100.0 * sum(after[t] for t in common) / len(common)
        measure = {"agent": a.agent, "tasks": len(common), "base": round(b), "after": round(f), "delta": round(f - b),
                   "min_difficulty": a.min_difficulty, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        evolve.update(a.id, measure=measure)
        print("\nProposal #%d on %d dungeons (GUIDE, %s): before %d%%, after %d%% (%+d points)." % (
            a.id, len(common), a.agent, measure["base"], measure["after"], measure["delta"]))
        return 0
    finally:
        for path in trees.values():
            git(["worktree", "remove", "--force", path])
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
