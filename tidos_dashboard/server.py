"""/TIDOSZIT Control Center HTTP server (stdlib only, 127.0.0.1 only).

Hardening:
  - binds 127.0.0.1; Host header must be localhost/127.0.0.1:<port> (blocks DNS rebinding)
  - every POST must carry a same-origin Origin header (blocks CSRF) + JSON body
  - cookies: HttpOnly, SameSite=Strict, no JS access; sessions live in memory only
  - CSP, X-Frame-Options DENY, no-store on API responses
"""
import json
import mimetypes
import os
import time
from datetime import datetime, timezone
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from tidos_brain import control, db

from . import auth, config, firebase, stats

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
PENDING_COOKIE = "tidoszit_pending"
SESSION_COOKIE = "tidoszit_session"
MAX_BODY = 64 * 1024

CSP = ("default-src 'self'; "
       "script-src 'self' https://www.gstatic.com https://apis.google.com; "
       "connect-src 'self' https://*.googleapis.com https://www.gstatic.com; "
       "frame-src https://*.firebaseapp.com https://accounts.google.com https://apis.google.com; "
       "img-src 'self' data: https://*.googleusercontent.com; "
       "style-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'none'")


class ControlServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port=8767, cfg=None, db_path=None, fb=firebase):
        super().__init__(("127.0.0.1", port), Handler)
        self.port = self.server_address[1]
        self.cfg = cfg or config.load()
        self.db_path = db_path
        self.fb = fb
        self.sessions = auth.Sessions()
        self.lockout = auth.Lockout(lambda: db.connect(self.db_path))
        self.allowed_hosts = {"localhost:%d" % self.port, "127.0.0.1:%d" % self.port}
        self.allowed_origins = {"http://" + h for h in self.allowed_hosts}

    def conn(self):
        return db.connect(self.db_path)


