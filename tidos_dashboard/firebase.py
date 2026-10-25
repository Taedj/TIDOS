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


def _doc_url(cfg, path=PASSWORD_DOC):
    return "https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents/%s" % (
        cfg["projectId"], path)


def refresh_id_token(cfg, refresh_token):
    """Exchange a stored refresh token for a fresh ID token (background uploads). Returns (id_token, uid)."""
    url = "https://securetoken.googleapis.com/v1/token?key=" + urllib.parse.quote(cfg["apiKey"])
    req = urllib.request.Request(url, data=urllib.parse.urlencode(
        {"grant_type": "refresh_token", "refresh_token": refresh_token}).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise FirebaseError("token refresh failed: %s" % e) from None
    return data["id_token"], data["user_id"]


def to_fields(value):
    """Python value -> Firestore REST value (dicts, lists, numbers, strings, booleans)."""
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, dict):
        return {"mapValue": {"fields": {k: to_fields(v) for k, v in value.items()}}}
    if isinstance(value, (list, tuple)):
        return {"arrayValue": {"values": [to_fields(v) for v in value]}}
    if value is None:
        return {"nullValue": None}
    return {"stringValue": str(value)}


def from_fields(value):
    """Firestore REST value -> Python value."""
    if "mapValue" in value:
        return {k: from_fields(v) for k, v in (value["mapValue"].get("fields") or {}).items()}
    if "arrayValue" in value:
        return [from_fields(v) for v in value["arrayValue"].get("values", [])]
    if "integerValue" in value:
        return int(value["integerValue"])
    if "nullValue" in value:
        return None
    return next(iter(value.values()))


def set_doc(cfg, id_token, path, data):
    _request("PATCH", _doc_url(cfg, path), {"fields": {k: to_fields(v) for k, v in data.items()}}, token=id_token)


def query_group(cfg, id_token, collection, limit=500):
    """Every document of a collection group the token may read (the owner's Community tab)."""
    url = "https://firestore.googleapis.com/v1/projects/%s/databases/(default)/documents:runQuery" % cfg["projectId"]
    rows = _request("POST", url, {"structuredQuery": {"from": [{"collectionId": collection, "allDescendants": True}],
                                                      "limit": limit}}, token=id_token)
    out = []
    for row in rows if isinstance(rows, list) else []:
        doc = row.get("document")
        if doc:
            out.append(dict({k: from_fields(v) for k, v in (doc.get("fields") or {}).items()}, _path=doc["name"]))
    return out


def get_password_doc(cfg, id_token, path=PASSWORD_DOC):
    """Return the stored hash record as a plain dict, or None if it was never set."""
    try:
        doc = _request("GET", _doc_url(cfg, path), token=id_token)
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


def set_password_doc(cfg, id_token, record, path=PASSWORD_DOC):
    fields = {}
    for key, value in record.items():
        if isinstance(value, int):
            fields[key] = {"integerValue": str(value)}
        else:
            fields[key] = {"stringValue": str(value)}
    _request("PATCH", _doc_url(cfg, path), {"fields": fields}, token=id_token)
