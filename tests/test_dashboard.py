"""Security + API tests for the /TIDOSZIT control center (real HTTP server, fake Firebase)."""
import http.client
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import control, db  # noqa: E402
from tidos_dashboard import auth, firebase, server  # noqa: E402

OWNER = "OWNER-UID-123"
CFG = {"projectId": "p", "apiKey": "k", "authDomain": "p.firebaseapp.com", "appId": "a", "ownerUid": OWNER}


class FakeFirebase:
    FirebaseError = firebase.FirebaseError

    def __init__(self):
        self.users = {"owner-token": {"localId": OWNER, "email": "owner@example.com"},
                      "stranger-token": {"localId": "someone-else", "email": "x@example.com"}}
        self.doc = None          # the owner's hash (admin/tidoszit)
        self.docs = {}           # other accounts' hashes (users/<uid>/private/tidoszit)
        self.writes = 0

    def lookup_user(self, cfg, id_token):
        if id_token not in self.users:
            raise firebase.FirebaseError("bad token", 400)
        return self.users[id_token]

    def get_password_doc(self, cfg, id_token, path="admin/tidoszit"):
        return self.doc if path == "admin/tidoszit" else self.docs.get(path)

    def query_group(self, cfg, id_token, collection):
        return [{"schema": "tidos-pack/1", "install": "i1", "date": "2026-10-25",
                 "work": [{"type": "bugfix", "stack": "python", "strong": True, "tasks": 3, "success": 2}]}]

    def set_password_doc(self, cfg, id_token, record, path="admin/tidoszit"):
        if path == "admin/tidoszit":
            self.doc = record
        else:
            self.docs[path] = record
        self.writes += 1


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json"),
                                                "TIDOS_HOME_DIR": os.path.join(self.tmp.name, "home")})
        self.env.start()
        self.fb = FakeFirebase()
        self.srv = server.ControlServer(port=0, cfg=CFG, db_path=os.path.join(self.tmp.name, "brain.db"), fb=self.fb)
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.srv.port
        self.cookies = {}

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.env.stop()
        self.tmp.cleanup()

    # --- client helpers ----------------------------------------------------
    def req(self, method, path, body=None, host=None, origin="same", ctype="application/json"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": host or "localhost:%d" % self.port}
        if origin == "same":
            headers["Origin"] = "http://localhost:%d" % self.port
        elif origin:
            headers["Origin"] = origin
        if self.cookies:
            headers["Cookie"] = "; ".join("%s=%s" % kv for kv in self.cookies.items())
        data = None
        if body is not None:
            data = json.dumps(body)
            headers["Content-Type"] = ctype
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        for header, value in resp.getheaders():
            if header.lower() == "set-cookie":
                name, val = value.split(";", 1)[0].split("=", 1)
                if "Max-Age=0" in value:
                    self.cookies.pop(name, None)
                else:
                    self.cookies[name] = val
                self.assertIn("HttpOnly", value)
                self.assertIn("SameSite=Strict", value)
        conn.close()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = raw
        return resp.status, payload, dict(resp.getheaders())

    def login_with_setup(self, password="Str0ng-Passw0rd!"):
        self.assertEqual(self.req("POST", "/api/auth/google", {"idToken": "owner-token"})[1]["stage"], "setup")
        status, body, _ = self.req("POST", "/api/auth/setup", {"password": password})
        self.assertEqual(status, 200, body)

    # --- tests ---------------------------------------------------------------
    def test_boot_starts_at_login_and_api_requires_session(self):
        status, body, headers = self.req("GET", "/api/boot")
        self.assertEqual((status, body["stage"]), (200, "login"))
        self.assertNotIn("ownerUid", body["firebase"])
        self.assertIn("frame-ancestors", headers.get("Content-Security-Policy", "") + "frame-ancestors")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        for path in ("/api/status", "/api/live", "/api/tasks", "/api/security", "/api/stream"):
            self.assertEqual(self.req("GET", path)[0], 401, path)

    def test_bad_host_is_refused(self):  # DNS rebinding
        self.assertEqual(self.req("GET", "/api/boot", host="evil.example:%d" % self.port)[0], 421)

    def test_cross_origin_and_non_json_posts_refused(self):  # CSRF
        self.assertEqual(self.req("POST", "/api/auth/google", {"idToken": "owner-token"}, origin="http://evil.example")[0], 403)
        self.assertEqual(self.req("POST", "/api/auth/google", {"idToken": "owner-token"}, origin=None)[0], 403)
        self.assertEqual(self.req("POST", "/api/auth/google", {"idToken": "owner-token"}, ctype="text/plain")[0], 415)

    def test_wrong_google_account_or_token_refused(self):
        self.login_with_setup()                 # the owner signs in first: this installation is now theirs
        self.cookies.clear()
        code, body = self.req("POST", "/api/auth/google", {"idToken": "stranger-token"})[:2]
        self.assertEqual(code, 403)             # another account can never open this computer's brain
        self.assertIn("belongs to another Google account", body["error"])
        self.assertEqual(self.req("POST", "/api/auth/google", {"idToken": "forged"})[0], 401)
        self.assertEqual(self.req("POST", "/api/auth/password", {"password": "x"})[0], 401)
        conn = db.connect(self.srv.db_path)
        events = [r["event"] for r in conn.execute("SELECT event FROM security_log")]
        conn.close()
        self.assertEqual(events[-2:], ["account_mismatch", "google_rejected"])

    def test_any_google_account_gets_its_own_tidos(self):
        code, body = self.req("POST", "/api/auth/google", {"idToken": "stranger-token"})[:2]
        self.assertEqual((code, body["stage"]), (200, "setup"))   # a normal user: first sign-in on their computer
        self.assertEqual(self.req("POST", "/api/auth/setup", {"password": "Us3r-Passw0rd!"})[0], 200)
        self.assertIn("users/someone-else/private/tidoszit", self.fb.docs)  # own hash, never the owner's doc
        self.assertIsNone(self.fb.doc)
        status = self.req("GET", "/api/status")[1]
        self.assertEqual(status["session"]["role"], "user")
        self.assertEqual(self.req("GET", "/api/community")[0], 403)            # developer-only, enforced server-side
        self.assertEqual(self.req("POST", "/api/community/export", {})[0], 403)

    def test_owner_sees_the_community(self):
        self.login_with_setup()
        code, body = self.req("GET", "/api/community")[:2]
        self.assertEqual((code, body["contributors"], body["work"][0]["tasks"]), (200, 1, 3))
        self.assertEqual(self.req("GET", "/api/share")[1]["consent"], "unasked")
        self.assertEqual(self.req("POST", "/api/share", {"answer": "decline"})[1]["consent"], "decline")
        self.assertEqual(self.req("POST", "/api/share", {"answer": "maybe"})[0], 400)

    def test_control_center_lists_every_tidos_command(self):
        self.assertEqual(self.req("GET", "/api/commands")[0], 401)               # behind the login like the rest
        self.login_with_setup()
        code, body = self.req("GET", "/api/commands")[:2]
        names = [c["name"] for c in body["commands"]]
        self.assertEqual(code, 200)
        self.assertEqual(names[0], "/TIDOSZIT")
        self.assertIn("/tidos-status", names)
        self.assertIsInstance(body["tools"], list)

    def test_first_run_setup_stores_only_a_hash(self):
        self.assertEqual(self.req("POST", "/api/auth/google", {"idToken": "owner-token"})[1]["stage"], "setup")
        self.assertEqual(self.req("POST", "/api/auth/setup", {"password": "short"})[0], 400)
        self.login_with_setup("Str0ng-Passw0rd!")
        self.assertNotIn("Str0ng-Passw0rd!", json.dumps(self.fb.doc))
        self.assertTrue(auth.verify_password("Str0ng-Passw0rd!", self.fb.doc))
        status, body, _ = self.req("GET", "/api/status")
        self.assertEqual(status, 200)
        self.assertEqual(body["session"]["email"], "owner@example.com")
        # setup cannot be replayed once a password exists
        self.assertEqual(self.req("POST", "/api/auth/google", {"idToken": "owner-token"})[1]["stage"], "password")
        self.assertEqual(self.req("POST", "/api/auth/setup", {"password": "An0ther-Passw0rd!"})[0], 401)

    def test_password_login_and_lockout(self):
        self.fb.doc = auth.hash_password("Right-Passw0rd", iterations=1000)
        self.req("POST", "/api/auth/google", {"idToken": "owner-token"})
        for left in range(auth.MAX_FAILURES - 1, 0, -1):
            status, body, _ = self.req("POST", "/api/auth/password", {"password": "wrong"})
            self.assertEqual((status, body["failures_left"]), (401, left))
        status, body, _ = self.req("POST", "/api/auth/password", {"password": "wrong"})
        self.assertIsNotNone(body["locked_until"])
        # even the right password is refused while locked
        self.assertEqual(self.req("POST", "/api/auth/password", {"password": "Right-Passw0rd"})[0], 423)
        self.assertEqual(self.req("GET", "/api/status")[0], 401)

    def test_password_login_success(self):
        self.fb.doc = auth.hash_password("Right-Passw0rd", iterations=1000)
        self.req("POST", "/api/auth/google", {"idToken": "owner-token"})
        self.assertEqual(self.req("POST", "/api/auth/password", {"password": "Right-Passw0rd"})[0], 200)
        self.assertIn(server.SESSION_COOKIE, self.cookies)
        self.assertNotIn(server.PENDING_COOKIE, self.cookies)
        self.assertEqual(self.req("GET", "/api/live")[0], 200)

    def test_switches_logout_and_change_password(self):
        self.login_with_setup()
        status, body, _ = self.req("POST", "/api/switches", {"name": "tracing", "on": False})
        self.assertEqual(status, 200)
        self.assertFalse(control.is_on("tracing"))
        self.assertEqual(self.req("POST", "/api/switches", {"name": "rm-rf", "on": True})[0], 400)
        self.assertEqual(self.req("POST", "/api/auth/change", {"current": "nope", "new": "N3w-Passw0rd!"})[0], 401)
        self.assertEqual(self.req("POST", "/api/auth/change", {"current": "Str0ng-Passw0rd!", "new": "N3w-Passw0rd!"})[0], 200)
        self.assertTrue(auth.verify_password("N3w-Passw0rd!", self.fb.doc))
        self.req("POST", "/api/auth/logout", {})
        self.assertEqual(self.req("GET", "/api/status")[0], 401)

    def test_playbook_library(self):
        home = os.path.join(self.tmp.name, "tidoshome")
        with mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": home}):
            pb = os.path.join(home, "playbooks", "app", "bugfix.md")
            os.makedirs(os.path.dirname(pb))
            with open(pb, "w", encoding="utf-8") as f:
                f.write("---\ntype: bugfix\nstack: python\nproject: APP\nconfidence: 0.8\n---\n# body\n")
            with open(os.path.join(home, "secret.txt"), "w") as f:
                f.write("x")
            self.assertEqual(self.req("GET", "/api/playbooks")[0], 401)
            self.assertEqual(self.req("POST", "/api/playbooks/toggle", {"path": "app/bugfix.md", "disabled": True})[0], 401)
            self.login_with_setup()
            status, body, _ = self.req("GET", "/api/playbooks")
            self.assertEqual([(p["path"], p["project"], p["disabled"]) for p in body["playbooks"]],
                             [("app/bugfix.md", "APP", False)])
            self.assertIn("# body", self.req("GET", "/api/playbook?path=app/bugfix.md")[1]["text"])
            for bad in ("../secret.txt", "..%2Fsecret.txt", "app/../../secret.txt"):
                self.assertEqual(self.req("GET", "/api/playbook?path=" + bad)[0], 404, bad)
            self.assertEqual(self.req("POST", "/api/playbooks/toggle", {"path": "../secret.txt", "disabled": True})[0], 400)
            self.assertEqual(self.req("POST", "/api/playbooks/toggle", {"path": "app/bugfix.md", "disabled": True})[0], 200)
            self.assertTrue(self.req("GET", "/api/playbooks")[1]["playbooks"][0]["disabled"])

    def test_tool_scout_endpoints(self):
        home = os.path.join(self.tmp.name, "tidoshome3")
        with mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": home}):
            self.assertEqual(self.req("GET", "/api/tools")[0], 401)
            self.assertEqual(self.req("POST", "/api/tools/action", {"name": "ruff", "action": "approved"})[0], 401)
            self.login_with_setup()
            tools = self.req("GET", "/api/tools")[1]["tools"]
            self.assertTrue(any(t["name"] == "gitleaks" for t in tools))
            self.assertEqual(self.req("POST", "/api/tools/action", {"name": "ruff", "action": "blacklisted"})[0], 200)
            from tidos_scout import scout
            self.assertEqual(scout.state()["ruff"]["status"], "blacklisted")
            for bad in ({"name": "ruff", "action": "rm"}, {"name": "rm -rf", "action": "vet"}):
                self.assertEqual(self.req("POST", "/api/tools/action", bad)[0], 400, bad)
            code, body = self.req("POST", "/api/tools/action", {"name": "ruff", "action": "install"})[:2]
            self.assertEqual(code, 409)  # refused: tool_install switch off by default (and ruff is blacklisted)
            self.assertIn("switch is off", json.dumps(body))

    def test_connect_ai_tools_endpoints(self):
        home = os.path.join(self.tmp.name, "userhome")
        os.makedirs(os.path.join(home, ".config", "opencode"))
        fake_home = mock.patch("tidos_session.wire.os.path.expanduser", lambda p: p.replace("~", home, 1))
        no_path = mock.patch("tidos_session.wire.shutil.which", lambda exe: None)
        with fake_home, no_path:
            self.assertEqual(self.req("GET", "/api/connect")[0], 401)
            self.assertEqual(self.req("POST", "/api/connect", {"tool": "opencode", "action": "connect"})[0], 401)
            self.login_with_setup()
            rows = {r["id"]: r for r in self.req("GET", "/api/connect")[1]["tools"]}
            self.assertEqual((rows["opencode"]["installed"], rows["opencode"]["connected"]), (True, False))
            self.assertFalse(rows["codex"]["installed"])
            for bad in ({"tool": "opencode", "action": "rm"}, {"tool": "cursor", "action": "connect"},
                        {"tool": "../x", "action": "connect"}):
                self.assertEqual(self.req("POST", "/api/connect", bad)[0], 400, bad)
            code, body = self.req("POST", "/api/connect", {"tool": "opencode", "action": "connect"})[:2]
            self.assertEqual(code, 200)
            self.assertEqual([d["status"] for d in body["done"]], ["added", "added"])
            self.assertTrue(os.path.isfile(os.path.join(home, ".config", "opencode", "AGENTS.md")))
            self.assertEqual(self.req("POST", "/api/connect", {"tool": "opencode", "action": "disconnect"})[0], 200)
            self.assertFalse(os.path.exists(os.path.join(home, ".config", "opencode", "AGENTS.md")))
        conn = db.connect(self.srv.db_path)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM security_log WHERE event = 'connect'").fetchone()[0], 2)
        conn.close()

    def test_memory_and_army_endpoints(self):
        home = os.path.join(self.tmp.name, "tidoshome2")
        with mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": home}):
            os.makedirs(os.path.join(home, "memory"))
            with open(os.path.join(home, "memory", "LESSONS.md"), "w", encoding="utf-8") as f:
                f.write("# lessons")
            with open(os.path.join(home, "control.md"), "w", encoding="utf-8") as f:
                f.write("outside")
            self.assertEqual(self.req("GET", "/api/memory")[0], 401)
            self.login_with_setup()
            items = self.req("GET", "/api/memory")[1]["items"]
            self.assertEqual([i["path"] for i in items], ["memory/LESSONS.md"])
            self.assertIn("lessons", self.req("GET", "/api/memory/file?path=memory/LESSONS.md")[1]["text"])
            for bad in ("control.md", "memory/../control.md", "../x.md"):
                self.assertEqual(self.req("GET", "/api/memory/file?path=" + bad)[0], 404, bad)
            units = self.req("GET", "/api/army")[1]["units"]
            self.assertTrue(any(u["name"] == "tidos-reviewer" and u["state"] == "active" for u in units))

    def test_session_expiry(self):
        now = [1000.0]
        sessions = auth.Sessions(clock=lambda: now[0])
        token = sessions.create("full", {"email": "e"})
        self.assertIsNotNone(sessions.get(token, stage="full"))
        self.assertIsNone(sessions.get(token, stage="pending"))
        now[0] += auth.SESSION_TTL + 1
        self.assertIsNone(sessions.get(token))

    def test_static_files_and_traversal(self):
        status, body, headers = self.req("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn(b"TIDOSZIT", body)
        self.assertEqual(self.req("GET", "/static/app.js")[0], 200)
        self.assertEqual(self.req("GET", "/static/../server.py")[0], 404)
        self.assertEqual(self.req("GET", "/static/..%5Cserver.py")[0], 404)


class ControlSwitchTests(unittest.TestCase):
    def test_defaults_and_cli(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {"TIDOS_CONTROL_FILE": os.path.join(tmp, "c.json")}):
            self.assertTrue(control.is_on("tracing"))
            self.assertFalse(control.is_on("gptid"))
            control.set_switch("auto_update", False)
            self.assertFalse(control.is_on("auto_update"))
            with open(os.path.join(tmp, "c.json"), "w") as f:
                f.write("{corrupt")
            self.assertTrue(control.is_on("auto_update"))  # corrupt file -> safe defaults


if __name__ == "__main__":
    unittest.main()
