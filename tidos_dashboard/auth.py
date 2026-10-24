"""/TIDOSZIT authentication: Google owner check + control password, sessions, lockout.

Flow:
  1. Browser signs in with Google (Firebase Web SDK) and POSTs the ID token.
     Server verifies it with Google and requires uid == owner_uid -> "pending" session (5 min).
  2. Browser POSTs the control password (typed in the page, never through the AI chat).
     Server reads the PBKDF2 hash from Firestore with the owner's token and verifies it
     -> full session cookie (30 min). First run: the owner sets the password instead.
  5 failed passwords within 15 min -> 15 min lockout. Every attempt goes to brain.security_log.
"""
import base64
import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone

ALGO = "pbkdf2_sha256"
ITERATIONS = 600_000            # OWASP 2023+ guidance for PBKDF2-HMAC-SHA256
MIN_PASSWORD_LENGTH = 10
PENDING_TTL = 5 * 60
SESSION_TTL = 30 * 60
MAX_FAILURES = 5
LOCKOUT_SECONDS = 15 * 60


def hash_password(password, iterations=ITERATIONS):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return {"algo": ALGO, "iterations": iterations,
            "salt": base64.b64encode(salt).decode(), "hash": base64.b64encode(digest).decode(),
            "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def verify_password(password, record):
    if not record or record.get("algo") != ALGO:
        return False
    try:
        salt = base64.b64decode(record["salt"])
        expected = base64.b64decode(record["hash"])
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(record["iterations"]))
    except (KeyError, ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def password_problem(password):
    """Return why a new password is too weak, or None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return "Use at least %d characters." % MIN_PASSWORD_LENGTH
    classes = sum([any(c.islower() for c in password), any(c.isupper() for c in password),
                   any(c.isdigit() for c in password), any(not c.isalnum() for c in password)])
    if classes < 3:
        return "Mix at least 3 of: lowercase, uppercase, digits, symbols."
    return None


class Sessions:
    """In-memory session store (a server restart logs everyone out — by design)."""

    def __init__(self, clock=time.time):
        self._clock = clock
        self._lock = threading.Lock()
        self._items = {}

    def create(self, stage, data):
        token = secrets.token_urlsafe(32)
        ttl = PENDING_TTL if stage == "pending" else SESSION_TTL
        with self._lock:
            self._items[token] = {"stage": stage, "expires": self._clock() + ttl, **data}
        return token

    def get(self, token, stage=None):
        if not token:
            return None
        with self._lock:
            item = self._items.get(token)
            if item and item["expires"] < self._clock():
                del self._items[token]
                item = None
        if item and stage and item["stage"] != stage:
            return None
        return item

    def drop(self, token):
        with self._lock:
            self._items.pop(token, None)

    def remaining(self, token):
        item = self.get(token)
        return max(0, int(item["expires"] - self._clock())) if item else 0


class Lockout:
    """Brute-force protection backed by brain.security_log (survives restarts)."""

    def __init__(self, conn_factory, clock=lambda: datetime.now(timezone.utc)):
        self._conn = conn_factory
        self._clock = clock

    def log(self, event, detail=""):
        conn = self._conn()
        with conn:
            conn.execute("INSERT INTO security_log (ts, event, detail) VALUES (?,?,?)",
                         (self._clock().isoformat(timespec="seconds"), event, detail))
        conn.close()

    def locked_until(self):
        """Return the datetime the lockout ends, or None."""
        conn = self._conn()
        window_start = (self._clock() - timedelta(seconds=LOCKOUT_SECONDS)).isoformat(timespec="seconds")
        last_ok = conn.execute("SELECT MAX(ts) FROM security_log WHERE event = 'login_ok'").fetchone()[0]
        since = max(window_start, last_ok or "")
        rows = conn.execute("SELECT ts FROM security_log WHERE event = 'login_fail' AND ts > ? ORDER BY ts",
                            (since,)).fetchall()
        conn.close()
        if len(rows) < MAX_FAILURES:
            return None
        until = datetime.fromisoformat(rows[-1][0]) + timedelta(seconds=LOCKOUT_SECONDS)
        return until if until > self._clock() else None

    def failures_left(self):
        conn = self._conn()
        window_start = (self._clock() - timedelta(seconds=LOCKOUT_SECONDS)).isoformat(timespec="seconds")
        last_ok = conn.execute("SELECT MAX(ts) FROM security_log WHERE event = 'login_ok'").fetchone()[0]
        n = conn.execute("SELECT COUNT(*) FROM security_log WHERE event = 'login_fail' AND ts > ?",
                         (max(window_start, last_ok or ""),)).fetchone()[0]
        conn.close()
        return max(0, MAX_FAILURES - n)
