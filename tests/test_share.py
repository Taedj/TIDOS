"""Tests for community learning: consent, the anonymous pack, upload, the owner's Community view."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_brain import control, db  # noqa: E402
from tidos_dashboard import community, firebase  # noqa: E402
from tidos_learn import share  # noqa: E402
from tidos_session import brief  # noqa: E402
from test_learn import add_session  # noqa: E402

SECRET_PROJECT = "SECRETPROJ"
CWD = r"D:\work\Dev\SECRETPROJ"
CALLS = [("read", CWD + r"\lib\payments_secret.dart"), ("edit", CWD + r"\lib\payments_secret.dart"),
         ("exec", "flutter test test/payments_secret_test.dart")]


class FakeFb:
    FirebaseError = firebase.FirebaseError

    def __init__(self):
        self.writes = []

    def refresh_id_token(self, cfg, refresh_token):
        return "id-token", "user-123"

    def set_doc(self, cfg, id_token, path, data):
        self.writes.append((path, data))


class ShareTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.env = mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.home,
                                                "TIDOS_CONTROL_FILE": os.path.join(self.tmp.name, "control.json")})
        self.env.start()
        self.conn = db.connect(":memory:")
        add_session(self.conn, "s", CWD, SECRET_PROJECT, "claude-opus-5-5", [
            ("fix the crash in my secret payment flow for client Acme", "success", 1, 0, CALLS, [("flutter test", 1)]),
            ("add the refund screen, my api key is sk-ant-api03-" + "x" * 40, "failure", 0, 1, CALLS,
             [("flutter test test/payments_secret_test.dart", 0)])])

    def tearDown(self):
        self.conn.close()
        self.env.stop()
        self.tmp.cleanup()

    def test_pack_is_whitelist_only(self):
        pack = share.build(self.conn)
        text = json.dumps(pack)
        for private in (SECRET_PROJECT, "Acme", "payment flow", "payments_secret", "sk-ant", "D:\\\\", "work/Dev",
                        "refund screen"):
            self.assertNotIn(private, text, private)
        self.assertEqual(set(pack), {"schema", "tidos_version", "install", "date", "work", "checks", "guide",
                                     "dungeons", "tools", "army"})
        self.assertEqual(pack["checks"][0]["check"], "flutter test")      # tool + subcommand only, no file
        self.assertEqual(sum(w["tasks"] for w in pack["work"]), 2)

    def test_consent_question_until_answered_and_never_blocking(self):
        from tidos_session import cli
        self.assertEqual(share.consent(), "unasked")
        project = os.path.join(self.tmp.name, "proj")
        os.makedirs(project)
        with mock.patch("os.path.expanduser", lambda p: p.replace("~", self.home, 1)):
            text = cli.start("claude-code", "claude-opus-5-5", project)[2]
            self.assertIn("Allow TIDOS to self-learn from your work?", text)
            self.assertIn("consent agree", text)
            share.set_consent("decline")
            text = cli.start("claude-code", "claude-opus-5-5", project)[2]
        self.assertNotIn("Allow TIDOS to self-learn", text)            # asked once: not again after an answer
        self.assertIn("TIDOS LEARN MODE", text)                        # 'Not agree' never blocks TIDOS

    def test_upload_only_with_consent_and_sign_in(self):
        fb = FakeFb()
        ok, detail = share.upload(self.conn, fb=fb, cfg={})
        self.assertFalse(ok)
        self.assertIn("did not agree", detail)
        share.set_consent("agree")
        ok, detail = share.upload(self.conn, fb=fb, cfg={})
        self.assertFalse(ok)
        self.assertIn("sign in", detail)                               # no Google session yet
        os.makedirs(self.home, exist_ok=True)
        with open(os.path.join(self.home, "tidos-session.json"), "w", encoding="utf-8") as f:
            json.dump({"refreshToken": "r"}, f)
        ok, detail = share.upload(self.conn, fb=fb, cfg={})
        self.assertTrue(ok, detail)
        path, data = fb.writes[0]
        self.assertTrue(path.startswith("contributions/user-123/packs/"))
        self.assertEqual(data["schema"], "tidos-pack/1")
        self.assertFalse(share.due())                                  # at most once a day
        share.set_consent("decline")
        self.assertFalse(share.upload(self.conn, fb=fb, cfg={})[0])     # changing your mind stops it at once

    def test_community_counts_each_installation_once(self):
        old = {"schema": "tidos-pack/1", "install": "a", "date": "2026-10-20", "tidos_version": "5.1.0",
               "work": [{"type": "bugfix", "stack": "python", "strong": True, "tasks": 5, "success": 4}],
               "checks": [{"stack": "python", "check": "python -m pytest", "runs": 5, "passed": 4}]}
        new = dict(old, date="2026-10-25", tidos_version="5.2.0",
                   work=[{"type": "bugfix", "stack": "python", "strong": True, "tasks": 8, "success": 6}])
        other = dict(old, install="b", work=[{"type": "bugfix", "stack": "python", "strong": True, "tasks": 2, "success": 2}])
        summary = community.aggregate([old, new, other, {"schema": "evil"}])
        self.assertEqual((summary["contributors"], summary["packs"]), (2, 3))
        self.assertEqual(summary["work"][0]["tasks"], 10)              # 8 (latest of a) + 2 (b), never 5 again
        self.assertEqual(summary["checks"][0]["users"], 2)
        path = community.export(summary, os.path.join(self.tmp.name, "knowledge.json"))
        with open(path, encoding="utf-8") as f:
            exported = json.load(f)
        self.assertEqual(exported["schema"], "tidos-community/1")
        self.assertNotIn('"install"', json.dumps(exported))            # no installation ids leave the developer

    def test_consent_values_are_validated(self):
        with self.assertRaises(ValueError):
            control.set_text("share_learning", "maybe")
        self.assertIn("Not agree", brief.CONSENT_QUESTION)


if __name__ == "__main__":
    unittest.main()
