"""Second opinion from a DIFFERENT model on the current changes - the supported replacement for GPTID.

  python -I tidos_session/__main__.py review [--with claude:sonnet | opencode:<provider/model>] [--project DIR]

The git diff (sanitized: secrets, user paths, e-mails redacted; capped) goes to the chosen model through its
official CLI. The reviewer never edits anything: Claude gets no tools; OpenCode runs in a temp folder with edits,
shell and web access denied. The answer is reviewer input only - TIDOS and the user decide.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

MAX_DIFF = 60_000
PROMPT = """You are an independent code reviewer giving a second opinion. Review this git diff.
Report only real problems, most severe first: bugs (edge cases, None/null, off-by-one, error handling), regressions
for callers, security issues, and requirements that look unmet. For each: file:line, a concrete failure scenario, and
the fix. If you find nothing blocking, say "No blocking issues" and list at most 3 minor notes. Be concise.

{diff}"""


def collect_diff(project, staged=False):
    args = ["git", "diff", "--cached"] if staged else ["git", "diff", "HEAD"]
    try:
        proc = subprocess.run(args, cwd=project, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=60)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, "git diff failed: %s" % e
    if proc.returncode != 0:
        return None, proc.stderr.strip() or "not a git repository"
    diff = proc.stdout
    scripts = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    sys.path.insert(0, scripts)
    import sanitizer  # privacy firewall: nothing private leaves the machine
    diff = sanitizer.sanitize_text(diff)
    if len(diff) > MAX_DIFF:
        diff = diff[:MAX_DIFF] + "\n... [diff truncated at %d characters]\n" % MAX_DIFF
    return diff, None


def _env():
    return {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}


def ask_claude(model, prompt):
    exe = shutil.which("claude")
    if not exe:
        return None, "claude CLI not found"
    proc = subprocess.run([exe, "-p", "--model", model or "sonnet", "--output-format", "json", "--max-budget-usd", "0.5"],
                          input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=600, env=_env(), cwd=tempfile.gettempdir())
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None, (proc.stderr or proc.stdout)[-500:]
    return (None, data.get("subtype")) if data.get("is_error") else (data.get("result"), None)


def ask_opencode(model, prompt):
    exe = shutil.which("opencode")
    if not exe:
        return None, "opencode CLI not found"
    work = tempfile.mkdtemp(prefix="review-")
    try:
        with open(os.path.join(work, "DIFF.md"), "w", encoding="utf-8") as f:
            f.write(prompt)
        with open(os.path.join(work, "opencode.json"), "w", encoding="utf-8") as f:
            json.dump({"permission": {"edit": "deny", "webfetch": "deny", "bash": {"*": "deny"}}}, f)
        env = dict(_env(), PWD=work)
        proc = subprocess.run([exe, "run", "--dir", work, "-m", model,
                               "Read DIFF.md and do exactly what it says. Reply with the review only."],
                              cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=900, env=env, stdin=subprocess.DEVNULL)
        return (proc.stdout.strip() or None), (None if proc.returncode == 0 else "exit %d" % proc.returncode)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def second_opinion(project, reviewer="claude:sonnet", staged=False, ask=None):
    diff, error = collect_diff(project, staged)
    if error:
        return None, error
    if not diff.strip():
        return None, "no changes to review (git diff is empty)"
    family, _, model = reviewer.partition(":")
    prompt = PROMPT.format(diff=diff)
    if ask:
        text, error = ask(family, model, prompt)
    elif family == "claude":
        text, error = ask_claude(model, prompt)
    elif family == "opencode":
        text, error = ask_opencode(model, prompt)
    else:
        return None, "unknown reviewer %r (use claude:<model> or opencode:<provider/model>)" % reviewer
    if not text:
        return None, error or "the reviewer returned an empty answer"
    return text, None


def same_family_warning(reviewer, session_model):
    """A second opinion is worth more from another model family than the one doing the work."""
    def family(name):
        name = (name or "").lower()
        return "claude" if "claude" in name else name.split("/")[0]

    tool, _, model = reviewer.partition(":")
    reviewer_family = "claude" if tool == "claude" else family(model)
    if session_model and reviewer_family == family(session_model):
        return ("Note: the reviewer is the same model family as this session (%s). For a truly independent "
                "opinion use another family, e.g. --with opencode:google/gemini-2.5-flash." % session_model)
    return None
