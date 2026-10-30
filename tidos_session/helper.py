"""TIDOS's helper model: the model TIDOS itself uses for its own jobs (advice notes, Ask TIDOS, self-improve).

Nothing to choose: TIDOS uses the model you are working with. Every START TIDOS records the tool and model
(~/.tidos/session.json), and TIDOS reaches that same model through the tool's own command line:
  Claude Code -> claude      OpenCode -> opencode (Gemini, OpenAI, local Ollama, free models...)
  Gemini CLI  -> gemini
IDEs without a command line (Antigravity, Cursor, Windsurf...) and missing CLIs fall back to a FREE model you
already use through OpenCode; if a model fails, the next free one is tried; with none TIDOS works local-only.
Optional override in ~/.tidos/control.json "helper_model": auto (default) | none | opencode:<provider/model> |
claude:<model> | gemini:<model>.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

from tidos_brain import control

PATTERN = re.compile(r"^(auto|none|claude:[A-Za-z0-9.\-]+|gemini:[A-Za-z0-9.\-]+|"
                     r"opencode:[A-Za-z0-9._\-]+/[A-Za-z0-9._\-/]+)$")
CLIS = {"claude": "claude", "opencode": "opencode", "gemini": "gemini"}
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


def session_model():
    """(family:model or None, tool, model) from the last START TIDOS."""
    from tidos_session.detect import tidos_home
    try:
        with open(os.path.join(tidos_home(), "session.json"), "r", encoding="utf-8") as f:
            s = json.load(f)
    except (OSError, ValueError):
        return None, None, None
    tool, model = s.get("tool"), s.get("model")
    if not model or model in ("unknown", "auto"):
        return None, tool, model
    family = {"claude-code": "claude", "opencode": "opencode", "gemini-cli": "gemini"}.get(tool)
    if family == "opencode" and "/" not in model:
        family = None
    route = "%s:%s" % (family, model) if family else None
    return (route if route and PATTERN.match(route) else None), tool, model


def _free(conn=None):
    if not shutil.which("opencode"):
        return None
    models = free_models(conn)
    return "opencode:" + models[0] if models else None


def resolve(choice=None, conn=None):
    """'family:model' to use, or None (local-only). auto = the model of your last START TIDOS, else free."""
    choice = choice or control.text("helper_model")
    if choice == "none":
        return None
    if choice != "auto":
        return choice
    route, _, _ = session_model()
    if route and shutil.which(CLIS[route.split(":", 1)[0]]):
        return route
    return _free(conn)


def background(conn=None):
    """Model for unattended work (autopilot): a free model, never your working model by surprise.
    An explicit helper_model setting is respected; 'auto' means free here. None: no free model, skip the job."""
    choice = control.text("helper_model")
    if choice == "none":
        return None
    if choice != "auto":
        return choice
    return _free(conn)


def describe(conn=None):
    """What the control center shows: the model in use and where it came from."""
    chosen = control.text("helper_model")
    model = resolve(chosen, conn)
    route, tool, session = session_model()
    if not model:
        note = "local facts only (no model available)"
    elif chosen != "auto":
        note = "set in control.json"
    elif route and model == route:
        note = "from your last START TIDOS"
    elif tool and session:
        note = "free fallback: %s has no command line TIDOS can use" % tool
    else:
        note = "free fallback: no START TIDOS yet"
    return {"setting": chosen, "model": model, "tool": tool, "session_model": session, "note": note}


def ask(prompt, choice=None, conn=None, timeout=TIMEOUT):
    """Text in, text out, with NO tools (no files, shell or web). Returns (text, error).
    'auto' tries the free models one after another: free providers are sometimes down."""
    choice = choice or control.text("helper_model")
    model = resolve(choice, conn)
    if not model:
        return None, "no helper model (TIDOS works local-only; choose one in the control center)"
    candidates = [model]
    if choice == "auto":  # the session model first, then free models
        candidates += ["opencode:" + m for m in free_models(conn) if "opencode:" + m != model][:2]
    errors = []
    for candidate in candidates:
        family, _, name = candidate.partition(":")
        text, error = {"claude": _ask_claude, "gemini": _ask_gemini}.get(family, _ask_opencode)(name, prompt, timeout)
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


def _ask_gemini(model, prompt, timeout):
    """Gemini CLI, headless: the prompt arrives on stdin; tools are not auto-approved in this mode."""
    exe = shutil.which("gemini")
    if not exe:
        return None, "gemini CLI not found"
    try:
        proc = subprocess.run([exe, "-m", model, "-p", "Answer the question above. Reply with the answer only."],
                              input=prompt, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              timeout=timeout, env=_env(), cwd=tempfile.gettempdir())
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, str(e)
    text = proc.stdout.strip()
    return (text or None), (None if proc.returncode == 0 and text else "exit %d" % proc.returncode)


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
