"""End-to-end test of /TIDOSZIT in a real browser (Playwright + Chromium).

Opt-in (needs `pip install playwright` + `playwright install chromium`):  TIDOS_E2E=1 python -m pytest tests/test_dashboard_e2e.py
Runs against a temp brain, a fake Firebase, a temp copy of config/framework.md and a fake Ask model:
nothing real is read, written or sent.
"""
import os
import re
import shutil
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tidos_brain import db  # noqa: E402
from tidos_dashboard import auth, explore, server  # noqa: E402
from test_dashboard import CFG, FakeFirebase  # noqa: E402
from test_learn import add_session  # noqa: E402

try:
    from playwright.sync_api import sync_playwright
except ImportError:  # pragma: no cover
    sync_playwright = None

PASSWORD = "E2e-Passw0rd!"
CWD = r"D:\work\Dev\APP"
CALLS = [("read", CWD + r"\lib\a.dart"), ("edit", CWD + r"\lib\a.dart")]


@unittest.skipUnless(os.environ.get("TIDOS_E2E") == "1" and sync_playwright, "set TIDOS_E2E=1 (needs Playwright)")
class DashboardE2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        home = os.path.join(cls.tmp.name, "home")
        framework = os.path.join(cls.tmp.name, "framework.md")
        shutil.copy(explore.FRAMEWORK, framework)
        cls.framework = framework
        cls.patches = [
            mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": home,
                                         "TIDOS_CONTROL_FILE": os.path.join(cls.tmp.name, "control.json")}),
            mock.patch.object(explore, "FRAMEWORK", framework),
            mock.patch("tidos_learn.summarize.ask_strong_model",
                       lambda prompt, **kw: ("APP had 1 failed task: the login crash.", None)),
        ]
        for p in cls.patches:
            p.start()
        os.makedirs(os.path.join(home, "memory"))
        with open(os.path.join(home, "memory", "LESSONS.md"), "w", encoding="utf-8") as f:
            f.write("# Lessons\nThe login crash came from a null token.\n")
        db_path = os.path.join(cls.tmp.name, "brain.db")
        conn = db.connect(db_path)
        add_session(conn, "s", CWD, "APP", "claude-opus-5-5", [
            ("fix the login crash on android", "failure", 0, 0, CALLS, [("flutter test", 0)]),
            ("add a dark theme toggle", "success", 1, 0, CALLS, [("flutter test", 1)])])
        conn.close()
        cls.fb = FakeFirebase()
        cls.fb.doc = auth.hash_password(PASSWORD, iterations=1000)
        cls.srv = server.ControlServer(port=0, cfg=CFG, db_path=db_path, fb=cls.fb)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = "http://localhost:%d" % cls.srv.port
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()
        cls.srv.shutdown()
        cls.srv.server_close()
        for p in reversed(cls.patches):
            p.stop()
        cls.tmp.cleanup()

    def open(self, width=1440, height=1000):
        ctx = self.browser.new_context(viewport={"width": width, "height": height})
        page = ctx.new_page()
        errors = []
        page.on("console", lambda m: m.type == "error" and errors.append(m.text))
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(self.base + "/")
        page.wait_for_selector("#googleBtn")
        page.evaluate("""async (pw) => {
            const h = {'Content-Type': 'application/json'};
            await fetch('/api/auth/google', {method: 'POST', headers: h, body: JSON.stringify({idToken: 'owner-token'})});
            await fetch('/api/auth/password', {method: 'POST', headers: h, body: JSON.stringify({password: pw})});
        }""", PASSWORD)
        page.goto(self.base + "/")
        page.wait_for_selector("#app:not(.hidden)")
        return ctx, page, errors

    def test_login_wall(self):
        ctx = self.browser.new_context()
        page = ctx.new_page()
        page.goto(self.base + "/")
        page.wait_for_selector("#googleBtn")
        self.assertTrue(page.is_hidden("#app"))
        page.evaluate("""async () => {
            const h = {'Content-Type': 'application/json'};
            await fetch('/api/auth/google', {method: 'POST', headers: h, body: JSON.stringify({idToken: 'owner-token'})});
        }""")
        page.goto(self.base + "/")
        page.fill("#pw", "wrong-password-1A")
        page.click("#stage-password button[type=submit]")
        page.locator("#loginMsg").filter(has_text=re.compile(".+")).wait_for()  # no string eval: the CSP forbids it
        self.assertTrue(page.is_hidden("#app"))
        ctx.close()

    def test_every_tab_renders_without_errors(self):
        ctx, page, errors = self.open()
        for view in ("status", "live", "security", "dungeons", "playbooks", "army", "memory", "evolution", "tools"):
            page.click(".tab[data-view=%s]" % view)
            page.wait_for_selector("#view-%s:not(.hidden)" % view)
            page.wait_for_timeout(300)
        self.assertEqual(errors, [])
        ctx.close()

    def test_search_ask_settings_backup(self):
        ctx, page, errors = self.open()
        page.fill("#askQ", "login crash")
        page.click("#askBar button[data-mode=search]")
        page.wait_for_selector("#askBody .hit")
        kinds = page.eval_on_selector_all("#askBody .hit .pill", "els => els.map(e => e.textContent)")
        self.assertEqual(sorted(kinds), ["memory", "task"])
        page.click("#askBody .hitlink[data-kind=memory]")
        page.locator("#memView", has_text="null token").wait_for()

        page.fill("#askQ", "why did APP tasks fail?")
        page.click("#askBar button[data-mode=ask]")
        page.wait_for_selector("#askBody .answer")
        self.assertIn("login crash", page.text_content("#askBody .answer"))

        page.click(".tab[data-view=security]")
        page.wait_for_selector("#settings [data-key='persona_factory.depth_threshold']")
        page.fill("#settings [data-key='persona_factory.depth_threshold']", "5")
        page.dispatch_event("#settings [data-key='persona_factory.depth_threshold']", "change")
        page.wait_for_selector("#settingsMsg.ok")
        with open(self.framework, encoding="utf-8") as f:
            self.assertIn("depth_threshold: 5", f.read())

        page.click("#backupBtn")
        page.wait_for_selector("#backups .kv")
        self.assertEqual(len(explore.list_backups()), 1)
        self.assertEqual(errors, [])
        ctx.close()

    def test_mobile_has_no_horizontal_scroll(self):
        ctx, page, errors = self.open(390, 844)
        for view in ("status", "security", "tools", "evolution"):
            page.click(".tab[data-view=%s]" % view)
            page.wait_for_timeout(400)
            overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
            self.assertFalse(overflow, view)
        self.assertEqual(errors, [])
        ctx.close()

    def test_arabic_interface_is_rtl_and_switches_back(self):
        ctx, page, errors = self.open(390, 844)
        page.click("#app .lang-switch")  # reloads in Arabic; the session survives
        page.wait_for_selector("html[dir=rtl] #app:not(.hidden)")
        self.assertEqual(page.text_content(".tab[data-view=status]"), "الحالة")
        self.assertEqual(page.text_content("#app .lang-switch"), "English")
        page.locator("#quests", has_text="أنجز 3 مهام").wait_for()  # server text translated
        for view in ("status", "live", "security", "tools", "evolution", "playbooks", "army", "memory", "dungeons"):
            page.click(".tab[data-view=%s]" % view)
            page.wait_for_timeout(300)
            self.assertFalse(page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1"), view)
        page.fill("#askQ", "why did APP fail?")
        page.click("#askBar button[data-mode=ask]")
        page.locator("#askBody .answer").wait_for()
        page.click("#app .lang-switch")
        page.wait_for_selector("html[dir=ltr] #app:not(.hidden)")
        self.assertEqual(page.text_content(".tab[data-view=status]"), "Status")
        self.assertEqual(errors, [])
        ctx.close()


if __name__ == "__main__":
    unittest.main()
