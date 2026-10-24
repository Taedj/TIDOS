"""Minimal Firebase REST client (stdlib only).

- ID tokens are verified server-side by Google (Identity Toolkit accounts:lookup).
- The password-hash document is read/written with the owner's own ID token, so
  Firestore security rules (firebase/firestore.rules) are the second lock.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 15
PASSWORD_DOC = "admin/tidoszit"


class FirebaseError(Exception):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


def _request(method, url, body=None, token=None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8")).get("error", {}).get("message", "")
        except ValueError:
            detail = ""
        raise FirebaseError("Firebase HTTP %d %s" % (e.code, detail), e.code) from None
    except (urllib.error.URLError, OSError) as e:
        raise FirebaseError("Firebase unreachable: %s" % e) from None


def lookup_user(cfg, id_token):
    """Verify an ID token with Google and return the account (raises if invalid/expired)."""
    url = "https://identitytoolkit.googleapis.com/v1/accounts:lookup?key=" + urllib.parse.quote(cfg["apiKey"])
    users = _request("POST", url, {"idToken": id_token}).get("users") or []
    if not users:
        raise FirebaseError("ID token rejected", 401)
    return users[0]


def _doc_url(cfg):
    return "https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents/%s" % (
        cfg["projectId"], PASSWORD_DOC)


def get_password_doc(cfg, id_token):
    """Return the stored hash record as a plain dict, or None if it was never set."""
    try:
        doc = _request("GET", _doc_url(cfg), token=id_token)
    except FirebaseError as e:
        if e.status == 404:
            return None
        raise
    out = {}
    for key, value in (doc.get("fields") or {}).items():
        if "integerValue" in value:
            out[key] = int(value["integerValue"])
        else:
            out[key] = next(iter(value.values()))
    return out


def set_password_doc(cfg, id_token, record):
    fields = {}
    for key, value in record.items():
        if isinstance(value, int):
            fields[key] = {"integerValue": str(value)}
        else:
            fields[key] = {"stringValue": str(value)}
    _request("PATCH", _doc_url(cfg), {"fields": fields}, token=id_token)
