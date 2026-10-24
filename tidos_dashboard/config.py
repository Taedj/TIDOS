"""Reads Firebase + owner settings from config/firebase.md (the single source of truth)."""
import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIREBASE_MD = os.path.join(REPO_ROOT, "config", "firebase.md")

_KEYS = {
    "project_id": "projectId", "api_key": "apiKey", "auth_domain": "authDomain", "app_id": "appId",
    "storage_bucket": "storageBucket", "messaging_sender_id": "messagingSenderId", "owner_uid": "ownerUid",
}


def load(path=FIREBASE_MD):
    values = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^\s+([a-z_]+):\s*([^\s#]+)", line)
            if m and m.group(1) in _KEYS and _KEYS[m.group(1)] not in values:
                values[_KEYS[m.group(1)]] = m.group(2)
    missing = {"projectId", "apiKey", "authDomain", "appId", "ownerUid"} - set(values)
    if missing:
        raise ValueError("config/firebase.md is missing: %s" % ", ".join(sorted(missing)))
    return values


def web_config(cfg):
    """The public Firebase Web SDK config sent to the browser (no owner UID)."""
    return {k: cfg[k] for k in ("apiKey", "authDomain", "projectId", "appId", "storageBucket",
                                "messagingSenderId") if k in cfg}
