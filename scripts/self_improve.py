"""TIDOS self-improvement: implement ONE accepted proposal on a separate branch, gated by the full checks.

  python scripts/self_improve.py [--id N] [--agent opencode:<provider/model> | claude:<model>] [--dry-run]

The agent is TIDOS's helper model by default (tidos_session.helper: a free model you already use).

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
for stream in (sys.stdout, sys.stderr):  # opencode prints \u2699-ish glyphs: bare cmd windows run cp1252
    if stream is not None and getattr(stream, "encoding", "").lower().replace("-", "") not in ("utf8",):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError, AttributeError):
            pass

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


def count_tests(cwd):
    code, out = run(["{python}", "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "tests"], cwd)
    m = re.search(r"(\d+) tests? collected", out)
    return int(m.group(1)) if m else None


def implement(agent, prompt, work):
    """Let the agent edit the worktree: OpenCode (any provider, free by default) or Claude Code.
    A dead free model (server refuses) falls through to the next free one instead of wasting the run."""
    env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}
    family, _, model = agent.partition(":")
    if family == "claude":
        exe = shutil.which("claude")
        if not exe:
            print("claude CLI not found.")
            return False
        # the per-run cap is only a safety net for people who chose Claude (it bills their own account)
        proc = subprocess.run([exe, "-p", "--model", model, "--output-format", "json", "--permission-mode",
                               "acceptEdits", "--allowedTools", AGENT_TOOLS, "--max-budget-usd", "0.5"],
                              input=prompt, cwd=work, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=3600, env=dict(env, TIDOS_JOB="self_improve"))
        try:
            print(str(json.loads(proc.stdout.strip().splitlines()[-1]).get("result"))[-800:])
        except (ValueError, IndexError):
            print("Agent output unreadable:\n" + (proc.stdout + proc.stderr)[-800:])
        return True
    exe = shutil.which("opencode")
    if not exe:
        print("opencode CLI not found.")
        return False
    from tidos_session import helper
    try_names = [model] + [m for m in helper.FREE_FALLBACK if m != model]  # "provider/model" ids, same shape
    from tidos_evals.agents import OPENCODE_SANDBOX  # edits + language runners only; no web, no other shell
    scratch = [os.path.join(work, n) for n in ("PROPOSAL.md", "opencode.json")]
    with open(scratch[0], "w", encoding="utf-8") as f:
        f.write(prompt)
    with open(scratch[1], "w", encoding="utf-8") as f:
        json.dump(OPENCODE_SANDBOX, f)
    try:
        tail = ""
        for name in try_names:
            try:
                proc = subprocess.run([exe, "run", "--dir", work, "-m", name,
                                       "Read PROPOSAL.md and do exactly what it says."],
                                      cwd=work, capture_output=True, text=True, encoding="utf-8",
                                      errors="replace", timeout=3600, env=dict(env, PWD=work, TIDOS_JOB="self_improve"),
                                      stdin=subprocess.DEVNULL)
            except subprocess.TimeoutExpired as e:
                tail = str(e)
                print("Model %s timed out: trying the next free model." % name)
                continue
            tail = (proc.stdout + proc.stderr)
            if proc.returncode == 0 and "Unexpected server error" not in tail:
                print(tail[-1200:])
                return True
            print("Model %s failed (exit %d, server refused or no output): trying the next free model."
                  % (name, proc.returncode))
        print("Every free model failed:\n" + tail[-1200:])
        return False
    finally:
        for path in scratch:  # TIDOS's own instructions never end up in the commit
            if os.path.exists(path):
                os.remove(path)


def gates(cwd):
    results = []
    for argv in GATES:
        code, out = run(argv, cwd)
        results.append((" ".join(argv).replace("{python}", "python"), code, out))
    return results


def _branch_worktrees(branch, root=ROOT):
    out = run(["git", "worktree", "list", "--porcelain"], root)[1]
    found = []
    for block in re.split(r"\n\s*\n", out):
        if "branch refs/heads/%s" % branch in block:
            first = block.strip().splitlines()
            found.append(first[0][len("worktree "):])
    return found


def prepare_branch(branch, root=ROOT):
    """A fresh worktree for branch; leftover auto branches are recycled when merged, refused when not.
    Returns (error or None, work path)."""
    run(["git", "worktree", "prune"], root)
    if run(["git", "rev-parse", "--verify", "--quiet", "refs/heads/%s" % branch], root)[0] == 0:
        if run(["git", "branch", "--merged", "HEAD", "--list", branch], root)[1].strip():
            for wt in _branch_worktrees(branch, root):       # a branch checked out in a worktree
                run(["git", "worktree", "remove", "--force", wt], root)  # cannot be deleted until freed
            # git branch -d refuses unmerged branches by design: merged leftovers lose nothing
            run(["git", "branch", "-d", branch], root)
            print("Recycled %s: the previous attempt is fully merged into HEAD, starting fresh." % branch)
        else:
            return ("branch %s already exists (an UNMERGED earlier attempt): inspect it with `git log -p %s`, "
                    "then delete it yourself if it should not stay: git branch -D %s" % (branch, branch, branch), None)
    work = os.path.join(tempfile.mkdtemp(prefix="tidos-auto-"), "wt")
    code, out = run(["git", "worktree", "add", "-q", "-b", branch, work, "HEAD"], root)
    return (None, work) if code == 0 else ("Cannot create worktree/branch %s:\n%s" % (branch, out), None)


def main(args=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int)
    ap.add_argument("--agent", help="opencode:<provider/model> or claude:<model> (default: TIDOS's helper model)")
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
    refused, work = prepare_branch(branch)
    if refused:
        print(refused)
        return 1
    print("Worktree %s on branch %s" % (work, branch))
    impact = {"tests_before": count_tests(work)}
    try:
        if not a.dry_run:
            from tidos_session import helper
            agent = a.agent or helper.resolve()
            if not agent:
                print("No model available: install OpenCode (free models) or pass --agent.")
                return 1
            impact["agent"] = agent
            print("Agent: %s" % agent)
            if not implement(agent, PROMPT.format(**item), work):
                return 1
        results = gates(work)
        for name, rc, out in results:
            print("[%s] %s" % ("PASS" if rc == 0 else "FAIL", name))
            if rc:
                print(out[-1200:])
        ok = all(rc == 0 for _, rc, _ in results)
        changed = run(["git", "status", "--porcelain"], work)[1].strip()
        if ok and changed and not a.dry_run:
            run(["git", "add", "-A"], work)
            stat = run(["git", "diff", "--cached", "--shortstat"], work)[1]
            nums = dict((k, int(n)) for n, k in re.findall(r"(\d+) (file|insertion|deletion)", stat))
            impact.update(tests_after=count_tests(work), files=nums.get("file", 0),
                          insertions=nums.get("insertion", 0), deletions=nums.get("deletion", 0), gates="all passed")
            run(["git", "commit", "-q", "-m", "auto: %s (evolution #%d)\n\nImplemented by scripts/self_improve.py; "
                 "all gates passed. Review before merging." % (item["title"], item["id"])], work)
            evolve.set_status(item["id"], "implemented", branch=branch, impact=impact)
            print("\nCommitted on %s (not pushed). Review: git log -p %s ; merge if you agree." % (branch, branch))
            print("Impact: tests %s -> %s, %d file(s) +%d/-%d. Measure its effect: python scripts/measure_proposal.py "
                  "--id %d" % (impact["tests_before"], impact["tests_after"], impact["files"], impact["insertions"],
                               impact["deletions"], item["id"]))
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
