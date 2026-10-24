"""Outcome scoring for traced tasks (v1 heuristics, refined later by evals).

score in [0, 1]:
  base 0.5
  +0.3  last verification passed      -0.3  last verification failed
  -0.3  the user's next prompt was a correction
  -0.05 per tool error (max -0.2)
outcome: success >= 0.7, failure <= 0.3, else unknown
"""
import re

TOOL_KINDS = {
    "Read": "read", "NotebookRead": "read",
    "Grep": "search", "Glob": "search", "LS": "search",
    "Edit": "edit", "MultiEdit": "edit", "Write": "edit", "NotebookEdit": "edit",
    "Bash": "exec", "PowerShell": "exec",
    "Agent": "delegate", "Task": "delegate",
    "WebFetch": "web", "WebSearch": "web",
}

# Commands that verify work: tests, linters, type checkers, builds
VERIFY_COMMAND = re.compile(
    r"(?i)\b(pytest|unittest|tox|nox|npm (run )?test|pnpm test|yarn test|vitest|jest|"
    r"flutter (test|analyze)|dart (test|analyze)|cargo (test|check|clippy|build)|go (test|vet|build)|"
    r"gradlew?\b.*\b(test|build|assemble)|mvn (test|verify)|dotnet (test|build)|"
    r"ruff|flake8|pylint|mypy|pyright|tsc\b|eslint|py_compile|shellcheck|Invoke-ScriptAnalyzer|"
    r"Invoke-Pester|make (test|check))\b"
)

_FAILED_OUTPUT = re.compile(r"(?i)(\b\d+ (failed|errors?)\b|\bFAILED\b|\bTraceback \(most recent call last\)|"
                            r"\berror(\[E\d+\])?:|\bBUILD FAILED\b|\bTests? failed\b)")
_ZERO_FAILED = re.compile(r"(?i)\b0 (failed|errors?)\b")

# The user's next prompt says the previous answer was wrong (English + French)
CORRECTION = re.compile(
    r"(?i)^\s*(no\b|nope|wrong|that'?s (not|wrong)|not what i|doesn'?t work|does not work|didn'?t work|"
    r"still (fails|broken|not)|you (broke|forgot|missed)|revert|undo|"
    r"non\b|faux|ça (ne )?marche pas|ca (ne )?marche pas|toujours (pas|le même)|erreur)"
)


def tool_kind(tool_name):
    if tool_name.startswith("mcp__"):
        return "other"
    return TOOL_KINDS.get(tool_name, "other")


def is_verify_command(command):
    return bool(command and VERIFY_COMMAND.search(command))


def verify_passed(is_error, output):
    """Did a verification command pass? Tool error flag first, then output markers."""
    if is_error:
        return False
    text = output or ""
    failed = [m for m in _FAILED_OUTPUT.finditer(text)]
    if not failed:
        return True
    # "0 failed" style summaries are not failures
    return all(_ZERO_FAILED.match(text, m.start()) for m in failed)


def is_correction(prompt):
    return bool(prompt and CORRECTION.search(prompt))


def score_task(verify_passed_last, corrected, tool_errors):
    score = 0.5
    if verify_passed_last is True:
        score += 0.3
    elif verify_passed_last is False:
        score -= 0.3
    if corrected:
        score -= 0.3
    score -= min(0.2, 0.05 * tool_errors)
    score = round(max(0.0, min(1.0, score)), 2)
    outcome = "success" if score >= 0.7 else "failure" if score <= 0.3 else "unknown"
    return score, outcome
