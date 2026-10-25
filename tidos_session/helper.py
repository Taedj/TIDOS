"""TIDOS's helper model: the model TIDOS itself uses for its own jobs (advice notes, Ask TIDOS, self-improve).

TIDOS is no-cost by design and works with any model:
  auto                      (default) a FREE model you already use through OpenCode (OpenCode reaches Gemini, OpenAI,
                            local Ollama, free hosted models ...); no free model -> TIDOS stays local-only
  opencode:<provider/model> that model through the OpenCode CLI
  claude:<model>            Claude Code (your own subscription); only if you choose it
  none                      never call a model: every feature uses local facts only
The choice lives in ~/.tidos/control.json ("helper_model"), editable in the control center.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

from tidos_brain import control

PATTERN = re.compile(r"^(auto|none|claude:[A-Za-z0-9.\-]+|opencode:[A-Za-z0-9._\-]+/[A-Za-z0-9._\-/]+)$")
FREE_FALLBACK = ["opencode/big-pickle", "opencode/glm-5.3-flash-free"]
TIMEOUT = 600


def _env():
    return {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "CLAUDE_CODE_ENTRYPOINT")}


def free_models(conn=None):
    """Free OpenCode models: the ones you used (most used first), then known free defaults."""
    used = []
    if conn is not None:
        used = [r[0] for r in conn.execute(
            "SELECT model, COUNT(*) n FROM sessions WHERE source = 'opencode' AND model IS NOT NULL GROUP BY model "
            "ORDER BY n DESC") if r[0] and ("free" in r[0] or r[0] == "opencode/big-pickle")]
    return used + [m for m in FREE_FALLBACK if m not in used]


def resolve(choice=None, conn=None):
    """'family:model' to use, or None (local-only). 'auto' never picks a paid model."""
    choice = choice or control.text("helper_model")
    if choice == "none":
        return None
    if choice != "auto":
        return choice
    if not shutil.which("opencode"):
        return None
    models = free_models(conn)
    return "opencode:" + models[0] if models else None


def describe(conn=None):
    chosen = control.text("helper_model")
    model = resolve(chosen, conn)
    return {"setting": chosen, "model": model,
            "note": "local facts only (no model available)" if not model else
                    "free model" if model.startswith("opencode:") and ("free" in model or "big-pickle" in model) else
                    "your choice"}


def ask(prompt, choice=None, conn=None, timeout=TIMEOUT):
    """Text in, text out, with NO tools (no files, shell or web). Returns (text, error).
    'auto' tries the free models one after another: free providers are sometimes down."""
    choice = choice or control.text("helper_model")
    model = resolve(choice, conn)
    if not model:
        return None, "no helper model (TIDOS works local-only; choose one in the control center)"
    candidates = [model]
    if choice == "auto":
        candidates += ["opencode:" + m for m in free_models(conn) if "opencode:" + m != model][:2]
    errors = []
    for candidate in candidates:
        family, _, name = candidate.partition(":")
        text, error = (_ask_claude if family == "claude" else _ask_opencode)(name, prompt, timeout)
        if text:
            return text, None
        errors.append("%s: %s" % (name, error))
    return None, "; ".join(errors)


def _ask_claude(model, prompt, timeout):
    exe = shutil.which("claude")
    if not exe:
        return None, "claude CLI not found"
    try:  # the budget cap is only an internal safety net for users who chose Claude
        proc = subprocess.run([exe, "-p", "--model", model, "--output-format", "json", "--max-budget-usd", "0.05",
                               "--tools", "", "--strict-mcp-config"],
                              input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, env=_env(), cwd=tempfile.gettempdir())
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (subprocess.TimeoutExpired, ValueError, IndexError, OSError) as e:
        return None, str(e)
    return (None, data.get("subtype") or "error") if data.get("is_error") else (data.get("result", ""), None)


def answer_text(jsonl):
    """The model's words from `opencode run --format json` events (tool activity is left out)."""
    texts = []
    for line in (jsonl or "").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        part = event.get("part") or {}
        if event.get("type") == "text" and part.get("text"):
            texts.append(part["text"].strip())
    return "\n".join(t for t in texts if t).strip()


def _ask_opencode(model, prompt, timeout):
    exe = shutil.which("opencode")
    if not exe:
        return None, "opencode CLI not found"
    work = tempfile.mkdtemp(prefix="tidos-helper-")
    try:  # the question goes in a file (long prompts break the Windows .cmd wrapper); every tool is denied
        with open(os.path.join(work, "QUESTION.md"), "w", encoding="utf-8") as f:
            f.write(prompt)
        with open(os.path.join(work, "opencode.json"), "w", encoding="utf-8") as f:
            json.dump({"$schema": "https://opencode.ai/config.json",
                       "permission": {"edit": "deny", "webfetch": "deny", "bash": {"*": "deny"}}}, f)
        proc = subprocess.run([exe, "run", "--format", "json", "--dir", work, "-m", model,
                               "Read QUESTION.md and answer it exactly as it asks. Reply with the answer only."],
                              cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, env=dict(_env(), PWD=work), stdin=subprocess.DEVNULL)
        text = answer_text(proc.stdout)
        return (text or None), (None if text else "exit %d, no answer" % proc.returncode)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, str(e)
    finally:
        shutil.rmtree(work, ignore_errors=True)
