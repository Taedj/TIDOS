"""Token accounting for TIDOS's own injected text: how much the brief costs, and before/after deltas.

There is no tokenizer at startup (one unknown model ids); chars/4 is the standard estimate and is what
GUIDE/GUIDE_LIMIT already calibrates against. Snapshot/compare turns this into a regression check:
  python -I tidos_session/__main__.py stats            show the current brief estimate
  python -I tidos_session/__main__.py stats --save      save it as the baseline
  python -I tidos_session/__main__.py stats --compare   diff against the baseline
"""
import json
import os
import re

from .detect import tidos_home

CHARS_PER_TOKEN = 4
STATS_FILE = "token_stats.json"


def est(text):
    """Estimated tokens for one text: ~4 chars per token is close for English with code."""
    return (len((text or "").encode("utf-8")) + CHARS_PER_TOKEN - 1) // CHARS_PER_TOKEN


def stats(text):
    """{tokens, chars, sections} of a brief or guidance text, split on '## ' headings."""
    sections = {}
    for chunk in re.split(r"^(?=# |## )", text, flags=re.M):
        if not chunk.strip():
            continue
        name = chunk.split("\n", 1)[0].lstrip("#").strip() or "header"
        sections[name] = est(chunk)
    return {"chars": len(text.encode("utf-8")), "tokens": est(text), "sections": sections}


def baseline_path():
    return os.path.join(_home(), STATS_FILE)


def _home():
    try:
        return tidos_home()
    except Exception:  # noqa: BLE001 - stats must never break a session
        return os.getcwd()


def save(text):
    """Snapshot the current brief as the baseline for later --compare runs."""
    data = dict(stats(text), source="brief")
    os.makedirs(_home(), exist_ok=True)
    with open(baseline_path(), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    return data


def load():
    try:
        with open(baseline_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def comparison(text):
    """(current stats, baseline stats or None) - callers format the report."""
    return stats(text), load()
