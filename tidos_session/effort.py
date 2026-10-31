"""Effort classification for ONE user request: fast / guide / deep.

FAST (default): trivial changes, simple questions, formatting, small fixes -> no guide call, no playbook.
GUIDE: medium coding tasks -> the per-request guidance (playbook, pitfalls, notes).
DEEP: complex debugging, architecture work, multi-file tasks -> guidance + small-plan discipline.

FAST is the default on purpose ("buy milk", "Phase 1", anything the rules cannot read): the cheap path
costs a fraction of the tokens. Validation never goes away (write check first, run checks, show proof),
so fast only skips the narrative, never the verification.
"""
import re

from tidos_learn.classify import _COMPILED, task_type  # ONE classifier: reuse its rules, no duplicate word list

DEEP_RULES = re.compile(
    r"\b(architect\w*|redesign|migrat\w*|restructur\w*|whole (system|project|codebase|app)|"
    r"(multi|several) files|many files|systematic|root cause|investigat\w*|security (audit|review)|"
    r"performance (issue|problem|work)|refactor\b|big (change|feature)|from scratch|rewrite)", re.I)
FASTISH_RULES = re.compile(
    r"\b(typo|spelling|grammar|format(ting)?|indent\w*|renam\w*|tweak|polish|cosmetic|wording|"
    r"capitaliz\w*|translate|one ?-?liner)\b", re.I)


def classify(request):
    """'fast' | 'guide' | 'deep' for a raw user request (before any tool call)."""
    text = (request or "").strip()
    if not text:
        return "fast"
    level = "deep" if DEEP_RULES.search(text) else None
    if level:
        return level
    if FASTISH_RULES.search(text):
        return "fast"
    # task_type() answers "question" only when no bug/deploy words argue otherwise - trust it there
    if task_type(text) == "question":
        return "fast"
    return "guide" if _compiled_hits(text) else "fast"


def _compiled_hits(text):
    """Any of the learner's own type rules matched -> the words name a real task (bug, ui, feature...)."""
    return any(pattern.search(text) for _, pattern in _COMPILED)