class Handler(BaseHTTPRequestHandler):
    server_version = "TIDOSZIT"
    sys_version = ""

    def log_message(self, fmt, *args):  # no request logs (could contain tokens in bodies)
        return

    # --- helpers -----------------------------------------------------------
    def _cookie(self, name):
        jar = cookies.SimpleCookie(self.headers.get("Cookie", ""))
        return jar[name].value if name in jar else None

    def _headers(self, code, ctype, extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin-allow-popups")
        for k, v in (extra or []):
            self.send_header(k, v)

    def _json(self, code, obj, set_cookies=()):
        body = json.dumps(obj, default=str).encode("utf-8")
        extra = [("Cache-Control", "no-store"), ("Content-Length", str(len(body)))]
        extra += [("Set-Cookie", c) for c in set_cookies]
        self._headers(code, "application/json; charset=utf-8", extra)
        self.end_headers()
        self.wfile.write(body)

    def _set_cookie(self, name, value, max_age):
        return "%s=%s; HttpOnly; SameSite=Strict; Path=/; Max-Age=%d" % (name, value, max_age)

    def _clear_cookie(self, name):
        return "%s=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0" % name

    def _host_ok(self):
        return self.headers.get("Host", "") in self.server.allowed_hosts

    def _read_raw(self):
        """Read the (bounded) body before any refusal, so clients get a clean response, not a reset."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            self.close_connection = True
            raise ValueError("body too large")
        return self.rfile.read(length)

    @staticmethod
    def _parse(raw):
        data = json.loads(raw.decode("utf-8") or "{}")
        if not isinstance(data, dict):
            raise ValueError("JSON object expected")
        return data

    def _session(self):
        return self.server.sessions.get(self._cookie(SESSION_COOKIE), stage="full")

    def _stage(self):
        if self._session():
            return "app"
        pending = self.server.sessions.get(self._cookie(PENDING_COOKIE), stage="pending")
        if pending:
            return "password" if pending["has_password"] else "setup"
        return "login"

    def _lock_info(self):
        until = self.server.lockout.locked_until()
        return {"locked_until": until.isoformat(timespec="seconds") if until else None,
                "failures_left": self.server.lockout.failures_left()}

    # --- GET ---------------------------------------------------------------
    def do_GET(self):
        if not self._host_ok():
            return self._json(421, {"error": "bad host"})
        url = urlparse(self.path)
        path = url.path
        if path == "/" or path.startswith("/static/"):
            return self._static("index.html" if path == "/" else path[len("/static/"):])
        if path == "/api/boot":
            return self._json(200, {"stage": self._stage(), "firebase": config.web_config(self.server.cfg),
                                    **self._lock_info()})

        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        token = self._cookie(SESSION_COOKIE)
        query = parse_qs(url.query)
        conn = self.server.conn()
        try:
            if path == "/api/status":
                data = stats.status(conn)
                data["session"] = {"email": session["email"], "expires_in": self.server.sessions.remaining(token)}
                return self._json(200, data)
            if path == "/api/live":
                since = int((query.get("since") or ["0"])[0])
                return self._json(200, {"events": stats.live(conn, since), "active": stats.active_sessions(conn)})
            if path == "/api/tasks":
                return self._json(200, {"tasks": stats.recent_tasks(conn)})
            if path == "/api/security":
                db_file = self.server.db_path or db.default_path()
                return self._json(200, {"log": stats.security_log(conn), "switches": control.describe(),
                                        "session": {"email": session["email"],
                                                    "expires_in": self.server.sessions.remaining(token)},
                                        "brain": {"path": "~/.tidos/" + os.path.basename(db_file),
                                                  "size_kb": round(os.path.getsize(db_file) / 1024)
                                                  if os.path.exists(db_file) else 0},
                                        **self._lock_info()})
            if path == "/api/stream":
                conn.close()
                conn = None
                return self._stream(token, int((query.get("since") or ["0"])[0]))
            return self._json(404, {"error": "not found"})
        finally:
            if conn is not None:
                conn.close()

    def _static(self, name):
        full = os.path.normpath(os.path.join(STATIC_DIR, name))
        if not full.startswith(STATIC_DIR + os.sep) or not os.path.isfile(full):
            return self._json(404, {"error": "not found"})
        with open(full, "rb") as f:
            body = f.read()
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype.endswith("javascript"):
            ctype += "; charset=utf-8"
        self._headers(200, ctype, [("Content-Length", str(len(body))), ("Cache-Control", "no-cache")])
        self.end_headers()
        self.wfile.write(body)

    def _stream(self, token, since):
        """Server-Sent Events: push new live events every second while the session is valid."""
        self._headers(200, "text/event-stream", [("Cache-Control", "no-store")])
        self.end_headers()
        last_beat = 0
        try:
            while self.server.sessions.get(token, stage="full"):
                conn = self.server.conn()
                events = stats.live(conn, since)
                conn.close()
                if events:
                    since = events[-1]["id"]
                    self.wfile.write(("event: live\ndata: %s\n\n" % json.dumps(events, default=str)).encode())
                    self.wfile.flush()
                if time.time() - last_beat > 15:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    last_beat = time.time()
                time.sleep(1)
            self.wfile.write(b"event: expired\ndata: {}\n\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    # --- POST --------------------------------------------------------------
    def do_POST(self):
        try:
            raw = self._read_raw()
        except ValueError as e:
            return self._json(413, {"error": str(e)})
        if not self._host_ok():
            return self._json(421, {"error": "bad host"})
        if self.headers.get("Origin") not in self.server.allowed_origins:
            return self._json(403, {"error": "cross-origin request refused"})
        if not (self.headers.get("Content-Type") or "").startswith("application/json"):
            return self._json(415, {"error": "JSON required"})
        try:
            body = self._parse(raw)
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        routes = {
            "/api/auth/google": self._auth_google, "/api/auth/password": self._auth_password,
            "/api/auth/setup": self._auth_setup, "/api/auth/logout": self._auth_logout,
            "/api/auth/change": self._auth_change, "/api/switches": self._switches,
        }
        handler = routes.get(urlparse(self.path).path)
        if not handler:
            return self._json(404, {"error": "not found"})
        try:
            return handler(body)
        except firebase.FirebaseError as e:
            return self._json(502, {"error": "Firebase: %s" % e})

    def _auth_google(self, body):
        id_token = str(body.get("idToken") or "")
        try:
            user = self.server.fb.lookup_user(self.server.cfg, id_token)
        except firebase.FirebaseError:
            self.server.lockout.log("google_rejected", "invalid or expired ID token")
            return self._json(401, {"error": "Google sign-in could not be verified."})
        if user.get("localId") != self.server.cfg["ownerUid"]:
            self.server.lockout.log("owner_mismatch", "uid %s…" % str(user.get("localId"))[:6])
            return self._json(403, {"error": "This Google account is not the TIDOS owner."})
        record = self.server.fb.get_password_doc(self.server.cfg, id_token)
        token = self.server.sessions.create("pending", {
            "id_token": id_token, "email": user.get("email", ""), "has_password": record is not None,
            "record": record})
        self.server.lockout.log("google_ok", "owner verified")
        return self._json(200, {"stage": "password" if record else "setup", **self._lock_info()},
                          [self._set_cookie(PENDING_COOKIE, token, auth.PENDING_TTL)])

    def _finish_login(self, pending_token, pending):
        self.server.sessions.drop(pending_token)
        token = self.server.sessions.create("full", {"id_token": pending["id_token"], "email": pending["email"]})
        return self._json(200, {"stage": "app"}, [self._set_cookie(SESSION_COOKIE, token, auth.SESSION_TTL),
                                                  self._clear_cookie(PENDING_COOKIE)])

    def _auth_password(self, body):
        pending_token = self._cookie(PENDING_COOKIE)
        pending = self.server.sessions.get(pending_token, stage="pending")
        if not pending or not pending["has_password"]:
            return self._json(401, {"error": "Sign in with Google first."})
        if self.server.lockout.locked_until():
            self.server.lockout.log("login_blocked", "attempt during lockout")
            return self._json(423, {"error": "Too many wrong passwords. Locked.", **self._lock_info()})
        if auth.verify_password(str(body.get("password") or ""), pending["record"]):
            self.server.lockout.log("login_ok", pending["email"])
            return self._finish_login(pending_token, pending)
        self.server.lockout.log("login_fail", "wrong control password")
        info = self._lock_info()
        if info["locked_until"]:
            self.server.lockout.log("lockout", "until %s" % info["locked_until"])
        return self._json(401, {"error": "Wrong password.", **info})

    def _auth_setup(self, body):
        pending_token = self._cookie(PENDING_COOKIE)
        pending = self.server.sessions.get(pending_token, stage="pending")
        if not pending or pending["has_password"]:
            return self._json(401, {"error": "Setup is only available before a password exists."})
        password = str(body.get("password") or "")
        problem = auth.password_problem(password)
        if problem:
            return self._json(400, {"error": problem})
        self.server.fb.set_password_doc(self.server.cfg, pending["id_token"], auth.hash_password(password))
        self.server.lockout.log("password_set", "first-time setup")
        self.server.lockout.log("login_ok", pending["email"])
        return self._finish_login(pending_token, pending)

    def _auth_logout(self, body):
        self.server.sessions.drop(self._cookie(SESSION_COOKIE))
        self.server.sessions.drop(self._cookie(PENDING_COOKIE))
        return self._json(200, {"stage": "login"}, [self._clear_cookie(SESSION_COOKIE),
                                                    self._clear_cookie(PENDING_COOKIE)])

    def _auth_change(self, body):
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        record = self.server.fb.get_password_doc(self.server.cfg, session["id_token"])
        if not auth.verify_password(str(body.get("current") or ""), record):
            self.server.lockout.log("password_change_fail", "wrong current password")
            return self._json(401, {"error": "Current password is wrong."})
        new = str(body.get("new") or "")
        problem = auth.password_problem(new)
        if problem:
            return self._json(400, {"error": problem})
        self.server.fb.set_password_doc(self.server.cfg, session["id_token"], auth.hash_password(new))
        self.server.lockout.log("password_changed", session["email"])
        return self._json(200, {"ok": True})

    def _switches(self, body):
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        name = body.get("name")
        if name not in control.SWITCHES:
            return self._json(400, {"error": "unknown switch"})
        control.set_switch(name, bool(body.get("on")))
        self.server.lockout.log("switch", "%s=%s" % (name, "on" if body.get("on") else "off"))
        return self._json(200, {"switches": control.describe()})


def serve(port=8767, open_browser=True, db_path=None):
    server = ControlServer(port=port, db_path=db_path)
    url = "http://localhost:%d/" % server.port
    print("[TIDOSZIT] Control Center running at %s (localhost only). Ctrl+C to stop." % url)
    print("[TIDOSZIT] Log in IN THE BROWSER. Never type your control password in a chat or terminal.")
    if open_browser:
        import webbrowser
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        print("[TIDOSZIT] stopped at %s" % datetime.now(timezone.utc).isoformat(timespec="seconds"))
