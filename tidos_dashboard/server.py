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

from . import accounts, auth, config, explore, firebase, stats

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
                data["session"] = {"email": session["email"], "expires_in": self.server.sessions.remaining(token),
                                   "role": session.get("role", "owner")}
                return self._json(200, data)
            if path == "/api/live":
                since = int((query.get("since") or ["0"])[0])
                return self._json(200, {"events": stats.live(conn, since), "active": stats.active_sessions(conn)})
            if path == "/api/tasks":
                return self._json(200, {"tasks": stats.recent_tasks(conn)})
            if path == "/api/dungeons":
                return self._json(200, stats.dungeons(conn))
            if path == "/api/search":
                return self._json(200, explore.search(conn, (query.get("q") or [""])[0][:200]))
            if path == "/api/settings":
                return self._json(200, {"settings": explore.settings()})
            if path == "/api/backups":
                return self._json(200, {"backups": explore.list_backups()})
            if path == "/api/tools":
                from tidos_scout import scout
                return self._json(200, {"tools": scout.overview(conn)})
            if path == "/api/update":
                from tidos_session import updater
                return self._json(200, {"update": updater.status()})
            if path == "/api/actions":
                from tidos_brain import trust
                return self._json(200, {"actions": list(reversed(trust.journal(50))), "levels": trust.levels()})
            if path == "/api/connect":
                from tidos_session import wire
                return self._json(200, {"tools": wire.tools(), "snippet": wire.manual_snippet()})
            if path == "/api/evolution":
                return self._json(200, stats.evolution())
            if path == "/api/notifications":
                return self._json(200, {"notifications": stats.notifications(conn)})
            if path == "/api/army":
                return self._json(200, stats.army(conn))
            if path == "/api/commands":
                from tidos_session import commands
                return self._json(200, {"commands": commands.listing(), "tools": commands.installed_tools()})
            if path == "/api/center":
                from tidos_brain import center
                t = center.overview(self.server.db_path)
                try:
                    t["health"] = center.health(db_path=self.server.db_path)  # signature-cached scan on change
                except Exception as e:  # noqa: BLE001 - the tab must survive a broken diagnostics pass
                    t["health"] = {"error": "diagnostics unavailable: %s" % str(e)[:120], "issues": []}
                return self._json(200, t)
            if path == "/api/share":
                from tidos_learn import share
                return self._json(200, {"consent": share.consent(), "last": share.last_upload(),
                                        "signed_in": bool(share._google_session())})
            if path == "/api/share/preview":
                from tidos_learn import share
                return self._json(200, {"pack": share.build(conn)})
            if path == "/api/community":
                if session.get("role", "owner") != "owner":
                    return self._json(403, {"error": "the Community tab is for the TIDOS developer"})
                from tidos_dashboard import community
                packs = self.server.fb.query_group(self.server.cfg, session["id_token"], "packs")
                return self._json(200, community.aggregate(packs))
            if path == "/api/jobs":
                from tidos_dashboard import autopilot, jobs
                from tidos_session import helper
                return self._json(200, {
                    "jobs": [{k: v for k, v in j.items() if k != "log"} for j in reversed(jobs.history()[-30:])],
                    "running": (jobs.running() or {}).get("id"), "options": jobs.options(conn),
                    "recommendations": autopilot.decide(conn),
                    "autopilot": {"on": control.is_on("autopilot")},
                    "helper": helper.describe(conn)})
            if path == "/api/jobs/log":
                from tidos_dashboard import jobs
                data = jobs.log_text((query.get("id") or [""])[0], (query.get("offset") or ["0"])[0])
                return self._json(200, data) if data is not None else self._json(404, {"error": "not found"})
            if path == "/api/army/lessons":
                from tidos_learn import army
                text = army.lessons((query.get("name") or [""])[0])
                return self._json(200, {"text": text}) if text is not None else self._json(404, {"error": "not found"})
            if path == "/api/memory":
                return self._json(200, stats.memory_index())
            if path == "/api/memory/file":
                text = stats.memory_text((query.get("path") or [""])[0])
                return self._json(200, {"text": text}) if text is not None else self._json(404, {"error": "not found"})
            if path == "/api/session":
                return self._json(200, stats.session_info(conn))
            if path == "/api/playbooks":
                return self._json(200, stats.playbooks(conn))
            if path == "/api/playbook":
                text = stats.playbook_text((query.get("path") or [""])[0])
                return self._json(200, {"text": text}) if text is not None else self._json(404, {"error": "not found"})
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
            "/api/playbooks/toggle": self._playbook_toggle,
            "/api/evolution/status": self._evolution_status,
            "/api/center/diag": self._diag_status,
            "/api/army/action": self._army_action,
            "/api/share": self._share,
            "/api/community/export": self._community_export,
            "/api/jobs/run": self._job_run,
            "/api/jobs/cancel": self._job_cancel,
            "/api/tools/action": self._tool_action,
            "/api/connect": self._connect,
            "/api/actions/undo": self._action_undo,
            "/api/trust": self._trust_level,
            "/api/update": self._update,
            "/api/ask": self._ask,
            "/api/settings": self._setting,
            "/api/backups": self._backup,
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
        uid = user.get("localId")
        refused = accounts.check(uid)  # the first account to sign in on a computer owns that installation
        if refused:
            self.server.lockout.log("account_mismatch", "uid %s…" % str(uid)[:6])
            return self._json(403, {"error": refused})
        doc = accounts.password_doc(self.server.cfg, uid)
        record = self.server.fb.get_password_doc(self.server.cfg, id_token, path=doc)
        token = self.server.sessions.create("pending", {
            "id_token": id_token, "email": user.get("email", ""), "has_password": record is not None,
            "record": record, "uid": uid, "doc": doc})
        self.server.lockout.log("google_ok", "%s verified" % accounts.role(self.server.cfg, uid))
        return self._json(200, {"stage": "password" if record else "setup", **self._lock_info()},
                          [self._set_cookie(PENDING_COOKIE, token, auth.PENDING_TTL)])

    def _finish_login(self, pending_token, pending):
        self.server.sessions.drop(pending_token)
        accounts.claim(pending["uid"], pending["email"])
        token = self.server.sessions.create("full", {"id_token": pending["id_token"], "email": pending["email"],
                                                     "uid": pending["uid"], "doc": pending["doc"],
                                                     "role": accounts.role(self.server.cfg, pending["uid"])})
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
        self.server.fb.set_password_doc(self.server.cfg, pending["id_token"], auth.hash_password(password),
                                        path=pending["doc"])
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
        record = self.server.fb.get_password_doc(self.server.cfg, session["id_token"], path=session["doc"])
        if not auth.verify_password(str(body.get("current") or ""), record):
            self.server.lockout.log("password_change_fail", "wrong current password")
            return self._json(401, {"error": "Current password is wrong."})
        new = str(body.get("new") or "")
        problem = auth.password_problem(new)
        if problem:
            return self._json(400, {"error": problem})
        self.server.fb.set_password_doc(self.server.cfg, session["id_token"], auth.hash_password(new),
                                        path=session["doc"])
        self.server.lockout.log("password_changed", session["email"])
        return self._json(200, {"ok": True})

    def _evolution_status(self, body):
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        from tidos_learn import evolve
        status = body.get("status")
        if status not in ("accepted", "rejected", "new"):
            return self._json(400, {"error": "status must be accepted, rejected or new"})
        try:
            evolve.set_status(int(body.get("id")), status)
        except (KeyError, ValueError, TypeError):
            return self._json(400, {"error": "unknown proposal"})
        self.server.lockout.log("proposal", "#%s %s" % (body.get("id"), status))
        return self._json(200, {"ok": True})

    def _diag_status(self, body):
        """Owner action from the Agent Review tab: move one diagnostic report's status. Evidence is shown,
        never edited; this touches only ~/.tidos/diagnostics.json - no production state."""
        if not self._session():
            return self._json(401, {"error": "login required"})
        from tidos_brain import center
        try:
            item = center.health_set(str(body.get("id") or ""), str(body.get("status") or ""))
        except KeyError:
            return self._json(404, {"error": "unknown issue"})
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        self.server.lockout.log("diagnostics", "%s -> %s" % (item["id"], item["status"]))
        return self._json(200, {"ok": True, "issue": {k: v for k, v in item.items() if isinstance(v, (str, int, float, type(None)))}})

    def _job_run(self, body):
        """Run a TIDOS job from a button (only jobs in tidos_dashboard.jobs.JOBS, parameters checked)."""
        if not self._session():
            return self._json(401, {"error": "login required"})
        from tidos_dashboard import jobs
        conn = db.connect(self.server.db_path)
        try:
            params = body.get("params") if isinstance(body.get("params"), dict) else {}
            if body.get("dry"):  # what it would run, for the confirmation
                argv, _, title, model = jobs.build(conn, str(body.get("job") or ""), params)
                return self._json(200, {"title": title, "model": model, "busy": bool(jobs.running())})
            record = jobs.start(conn, str(body.get("job") or ""), params, by="owner", db_path=self.server.db_path)
        except (jobs.JobError, TypeError) as e:
            return self._json(400, {"error": str(e)})
        except RuntimeError as e:
            return self._json(409, {"error": str(e)})
        finally:
            conn.close()
        self.server.lockout.log("job", record["title"])
        return self._json(200, {k: v for k, v in record.items() if k != "log"})

    def _job_cancel(self, body):
        if not self._session():
            return self._json(401, {"error": "login required"})
        from tidos_dashboard import jobs
        try:
            jobs.cancel(str(body.get("id") or ""))
        except jobs.JobError as e:
            return self._json(409, {"error": str(e)})
        self.server.lockout.log("job", "cancelled %s" % body.get("id"))
        return self._json(200, {"ok": True})

    def _share(self, body):
        """Community learning answer from the Security tab (agree / decline). Never blocks TIDOS."""
        if not self._session():
            return self._json(401, {"error": "login required"})
        from tidos_learn import share
        answer = body.get("answer")
        if answer not in ("agree", "decline"):
            return self._json(400, {"error": "answer must be agree or decline"})
        share.set_consent(answer)
        self.server.lockout.log("share", answer)
        note = None
        if answer == "agree" and not share._google_session():
            note = "To start sharing, sign in once from START TIDOS or run: tidos_session consent agree"
        return self._json(200, {"consent": share.consent(), "note": note})

    def _community_export(self, body):
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        if session.get("role", "owner") != "owner":
            return self._json(403, {"error": "the Community tab is for the TIDOS developer"})
        from tidos_dashboard import community
        packs = self.server.fb.query_group(self.server.cfg, session["id_token"], "packs")
        path = community.export(community.aggregate(packs))
        self.server.lockout.log("community", "exported %s" % os.path.basename(path))
        return self._json(200, {"path": os.path.relpath(path, community.REPO_ROOT).replace("\\", "/")})

    def _army_action(self, body):
        """ARISE: activate a draft unit (-> ~/.claude/agents, personal) or undo it. Owner only, logged."""
        if not self._session():
            return self._json(401, {"error": "login required"})
        from tidos_learn import army
        name, action = str(body.get("name") or ""), body.get("action")
        if action not in ("activate", "deactivate"):
            return self._json(400, {"error": "unknown action"})
        try:
            path = army.activate(name) if action == "activate" else army.deactivate(name)
        except (ValueError, KeyError) as e:
            return self._json(409, {"error": str(e).strip("'")})
        self.server.lockout.log("army", "%s %s" % (name, action))
        from tidos_brain import trust
        if action == "activate":  # your activations teach TIDOS when it may activate by itself
            trust.record("activate_unit", "Activate %s" % name, by="owner", target=name)
        else:
            trust.reversed_by_you("activate_unit", name)
        return self._json(200, {"ok": True, "path": path})

    def _action_undo(self, body):
        """Undo one journaled action (activation, self-improve branch). Owner only, logged; lowers that kind's trust."""
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        if session.get("role", "owner") != "owner":
            return self._json(403, {"error": "only the owner can undo TIDOS actions"})
        from tidos_brain import trust
        try:
            item = trust.undo(int(body.get("id", -1)))
        except KeyError:
            return self._json(404, {"error": "no such action"})
        except ValueError as e:
            return self._json(409, {"error": str(e)})
        self.server.lockout.log("action_undo", "#%d %s: %s" % (item["id"], item["kind"], item.get("undo_detail")))
        return self._json(200, {"action": item, "level": trust.level(item["kind"])})

    def _update(self, body):
        """Apply the release that passed staging (you approve a minor/major one) or roll back. Owner only, logged."""
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        if session.get("role", "owner") != "owner":
            return self._json(403, {"error": "only the owner can update TIDOS"})
        from tidos_brain import trust
        from tidos_session import updater
        action = body.get("action")
        if action not in ("apply", "rollback"):
            return self._json(400, {"error": "unknown action"})
        try:
            done = updater.apply() if action == "apply" else updater.rollback()
        except updater.Refused as e:
            return self._json(409, {"error": str(e)})
        self.server.lockout.log("update", "%s: %s -> %s" % (action, done["from"], done["to"]))
        if action == "apply":
            trust.record("self_update", "Update to %s" % done["to"], by="owner")
        else:
            trust.reversed_by_you("self_update", None)
        return self._json(200, {"done": done, "update": updater.status()})

    def _trust_level(self, body):
        """Set the trust level of one kind of action (pinned), or clear it back to earned trust. Owner only."""
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        if session.get("role", "owner") != "owner":
            return self._json(403, {"error": "only the owner can change TIDOS's trust"})
        from tidos_brain import trust
        try:
            level = trust.set_level(str(body.get("kind")), body.get("level") or None)
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        self.server.lockout.log("trust", "%s -> %s" % (body.get("kind"), level))
        return self._json(200, {"levels": trust.levels()})

    def _ask(self, body):
        if not self._session():
            return self._json(401, {"error": "login required"})
        question = str(body.get("question") or "").strip()[:500]
        if not question:
            return self._json(400, {"error": "empty question"})
        conn = db.connect(self.server.db_path)
        try:
            result = explore.ask(conn, question, lang=str(body.get("lang") or ""))
        finally:
            conn.close()
        self.server.lockout.log("ask", result["source"])  # never the question itself
        return self._json(200, result)

    def _setting(self, body):
        if not self._session():
            return self._json(401, {"error": "login required"})
        try:
            value = explore.set_setting(str(body.get("key")), body.get("value"))
        except (KeyError, ValueError) as e:
            return self._json(400, {"error": str(e).strip("'")})
        self.server.lockout.log("setting", "%s=%s" % (body.get("key"), value))
        return self._json(200, {"settings": explore.settings()})

    def _backup(self, body):
        if not self._session():
            return self._json(401, {"error": "login required"})
        conn = db.connect(self.server.db_path)
        try:
            path = explore.backup(conn)
        finally:
            conn.close()
        self.server.lockout.log("backup", os.path.basename(path))
        return self._json(200, {"backups": explore.list_backups()})

    def _connect(self, body):
        """Connect / disconnect TIDOS to one AI tool (its MCP settings + global instructions). Owner only, logged."""
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        if session.get("role", "owner") != "owner":
            return self._json(403, {"error": "only the owner of this computer can change its AI tools"})
        from tidos_session import wire
        action = body.get("action")
        if action not in ("connect", "disconnect"):
            return self._json(400, {"error": "unknown action"})
        try:
            done = wire.connect(str(body.get("tool"))) if action == "connect" else wire.disconnect(str(body.get("tool")))
        except ValueError as e:
            return self._json(400, {"error": str(e)})
        except OSError as e:
            return self._json(500, {"error": "could not write the file: %s" % e})
        self.server.lockout.log("connect", "%s %s: %s" % (action, body.get("tool"), "; ".join(s for _, s in done)))
        return self._json(200, {"done": [{"file": f, "status": s} for f, s in done]})

    def _tool_action(self, body):
        """Tool scout: approve/propose/blacklist/reset, trust, vet, and install/uninstall (approved tools only,
        switch tool_install, pinned versions / verified downloads: see tidos_scout.scout.install)."""
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        from tidos_scout import scout
        tool = next((t for t in scout.catalog() if t["name"] == body.get("name")), None)
        action = body.get("action")
        if not tool or action not in ("proposed", "approved", "blacklisted", "none", "trust", "vet", "install",
                                      "uninstall"):
            return self._json(400, {"error": "unknown tool or action"})
        if action == "trust":
            result = scout.trust(tool, refresh=True)
        elif action == "vet":
            result = scout.vet(tool)
        elif action in ("install", "uninstall"):
            try:
                result = scout.install(tool["name"]) if action == "install" else scout.uninstall(tool["name"])
            except scout.InstallRefused as e:
                self.server.lockout.log("tool", "%s %s refused: %s" % (tool["name"], action, e))
                return self._json(409, {"error": str(e)})
            self.server.lockout.log("tool", "%s %s: %s" % (tool["name"], action, result["detail"]))
            return self._json(200, result)
        else:
            scout.set_status(tool["name"], action)
            result = {"ok": True}
        self.server.lockout.log("tool", "%s %s" % (tool["name"], action))
        return self._json(200, result)

    def _playbook_toggle(self, body):
        session = self._session()
        if not session:
            return self._json(401, {"error": "login required"})
        from tidos_session import pbstate
        relpath = str(body.get("path") or "")
        if stats.playbook_text(relpath) is None:
            return self._json(400, {"error": "unknown playbook"})
        pbstate.set_disabled(relpath, bool(body.get("disabled")))
        self.server.lockout.log("playbook", "%s %s" % ("disabled" if body.get("disabled") else "enabled", relpath))
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
    from tidos_dashboard import autopilot
    autopilot.loop(db_path, log=server.lockout.log)  # does nothing while the autopilot switch is off
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
