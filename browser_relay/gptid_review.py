"""GPTID automatic REVIEW policy (TIDOS-side decision layer).

Turns GPTID from a manually invoked transport into an intelligent OPTIONAL
review capability inside the normal TIDOS workflow:

  TIDOS task/change
    -> decide_review()          (this module: SHOULD ChatGPT look at this?)
    -> readiness gate           (existing relay /health machinery, unchanged)
    -> at most ONE bounded REVIEW task per change_id (ledger, no loops)
    -> existing relay transport (AUTO round-trip or MANUAL bridge, unchanged)
    -> result envelope with source=chatgpt-untrusted (provenance preserved)
    -> TIDOS verifies independently; only TIDOS may act on findings.

CORE RULE (enforced by design): this module contains NO code-apply path.
There is deliberately no function here that writes workspace files, patches
code, or executes project actions. A ChatGPT finding becomes actionable only
when TIDOS independently confirms it against the workspace.

Stdlib only. No network. No browser. Import-safe for unit tests.
"""
import json
import os

try:
    from gptid_protocol import (  # noqa: E402
        build_context_package, build_task, utc_now_iso, validate_task,
    )
except ImportError:  # pragma: no cover - direct-script fallback
    from browser_relay.gptid_protocol import (  # noqa: E402
        build_context_package, build_task, utc_now_iso, validate_task,
    )

# Provenance marker. Every result envelope carries it; TIDOS must treat the
# payload as external-untrusted reasoning input, never as a decision.
UNTRUSTED_SOURCE = "chatgpt-untrusted"

# Change kinds that are NEVER worth an external review (deterministic skip).
LOW_VALUE_KINDS = frozenset((
    "trivial", "format", "formatting-only", "docs-only", "typo",
    "one-line-fix", "routine", "dependency-bump",
))

# Change kinds that are ALWAYS worth considering for review.
SIGNIFICANT_KINDS = frozenset((
    "architecture", "cross-cutting", "large-change", "audit-requested",
    "hard-debug", "closeout-review", "ui-consistency", "multi-approach",
))

# Lines-changed heuristic: at or above this, size alone justifies review.
LARGE_CHANGE_LINES = 200

# Default ledger location (outside the repo, next to the relay PID file).
DEFAULT_LEDGER_PATH = os.path.join(os.path.expanduser("~"), ".tidos",
                                   "gptid-reviews.json")


def decide_review(change):
    """Decide whether a TIDOS task/change merits ONE GPTID REVIEW.

    `change` dict fields (all optional except honesty about unknowns):
      kind: one of LOW_VALUE_KINDS / SIGNIFICANT_KINDS / free text
      summary: short human description of the task/change
      scope: list of touched areas/files (may be empty)
      lines_changed: int (0 when unknown)
      alternatives: True when multiple plausible approaches exist
      uncertainty: True when edge cases/omissions are uncertain AND material
      unresolved_debug: True when TIDOS's own investigation already failed
      user_required: True when the user demanded ChatGPT review as a HARD
        requirement (the ONLY case that may block on unavailability)

    Returns (invoke, reason_code, log_line). Deterministic, no I/O.
    Log lines follow the GPTID REVIEW observability vocabulary.
    """
    change = dict(change or {})
    kind = str(change.get("kind", "") or "").strip().lower()
    lines = change.get("lines_changed", 0) or 0
    try:
        lines = int(lines)
    except Exception:
        lines = 0
    alternatives = bool(change.get("alternatives", False))
    uncertainty = bool(change.get("uncertainty", False))
    unresolved = bool(change.get("unresolved_debug", False))

    if kind in LOW_VALUE_KINDS:
        return (False, "low-value-kind",
                "GPTID REVIEW: SKIPPED — low-value task (kind=%s)" % kind)
    if kind in SIGNIFICANT_KINDS:
        return (True, "significant-kind",
                "GPTID REVIEW: REQUESTED — %s" % kind.replace("-", " "))
    if unresolved:
        return (True, "unresolved-debug",
                "GPTID REVIEW: REQUESTED — unresolved debug after TIDOS investigation")
    if alternatives:
        return (True, "multi-approach",
                "GPTID REVIEW: REQUESTED — multiple plausible approaches")
    if uncertainty:
        return (True, "material-uncertainty",
                "GPTID REVIEW: REQUESTED — material uncertainty on edge cases")
    if lines >= LARGE_CHANGE_LINES:
        return (True, "large-change",
                "GPTID REVIEW: REQUESTED — large change (%d lines)" % lines)
    return (False, "no-signal",
            "GPTID REVIEW: SKIPPED — low-value task (no review signal)")


