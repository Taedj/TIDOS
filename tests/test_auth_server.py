"""Security tests for scripts/google_auth_server.py (Google verification mocked)."""
import http.client
import json
import os
import socketserver
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import google_auth_server as g  # noqa: E402


def fake_verify(token):
    if token != "good-token":
        raise ValueError("rejected")
    return {"localId": "uid-1", "email": "owner@example.com", "emailVerified": True}


class AuthServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.session = os.path.join(self.tmp.name, "tidos-session.json")
        self.patches = [mock.patch.object(g, "SESSION_FILE", self.session),
                        mock.patch.object(g, "verify_id_token", side_effect=fake_verify)]
        for p in self.patches:
            p.start()
        g.AuthServerHandler.session_result = None
        self.server = socketserver.TCPServer(("127.0.0.1", 0), g.AuthServerHandler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def post(self, payload, origin="same"):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Host": "localhost:%d" % self.port, "Content-Type": "application/json"}
        if origin == "same":
            headers["Origin"] = "http://localhost:%d" % self.port
        elif origin:
            headers["Origin"] = origin
        conn.request("POST", "/callback", json.dumps(payload), headers)
        resp = conn.getresponse()
        resp.read()
        conn.close()
        return resp.status

    def good(self, **over):
        return dict({"idToken": "good-token", "refreshToken": "r-1", "email": "spoofed@evil.example",
                     "state": g.STATE}, **over)

    def test_page_embeds_the_nonce(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", "/", headers={"Host": "localhost:%d" % self.port})
        page = conn.getresponse().read().decode("utf-8")
        self.assertIn(g.STATE, page)
        self.assertNotIn("__STATE__", page)

    def test_rejections(self):
        self.assertEqual(self.post(self.good(state="")), 403)
        self.assertEqual(self.post(self.good(state="guess")), 403)
        self.assertEqual(self.post(self.good(), origin="http://evil.example"), 403)
        self.assertEqual(self.post(self.good(), origin=None), 403)
        self.assertEqual(self.post(self.good(idToken="forged")), 401)
        self.assertFalse(os.path.exists(self.session))

    def test_success_uses_googles_identity_not_the_page(self):
        self.assertEqual(self.post(self.good()), 200)
        with open(self.session, encoding="utf-8") as f:
            saved = json.load(f)
        self.assertEqual(saved["email"], "owner@example.com")    # not the spoofed one from the page
        self.assertNotIn("idToken", saved)                        # short-lived token is not stored
        self.assertEqual(saved["refreshToken"], "r-1")


if __name__ == "__main__":
    unittest.main()
