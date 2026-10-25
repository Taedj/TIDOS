"""Who may open THIS computer's control center, and with which role.

Anyone can use TIDOS with their own Google account; there is no separate sign-up.
  - The first Google account that signs in on a computer CLAIMS this installation (~/.tidos/install.json):
    from then on only that account can open this control center (it shows this computer's private brain).
  - Role "owner" = the TIDOS developer (ownerUid in config/firebase.md): everything, plus the Community tab
    (contributions from all users) - enforced again by the Firestore rules, not only by this file.
  - Role "user" = everyone else: the full control center for their own TIDOS.
Each account has its own control password: the owner's hash lives in admin/tidoszit, a user's in
users/<uid>/private/tidoszit (Firestore rules: only that account can read or write it).
"""
import json
import os
import uuid
from datetime import datetime, timezone

from tidos_session.detect import tidos_home


def _path():
    return os.path.join(tidos_home(), "install.json")


def load():
    try:
        with open(_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save(data):
    os.makedirs(tidos_home(), exist_ok=True)
    with open(_path() + ".tmp", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)
    os.replace(_path() + ".tmp", _path())


def install_id():
    """A random id for this installation (no personal data): links packs from one computer, nothing else."""
    data = load()
    if not data.get("install_id"):
        data["install_id"] = uuid.uuid4().hex
        _save(data)
    return data["install_id"]


def claimed_uid():
    return load().get("uid")


def check(uid):
    """None if this account may open this control center, else the reason it may not."""
    claimed = claimed_uid()
    if claimed and claimed != uid:
        return "This TIDOS installation belongs to another Google account."
    return None


def claim(uid, email=""):
    data = load()
    if not data.get("uid"):
        data.update(uid=uid, email_hint=(email.split("@")[0][:2] + "***") if email else "",
                    claimed_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
        data.setdefault("install_id", uuid.uuid4().hex)
        _save(data)
    return data


def role(cfg, uid):
    return "owner" if uid and uid == cfg.get("ownerUid") else "user"


def password_doc(cfg, uid):
    return "admin/tidoszit" if role(cfg, uid) == "owner" else "users/%s/private/tidoszit" % uid