def readiness_ok(health):
    """Evaluate the EXISTING relay /health payload against the REVIEW gate.

    Requires browser READY + ChatGPT READY + page_state READY + tabs > 0,
    with no cross-layer contradiction. Returns (ok, reason). Never probes
    the browser itself — the relay remains the single source of truth.
    """
    health = dict(health or {})
    browser = health.get("browser")
    chatgpt = health.get("chatgpt")
    page_state = health.get("page_state", health.get("state"))
    tabs = health.get("tabs", -1)
    relay_state = health.get("state")
    if chatgpt in ("AUTHENTICATION_REQUIRED", "UNAVAILABLE", "LOADING", "UNKNOWN"):
        return False, "ChatGPT not READY (%s)" % chatgpt
    if browser != "READY":
        return False, "browser not READY (%s)" % browser
    if chatgpt != "READY":
        return False, "ChatGPT not READY (%s)" % chatgpt
    if page_state not in ("READY", "CHATGPT_READY"):
        return False, "page_state not READY (%s)" % page_state
    try:
        if int(tabs) <= 0:
            return False, "no usable tabs (%s)" % tabs
    except Exception:
        return False, "tab count unknown"
    if relay_state == "ERROR":
        return False, "relay in ERROR"
    return True, "GPTID REVIEW: READY"


class ReviewLedger:
    """At-most-ONCE review record per change_id. No review loops, ever.

    Backed by a small JSON file outside the repo (default
    ~/.tidos/gptid-reviews.json). Records invoke AND skip outcomes so a
    repeated identical request resolves identically without re-sending.
    """

    def __init__(self, path=None):
        self.path = path or DEFAULT_LEDGER_PATH
        self._entries = {}
        self._load()

    def _load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self._entries = data
        except Exception:
            self._entries = {}

    def _save(self):
        try:
            parent = os.path.dirname(self.path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as fh:
                json.dump(self._entries, fh, indent=1, sort_keys=True)
        except Exception:
            pass

    def already_reviewed(self, change_id):
        return bool(change_id) and change_id in self._entries

    def record(self, change_id, outcome):
        """outcome: dict with at least status + reason; stored with timestamp."""
        if not change_id:
            return
        entry = dict(outcome or {})
        entry["recorded_at"] = utc_now_iso()
        self._entries[change_id] = entry
        self._save()

    def get(self, change_id):
        return self._entries.get(change_id)


def build_review_prompt(change, questions=None):
    """Build the bounded REVIEW prompt text for ChatGPT.

    Contains: the task/change, objective context, what to check, an explicit
    do-not-modify-code instruction, and a request for findings + evidence +
    uncertainties + omissions. Never includes secrets (caller must redact;
    envelopes are validated downstream by gptid_protocol).
    """
    change = dict(change or {})
    summary = str(change.get("summary", "") or "(no summary given)")[:2000]
    scope = change.get("scope") or []
    lines = [
        "[TIDOS via GPTID | REVIEW — advisory only, do NOT modify any code]",
        "Change under review: %s" % summary,
    ]
    if scope:
        lines.append("Scope: %s" % "; ".join(str(s) for s in scope)[:2000])
    if questions:
        lines.append("Independently check:")
        for q in list(questions)[:12]:
            lines.append("- %s" % q)
    else:
        lines.append("Independently check: correctness, edge cases, omissions, "
                     "and any risk the description overlooks.")
    lines.append("Reply with: concrete findings + supporting evidence + "
                 "uncertainties + potential omissions. No code execution, "
                 "no secrets, no implementation — review only.")
    return "\n".join(lines)


def build_review_task(change, context_parts=None, questions=None,
                      session_id=None, task_id=None):
    """Package ONE bounded REVIEW task envelope (existing protocol, REVIEW)."""
    prompt = build_review_prompt(change, questions)
    context, _included, _dropped = build_context_package(context_parts or {})
    task = build_task(objective=prompt, mode="REVIEW", context=context,
                      scope=list((change or {}).get("scope") or []),
                      constraints=["advisory only; do not modify code",
                                   "no secrets; no execution"],
                      questions=list(questions or []),
                      session_id=session_id, task_id=task_id)
    errors = validate_task(task)
    if errors:
        raise ValueError("invalid REVIEW task: %s" % errors)
    return task


def untrusted_envelope(task, chatgpt_response="", status="OK",
                       failure_reason=""):
    """Wrap a captured (or failed) REVIEW result with explicit provenance.

    The payload is ALWAYS source=chatgpt-untrusted. TIDOS must verify every
    finding against the workspace before anything becomes actionable.
    """
    return {
        "source": UNTRUSTED_SOURCE,
        "task_id": (task or {}).get("task_id", ""),
        "session_id": (task or {}).get("session_id", ""),
        "mode": "REVIEW",
        "status": status,
        "chatgpt_response": chatgpt_response,
        "failure_reason": failure_reason,
        "timestamp": utc_now_iso(),
    }


def verification_checklist():
    """TIDOS-side per-finding checklist (process gate, not automation).

    A finding becomes actionable ONLY when TIDOS marks it VERIFIED against
    repo evidence. No function in this module performs that transition.
    """
    return [
        "GPTID REVIEW: UNTRUSTED RESULT (source=chatgpt-untrusted)",
        "For each finding: locate supporting repo evidence (file:line, test, log).",
        "Mark VERIFIED only with evidence; else REJECTED (no evidence) or "
        "PARTIALLY VERIFIED (needs follow-up probe, still untrusted).",
        "Never implement a finding without a VERIFIED mark from TIDOS.",
    ]
