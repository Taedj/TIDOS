"""GPTID task protocol: machine-readable task/response schemas, validation, redaction, limits.

Stdlib only. No network. No browser. Import-safe for unit tests.
"""
import json
import re
import uuid
from datetime import datetime, timezone

PROTOCOL_VERSION = "1.0.0"

MODES = ("REVIEW", "AUDIT", "ARCHITECT", "DEBUG", "UIUX", "TRADING_REVIEW")

CONTEXT_KINDS = (
    "PROJECT_SUMMARY", "CURRENT_TASK", "RELEVANT_FILES", "RELEVANT_CODE",
    "TEST_RESULTS", "ANALYZER_RESULTS", "ERROR_LOGS", "RECENT_CHANGES",
    "ARCHITECTURE_SUMMARY",
)

TASK_REQUIRED = (
    "task_id", "session_id", "persona", "mode", "objective", "context",
    "scope", "constraints", "questions", "requested_output_format",
)

RESPONSE_REQUIRED = (
    "task_id", "session_id", "status", "chatgpt_response",
    "structured_findings", "recommendations", "uncertainties", "errors", "timestamp",
)

STATUS_VALUES = ("OK", "UNAVAILABLE", "TIMEOUT", "MALFORMED", "REJECTED", "ERROR")

DEFAULT_LIMITS = {
    "max_context_chars": 6000,
    "max_files": 8,
    "max_response_chars": 12000,
    "max_history": 5,
    "timeout_seconds": 30,
    "response_timeout_seconds": 180,
}

# Anything matching these patterns must never cross the GPTID protocol or logs.
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|apikey)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(password|passwd|pwd)\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(auth[_-]?token|access[_-]?token|refresh[_-]?token|id[_-]?token|bearer)\b\s*[:=]?\s*\S+"),
    re.compile(r"(?i)\bssid\b\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(deriv[_-]?token|pocket[_-]?ssid|broker[_-]?secret)\b\s*[:=]\s*\S+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)cookie\s*[:=]\s*\S+"),
    re.compile(r"(?i)set-cookie\s*:\s*\S+"),
)

REDACTED = "[REDACTED]"


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_task_id(prefix="gtask"):
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


def new_session_id(prefix="gsess"):
    return "%s-%s" % (prefix, uuid.uuid4().hex[:12])


def contains_secret(text):
    if not text:
        return False
    return any(p.search(text) for p in SECRET_PATTERNS)


def redact_secrets(text):
    """Replace secret-looking material with [REDACTED]. Never raises on bad input."""
    if text is None:
        return ""
    out = str(text)
    for p in SECRET_PATTERNS:
        out = p.sub(REDACTED, out)
    return out


def truncate(text, limit):
    text = "" if text is None else str(text)
    if limit is not None and len(text) > limit:
        return text[:limit] + "\n…[truncated %d chars]" % (len(text) - limit)
    return text


def build_context_package(parts, limits=None):
    """Assemble a bounded context string from {KIND: text} parts.

    Unknown kinds are kept (explicitly labelled) but bounded like the rest.
    Returns (context_str, included_kinds, dropped).
    """
    lim = dict(DEFAULT_LIMITS)
    if limits:
        lim.update(limits)
    included, dropped, chunks = [], [], []
    budget = lim["max_context_chars"]
    for kind, body in (parts or {}).items():
        body = redact_secrets(body)
        if len(body) > budget and budget > 0:
            body = truncate(body, budget)
            dropped.append("%s:truncated" % kind)
        if len(body) > budget:
            dropped.append("%s:dropped" % kind)
            continue
        budget -= len(body)
        included.append(kind)
        chunks.append("### %s\n%s" % (kind, body))
        if len(included) >= lim["max_files"]:
            break
    return "\n\n".join(chunks), included, dropped


def build_task(objective, mode="REVIEW", context="", scope=None, constraints=None,
               questions=None, session_id=None, task_id=None,
               requested_output_format="structured", limits=None):
    """Create a protocol task dict. Raises ValueError on bad mode."""
    if mode not in MODES:
        raise ValueError("unknown mode %r (expected one of %s)" % (mode, ",".join(MODES)))
    lim = dict(DEFAULT_LIMITS)
    if limits:
        lim.update(limits)
    task = {
        "protocol": "gptid/1",
        "protocol_version": PROTOCOL_VERSION,
        "task_id": task_id or new_task_id(),
        "session_id": session_id or new_session_id(),
        "persona": "GPTID",
        "mode": mode,
        "objective": redact_secrets(truncate(objective, lim["max_context_chars"])),
        "context": redact_secrets(truncate(context, lim["max_context_chars"])),
        "scope": list(scope or []),
        "constraints": list(constraints or []),
        "questions": list(questions or []),
        "requested_output_format": requested_output_format,
    }
    return task


def validate_task(task):
    """Return a list of error strings (empty = valid). Never raises."""
    errors = []
    if not isinstance(task, dict):
        return ["task is not an object"]
    for key in TASK_REQUIRED:
        if key not in task:
            errors.append("missing field: %s" % key)
    if task.get("persona") != "GPTID":
        errors.append("persona must be GPTID")
    if task.get("mode") not in MODES:
        errors.append("unknown mode: %r" % (task.get("mode"),))
    for blob_key in ("objective", "context"):
        if blob_key in task and contains_secret(str(task[blob_key])):
            errors.append("%s contains secret material" % blob_key)
    return errors


def build_response(task_id, session_id, chatgpt_response="", status="OK",
                   structured_findings=None, recommendations=None,
                   uncertainties=None, errors=None):
    if status not in STATUS_VALUES:
        raise ValueError("unknown status %r" % (status,))
    body = redact_secrets(chatgpt_response)
    body = truncate(body, DEFAULT_LIMITS["max_response_chars"])
    return {
        "protocol": "gptid/1",
        "protocol_version": PROTOCOL_VERSION,
        "task_id": task_id,
        "session_id": session_id,
        "status": status,
        "chatgpt_response": body,
        "structured_findings": list(structured_findings or []),
        "recommendations": list(recommendations or []),
        "uncertainties": list(uncertainties or []),
        "errors": list(errors or []),
        "timestamp": utc_now_iso(),
    }


def validate_response(resp):
    errors = []
    if not isinstance(resp, dict):
        return ["response is not an object"]
    for key in RESPONSE_REQUIRED:
        if key not in resp:
            errors.append("missing field: %s" % key)
    if resp.get("status") not in STATUS_VALUES:
        errors.append("unknown status: %r" % (resp.get("status"),))
    if "chatgpt_response" in resp and contains_secret(str(resp["chatgpt_response"])):
        errors.append("chatgpt_response contains secret material")
    if resp.get("status") == "OK" and not str(resp.get("chatgpt_response", "")).strip():
        errors.append("OK response has empty chatgpt_response (never accept silent success)")
    return errors


def task_matches_response(task, resp):
    """Correlation check: response must echo the task's ids."""
    return (isinstance(task, dict) and isinstance(resp, dict)
            and task.get("task_id") == resp.get("task_id")
            and task.get("session_id") == resp.get("session_id"))


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def loads(text):
    return json.loads(text)
