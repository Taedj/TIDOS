"""TIDOS self-improvement: implement ONE accepted proposal on a separate branch, gated by the full checks.

  python scripts/self_improve.py [--id N] [--model sonnet] [--budget 2.0] [--dry-run]

Safety:
  - works in a temporary git WORKTREE on branch auto/<id>-<slug>: the user's checkout is never touched
  - the agent (claude -p) may only edit files and run the project's checks; no network, no git push
  - gates: unit tests, spec validator, plugin sync; the branch is committed ONLY if every gate passes
  - never pushes, never merges: the user reviews `git log auto/...` and merges if they want
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tidos_learn import evolve  # noqa: E402

GATES = [
    ["{python}", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"],
    ["{python}", "scripts/validate_specs.py"],
    ["{python}", "scripts/build_plugin.py", "--check"],
]
AGENT_TOOLS = ",".join(["Read", "Edit", "Write", "Glob", "Grep", "Bash(python:*)", "Bash(python -m pytest:*)"])
PROMPT = """You are improving TIDOS (this repository). Implement exactly this accepted proposal, nothing else:

Title: {title}
Why: {reason}

Rules: read the relevant code first; keep the existing style; add or update tests for the change; run
`python -m pytest -q tests` and `python scripts/validate_specs.py` until both pass; if you change files under
.claude/, run `python scripts/build_plugin.py`. Do not touch memory/, evolution/, credentials or CI secrets.
End with a 3-line summary of what you changed."""


def run(argv, cwd, timeout=900):
    argv = [sys.executable if a == "{python}" else a for a in argv]
    proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout)
    return proc.returncode, (proc.stdout + proc.stderr)[-3000:]


def gates(cwd):
    results = []
    for argv in GATES:
        code, out = run(argv, cwd)
        results.append((" ".join(argv).replace("{python}", "python"), code, out))
    return results


def main(args=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int)
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--budget", type=float, default=2.0)
    ap.add_argument("--dry-run", action="store_true", help="create the worktree and run the gates, no agent")
    a = ap.parse_args(args)

    accepted = evolve.ranked("accepted")
    item = next((i for i in accepted if a.id is None or i["id"] == a.id), None)
    if not item:
        print("No accepted proposal%s. Accept one first (dashboard Evolution tab or `tidos_learn proposals --accept N`)."
              % (" with id %d" % a.id if a.id else ""))
        return 1
    slug = re.sub(r"[^a-z0-9]+", "-", item["title"].lower()).strip("-")[:40]
    branch = "auto/%d-%s" % (item["id"], slug)
    work = os.path.join(tempfile.mkdtemp(prefix="tidos-auto-"), "wt")
    code, out = run(["git", "worktree", "add", "-q", "-b", branch, work, "HEAD"], ROOT)
    if code:
        print("Cannot create worktree/branch %s:\n%s" % (branch, out))
        return 1
    print("Worktree %s on branch %s" % (work, branch))
    try:
        if not a.dry_run:
            exe = shutil.which("claude")
            if not exe:
                print("claude CLI not found.")
                return 1
            env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
            proc = subprocess.run([exe, "-p", "--model", a.model, "--output-format", "json", "--permission-mode",
                                   "acceptEdits", "--allowedTools", AGENT_TOOLS, "--max-budget-usd", str(a.budget)],
                                  input=PROMPT.format(**item), cwd=work, capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=3600, env=env)
            try:
                data = json.loads(proc.stdout.strip().splitlines()[-1])
                print("Agent: %s (cost %.2f USD)\n%s" % ("error" if data.get("is_error") else "done",
                                                        data.get("total_cost_usd", 0), str(data.get("result"))[-800:]))
            except (ValueError, IndexError):
                print("Agent output unreadable:\n" + (proc.stdout + proc.stderr)[-800:])
        results = gates(work)
        for name, rc, out in results:
            print("[%s] %s" % ("PASS" if rc == 0 else "FAIL", name))
            if rc:
                print(out[-1200:])
        ok = all(rc == 0 for _, rc, _ in results)
        changed = run(["git", "status", "--porcelain"], work)[1].strip()
        if ok and changed and not a.dry_run:
            run(["git", "add", "-A"], work)
            run(["git", "commit", "-q", "-m", "auto: %s (evolution #%d)\n\nImplemented by scripts/self_improve.py; "
                 "all gates passed. Review before merging." % (item["title"], item["id"])], work)
            evolve.set_status(item["id"], "implemented", branch=branch)
            print("\nCommitted on %s (not pushed). Review: git log -p %s ; merge if you agree." % (branch, branch))
        elif not a.dry_run:
            print("\nNothing committed (%s). The branch stays for inspection: %s" %
                  ("gates failed" if not ok else "no changes", branch))
        return 0 if ok else 1
    finally:
        run(["git", "worktree", "remove", "--force", work], ROOT)
        if a.dry_run:
            run(["git", "branch", "-D", branch], ROOT)


if __name__ == "__main__":
    sys.exit(main())
