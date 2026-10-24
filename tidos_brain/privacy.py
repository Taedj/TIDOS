"""Every string stored in the brain passes through the TIDOS Privacy Firewall first."""
import os
import sys

_SCRIPTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

import sanitizer  # noqa: E402

MAX_PROMPT_CHARS = 2000
MAX_SUMMARY_CHARS = 300


def clean(text, limit=MAX_SUMMARY_CHARS):
    """Sanitize (secrets, user paths, e-mails, IPs) and truncate."""
    if text is None:
        return None
    text = sanitizer.sanitize_text(str(text))
    if len(text) > limit:
        text = text[: limit - 15] + " ...[truncated]"
    return text
