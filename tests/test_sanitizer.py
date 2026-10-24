"""Tests for the TIDOS Privacy & Sanitization Firewall (scripts/sanitizer.py)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import sanitizer  # noqa: E402

SECRETS = {
    "anthropic": "key = sk-ant-api03-AbCdEfGhIjKlMnOpQrStUvWx0123",
    "openai": "sk-proj-AbCdEfGhIjKlMnOpQrStUvWx",
    "aws": "AKIAIOSFODNN7EXAMPLE",
    "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.dBjftJeZ4CVPmB92K27uhbUJU1p1r_wW1gFWFOEjXk",
    "slack": "xoxb-1234567890-abcdefghij",
    "github": "ghp_" + "a1B2" * 9,
    "google": "AIzaSyDzbyda_7ygLaWtqjLZtiHrqSd0b_CYBQk",
    "private-key": "-----BEGIN RSA PRIVATE KEY-----",
    "db-url": "postgres://admin:S3cr3t!@db.internal:5432/app",
    "assigned-password": 'password = "Tr0ub4dor&3"',
    "bearer": "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345",
}

PROSE = [
    "Use Bearer tokens in headers",
    "password: never hardcode",
    "api_key: <YOUR_API_KEY>",
    "token = ${GITHUB_TOKEN}",
    "Flutter 3.24.1 and Gradle 8.5 are required",
    "Bind to 127.0.0.1 only",
    "Docs IP 192.0.2.10 is reserved for examples",
    "Contact noreply@anthropic.com",
]


class SanitizeTextTests(unittest.TestCase):
    def test_does_not_crash_on_plain_text(self):
        # Regression: v4.0 crashed with re.PatternError ("bad escape \\U") on ANY input
        self.assertEqual(sanitizer.sanitize_text("hello world"), "hello world")

    def test_redacts_windows_user_path(self):
        out = sanitizer.sanitize_text(r"see C:\Users\Dr Jane Doe\project")
        self.assertEqual(out, r"see C:\Users\<USER>\project")

    def test_redacts_unix_home_path(self):
        self.assertIn("/home/<USER>", sanitizer.sanitize_text("/home/alice/code"))

    def test_redacts_git_bash_path_with_spaces(self):
        self.assertEqual(sanitizer.sanitize_text('cd "/c/Users/Dr Jane Doe/AppData"'), 'cd "/c/Users/<USER>/AppData"')

    def test_local_user_name_in_every_spelling(self):
        home = os.path.join("C:" + os.sep, "Users", "Dr Jane Doe")
        with mock.patch.dict(os.environ, {"USERNAME": "Dr Jane Doe", "USER": ""}), \
                mock.patch("os.path.expanduser", return_value=home):
            pat = sanitizer._local_user_names()
        for text in ("C--Users-Dr-Jane-Doe-Desktop-SYLLAB", "dr_jane_doe", "DrJaneDoe", "by Dr Jane Doe"):
            with self.subTest(text=text):
                self.assertTrue(pat.search(text), text)
        self.assertIsNone(pat.search("Dr Janet"))

    def test_redacts_secrets_and_email_and_ip(self):
        out = sanitizer.sanitize_text("k=" + SECRETS["anthropic"] + " mail bob@corp.io host 10.1.2.3")
        self.assertNotIn("sk-ant-", out)
        self.assertIn("<EMAIL_REDACTED>", out)
        self.assertIn("<IP_REDACTED>", out)

    def test_keeps_loopback_and_versions(self):
        text = "127.0.0.1 and version 3.24.1"
        self.assertEqual(sanitizer.sanitize_text(text), text)


class DetectionTests(unittest.TestCase):
    def test_true_positives(self):
        for name, text in SECRETS.items():
            with self.subTest(secret=name):
                self.assertTrue(sanitizer.find_secrets(text), "missed %s" % name)

    def test_no_false_positives_on_prose(self):
        for text in PROSE:
            with self.subTest(text=text):
                self.assertEqual(sanitizer.find_secrets(text), [])
                self.assertEqual(sanitizer.find_pii(text), [])

    def test_pii_detection(self):
        self.assertTrue(sanitizer.find_pii(r"C:\Users\someone\x"))
        self.assertTrue(sanitizer.find_pii("mail me: someone@gmail.com"))
        self.assertTrue(sanitizer.find_pii("server 10.0.0.12"))


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.root, "personas"))
        os.makedirs(os.path.join(self.root, "src"))

    def _write(self, rel, content):
        path = os.path.join(self.root, rel)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def test_clean_persona_passes(self):
        p = self._write("personas/tidosx.md", "# Persona\nNEVER hardcode a password.\n")
        ok, viols = sanitizer.audit_file(p, enforce_dirs=True, root=self.root)
        self.assertTrue(ok, viols)

    def test_directory_whitelist_enforced(self):
        p = self._write("src/notes.md", "# notes\n")
        ok, viols = sanitizer.audit_file(p, enforce_dirs=True, root=self.root)
        self.assertFalse(ok)
        self.assertIn("contribution whitelist", viols[0])

    def test_extension_and_secret_rejected(self):
        p = self._write("personas/leak.py", "KEY = 'AKIAIOSFODNN7EXAMPLE'\n")
        ok, viols = sanitizer.audit_file(p, enforce_dirs=True, root=self.root)
        self.assertFalse(ok)
        self.assertTrue(any(".md only" in v for v in viols))
        self.assertTrue(any("aws-access-key" in v for v in viols))

    def test_bundle_report(self):
        good = self._write("personas/a.md", "fine\n")
        bad = self._write("personas/b.md", "mail someone@gmail.com\n")
        ok, report = sanitizer.audit_bundle([good, bad], use_gitleaks=False, root=self.root)
        self.assertFalse(ok)
        self.assertEqual(list(report), [bad])

    def test_cli_sanitize_mode_runs(self):
        p = self._write("personas/c.md", r"path C:\Users\bob\x" + "\n")
        self.assertEqual(sanitizer.main(["--sanitize", p]), 0)
        with open(p, encoding="utf-8") as f:
            self.assertIn("<USER>", f.read())


if __name__ == "__main__":
    unittest.main()
