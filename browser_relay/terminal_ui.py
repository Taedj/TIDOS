"""Terminal UI and colored chat stream formatter for GPTID (stdlib only).

Provides rich ANSI color formatting for console logs and interactive
consultations between TIDOS and ChatGPT.

Colors:
  - TIDOS Prompts & Outgoing Tasks: Vibrant Cyan / Blue
  - ChatGPT Responses & Analysis: Emerald Mint Green
  - System Badges & Metadata: Gold / Yellow and Dim Gray
  - Errors & Alerts: Vibrant Red
"""

import os
import sys
import shutil

_COLORS_INITIALIZED = False
_CAN_UTF8 = False


def init_colors():
    """Ensure Windows console has VT100 / ANSI escape processing enabled and UTF-8 output."""
    global _COLORS_INITIALIZED, _CAN_UTF8
    if _COLORS_INITIALIZED:
        return
    _COLORS_INITIALIZED = True

    # Ensure UTF-8 output stream on Windows
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        _CAN_UTF8 = True
    except Exception:
        enc = getattr(sys.stdout, "encoding", "") or ""
        _CAN_UTF8 = "utf" in enc.lower()

    if os.name == "nt":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            h_stdout = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(h_stdout, ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(h_stdout, mode.value | 0x0004)
        except Exception:
            pass
        try:
            os.system("")  # Standard secondary trigger in Windows cmd/powershell
        except Exception:
            pass


class Ansi:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"

    # Standard / High Intensity Foregrounds
    BLACK = "\033[30m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    GRAY = "\033[90m"

    # Extended accents
    CYAN_VIBRANT = "\033[38;5;51m"
    BLUE_VIBRANT = "\033[38;5;39m"
    GREEN_MINT = "\033[38;5;48m"
    GREEN_EMERALD = "\033[38;5;42m"
    GOLD = "\033[38;5;220m"
    ORANGE = "\033[38;5;208m"
    PURPLE = "\033[38;5;141m"

    # Backgrounds
    BG_CYAN = "\033[48;5;24m"
    BG_GREEN = "\033[48;5;22m"
    BG_DARK = "\033[48;5;236m"


def colors_enabled():
    """True if output can support color sequences."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return True


def style(text, *codes):
    if not colors_enabled() or not codes:
        return text
    prefix = "".join(codes)
    return "%s%s%s" % (prefix, text, Ansi.RESET)


def _term_width(default=78, cap=86):
    try:
        cols = shutil.get_terminal_size((default, 24)).columns
        return max(40, min(cols, cap))
    except Exception:
        return default


def _safe_char(utf_char, ascii_char):
    return utf_char if _CAN_UTF8 else ascii_char


def print_tidos_banner(mode, task_id=None, session_id=None, objective=None, context_keys=None):
    """Render the outgoing TIDOS request box in Vibrant Cyan."""
    init_colors()
    width = _term_width()
    bar = _safe_char("─", "-") * (width - 24)
    vbar = _safe_char("│", "|")
    tl = _safe_char("┌──", "+--")
    bl = _safe_char("└──", "+--")
    arrow = _safe_char("➜", "->")

    header = "%s %s %s" % (
        tl,
        style("[TIDOS %s CHATGPT]" % arrow, Ansi.BOLD, Ansi.CYAN_VIBRANT),
        style(bar, Ansi.CYAN)
    )
    print("\n" + header)

    meta_parts = ["Mode: %s" % style(str(mode).upper(), Ansi.BOLD, Ansi.CYAN)]
    if session_id:
        meta_parts.append("Session: %s" % style(session_id[:16], Ansi.GRAY))
    if task_id:
        meta_parts.append("Task: %s" % style(task_id[:16], Ansi.GRAY))
    if context_keys:
        meta_parts.append("Context: %s" % style(str(context_keys), Ansi.YELLOW))

    print("%s  %s" % (style(vbar, Ansi.CYAN), " • ".join(meta_parts) if _CAN_UTF8 else " | ".join(meta_parts)))
    print("%s" % style(vbar, Ansi.CYAN))

    if objective:
        prompt_label = "[TIDOS Prompt / Objective]"
        print("%s  %s" % (style(vbar, Ansi.CYAN), style(prompt_label, Ansi.BOLD, Ansi.WHITE)))
        for line in str(objective).strip().splitlines():
            print("%s    %s" % (style(vbar, Ansi.CYAN), style(line, Ansi.WHITE)))

    footer = "%s%s" % (bl, style(_safe_char("─", "-") * (width - 4), Ansi.CYAN))
    print(footer + "\n")


def print_chatgpt_response(content, task_id=None, session_id=None, correlated=True, chars=None):
    """Render the incoming ChatGPT response box in Fresh Mint Green."""
    init_colors()
    width = _term_width()
    bar = _safe_char("─", "-") * (width - 26)
    vbar = _safe_char("│", "|")
    tl = _safe_char("┌──", "+--")
    bl = _safe_char("└──", "+--")
    arrow = _safe_char("➜", "->")

    header = "%s %s %s" % (
        tl,
        style("[CHATGPT %s TIDOS]" % arrow, Ansi.BOLD, Ansi.GREEN_MINT),
        style(bar, Ansi.GREEN_EMERALD)
    )
    print("\n" + header)

    total_chars = chars if chars is not None else len(content or "")
    corr_badge = style("VERIFIED", Ansi.BOLD, Ansi.GREEN) if correlated else style("MISMATCH", Ansi.BOLD, Ansi.RED)

    meta_parts = [
        "Status: %s" % style("RECEIVED", Ansi.BOLD, Ansi.GREEN_MINT),
        "Chars: %s" % style(str(total_chars), Ansi.BOLD, Ansi.WHITE),
        "Correlation: %s" % corr_badge,
        "Source: %s" % style("chatgpt-untrusted", Ansi.YELLOW)
    ]
    delim = " • " if _CAN_UTF8 else " | "
    print("%s  %s" % (style(vbar, Ansi.GREEN_EMERALD), delim.join(meta_parts)))
    print("%s" % style(vbar, Ansi.GREEN_EMERALD))
    print("%s  %s" % (
        style(vbar, Ansi.GREEN_EMERALD),
        style("[Extracted Response]", Ansi.BOLD, Ansi.GREEN_MINT)
    ))
    print("%s" % style(vbar, Ansi.GREEN_EMERALD))

    body_text = str(content or "").strip()
    for line in body_text.splitlines():
        print("%s  %s" % (style(vbar, Ansi.GREEN_EMERALD), style(line, Ansi.GREEN)))

    footer = "%s%s" % (bl, style(_safe_char("─", "-") * (width - 4), Ansi.GREEN_EMERALD))
    print(footer + "\n")


def print_chat_turn(speaker, text):
    """Format an ongoing multi-turn interactive discussion."""
    init_colors()
    spk = str(speaker).upper()
    if "TIDOS" in spk or "YOU" in spk:
        tag = style("[%s]" % speaker, Ansi.BOLD, Ansi.CYAN_VIBRANT)
        body = style(text, Ansi.WHITE)
        print("\n%s\n%s" % (tag, body))
    elif "CHATGPT" in spk or "AI" in spk or "PARTNER" in spk:
        tag = style("[%s]" % speaker, Ansi.BOLD, Ansi.GREEN_MINT)
        body = style(text, Ansi.GREEN)
        print("\n%s\n%s" % (tag, body))
    else:
        tag = style("[%s]" % speaker, Ansi.BOLD, Ansi.YELLOW)
        body = style(text, Ansi.WHITE)
        print("\n%s\n%s" % (tag, body))


def print_relay_badge(badge, message, level="INFO"):
    """Format system / relay status notices."""
    init_colors()
    lvl = str(level).upper()
    if lvl in ("ERROR", "FAIL"):
        tag = style("[%s]" % badge, Ansi.BOLD, Ansi.RED)
        msg = style(message, Ansi.RED)
    elif lvl in ("WARN", "WARNING", "QUEUED"):
        tag = style("[%s]" % badge, Ansi.BOLD, Ansi.GOLD)
        msg = style(message, Ansi.GOLD)
    elif lvl in ("SUCCESS", "READY", "OK"):
        tag = style("[%s]" % badge, Ansi.BOLD, Ansi.GREEN)
        msg = style(message, Ansi.GREEN)
    else:
        tag = style("[%s]" % badge, Ansi.BOLD, Ansi.CYAN)
        msg = style(message, Ansi.WHITE)
    print("%s %s" % (tag, msg))
