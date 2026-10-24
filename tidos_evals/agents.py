"""Agents that attempt dungeon tasks.

  reference                 apply the task's reference solution (validates the task)
  noop                      change nothing (the task must fail)
  claude:<model>            Claude Code headless (`claude -p`), e.g. claude:claude-haiku-4-5
  opencode:<provider/model> OpenCode headless (`opencode run`), e.g. opencode:opencode/glm-5.3-flash-free

Every agent gets the same one-line prompt pointing at TASK.md (multi-line arguments break the
Windows .cmd wrappers). "With TIDOS" adds TIDOS_PROTOCOL.md and one sentence asking to follow it.
"""
import json
import os
import shutil
import subprocess
import time

PROMPT = "Complete the task described in TASK.md in the current directory."
TIDOS_SUFFIX = " Before you start, read TIDOS_PROTOCOL.md and follow it strictly."

# Claude Code: edits + language runners only (no network, no arbitrary shell)
CLAUDE_TOOLS = ",".join([
    "Read", "Edit", "Write", "Glob", "Grep",
    "Bash(python:*)", "Bash(python3:*)", "Bash(pytest:*)", "Bash(node:*)", "Bash(dart:*)",
    "Bash(powershell:*)", "Bash(sqlite3:*)", "Bash(ls:*)", "Bash(cat:*)",
])


# OpenCode allows every shell command by default: each run gets a project config with the same
# sandbox as Claude (edits + language runners, everything else denied, no web access)
_RUNNERS = ["python", "python3", "pytest", "node", "dart", "powershell", "sqlite3", "ls", "cat"]
OPENCODE_SANDBOX = {
    "$schema": "https://opencode.ai/config.json",
    "permission": {
        "edit": "allow",
        "webfetch": "deny",
        "bash": {"*": "deny", **{"%s *" % r: "allow" for r in _RUNNERS}, **{r: "allow" for r in _RUNNERS}},
    },
}


class AgentResult:
    def __init__(self, ok=True, cost_usd=None, turns=None, error=None, log=""):
        self.ok, self.cost_usd, self.turns, self.error, self.log = ok, cost_usd, turns, error, log


def _env(workdir):
    env = dict(os.environ)
    # some CLIs (OpenCode) trust an inherited $PWD over the real cwd and would work in the caller's repo
    env["PWD"] = workdir
    for key in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT", "CLAUDE_CODE_SSE_PORT"):
        env.pop(key, None)  # run as a fresh top-level session, not nested in the caller's
    env["PYTHONUTF8"] = "1"
    return env


def _run(argv, workdir, timeout):
    exe = shutil.which(argv[0])
    if not exe:
        return None, "%s not found on PATH" % argv[0]
    try:
        proc = subprocess.run([exe] + argv[1:], cwd=workdir, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout, env=_env(workdir),
                              stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") if isinstance(e.stdout, str) else ""
        return None, "agent timed out after %ds\n%s" % (timeout, out[-2000:])
    return proc, None


def attempt(spec, task, workdir, with_tidos, budget_usd=1.0):
    prompt = PROMPT + (TIDOS_SUFFIX if with_tidos else "")
    if spec == "reference":
        task.overlay("solution", workdir)
        return AgentResult()
    if spec == "noop":
        return AgentResult()

    family, _, model = spec.partition(":")
    if family == "claude":
        argv = ["claude", "-p", prompt, "--output-format", "json", "--permission-mode", "acceptEdits",
                "--allowedTools", CLAUDE_TOOLS, "--max-budget-usd", str(budget_usd)]
        if model:
            argv += ["--model", model]
        proc, err = _run(argv, workdir, task.timeout)
        if err:
            return AgentResult(False, error=err)
        try:
            data = json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return AgentResult(proc.returncode == 0, error=None if proc.returncode == 0 else "non-JSON output",
                               log=(proc.stdout + proc.stderr)[-4000:])
        return AgentResult(not data.get("is_error"), cost_usd=data.get("total_cost_usd"),
                           turns=data.get("num_turns"),
                           error=data.get("subtype") if data.get("is_error") else None,
                           log=str(data.get("result", ""))[-4000:])

    if family == "opencode":
        if not model:
            return AgentResult(False, error="opencode needs provider/model, e.g. opencode:opencode/glm-5.3-flash-free")
        with open(os.path.join(workdir, "opencode.json"), "w", encoding="utf-8") as f:
            json.dump(OPENCODE_SANDBOX, f, indent=2)
        proc, err = _run(["opencode", "run", "--dir", workdir, "-m", model, prompt], workdir, task.timeout)
        if err:
            return AgentResult(False, error=err)
        return AgentResult(proc.returncode == 0, error=None if proc.returncode == 0 else "exit %d" % proc.returncode,
                           log=(proc.stdout + proc.stderr)[-4000:])

    return AgentResult(False, error="unknown agent %r" % spec)


def timed_attempt(spec, task, workdir, with_tidos, budget_usd=1.0):
    start = time.time()
    result = attempt(spec, task, workdir, with_tidos, budget_usd)
    return result, round(time.time() - start, 1)
