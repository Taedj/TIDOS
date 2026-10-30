"""Tests for safe self-update (tidos_session.updater) with real temporary git repositories."""
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_session import updater  # noqa: E402

GATE = [("checks", ["-c", "import os, sys; sys.exit(0 if os.path.exists('GOOD') else 1)"])]


def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert r.returncode == 0, (args, r.stderr)
    return r.stdout.strip()


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        gitconfig = os.path.join(t, "gitconfig")
        with open(gitconfig, "w") as f:
            f.write("[user]\n\tname = T\n\temail = t@example.invalid\n[init]\n\tdefaultBranch = main\n")
        self.bare = os.path.join(t, "upstream.git")
        self.env = mock.patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": gitconfig, "GIT_CONFIG_NOSYSTEM": "1", "TIDOS_UPDATE_TEST_URL": self.bare,
            "TIDOS_HOME_DIR": os.path.join(t, "home")})
        self.env.start()
        self.up = os.path.join(t, "upstream")
        os.makedirs(os.path.join(self.up, "core"))
        os.makedirs(os.path.join(self.up, "config"))
        for rel in updater.MARKERS:
            self.write(self.up, rel, "x\n")
        git(self.up, "init", "-q")
        self.release("v1.0.0", good=True)
        git(t, "init", "-q", "--bare", self.bare)
        git(self.up, "remote", "add", "origin", self.bare)
        git(self.up, "push", "-q", "origin", "main", "--tags")
        self.repo = os.path.join(t, "checkout")
        git(t, "clone", "-q", self.bare, self.repo)
        git(self.repo, "checkout", "-q", "--detach", "v1.0.0")

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def write(self, root, rel, text):
        with open(os.path.join(root, rel), "w", encoding="utf-8") as f:
            f.write(text)

    def release(self, tag, good=True):
        self.write(self.up, "VERSION", tag + "\n")
        if good:
            self.write(self.up, "GOOD", "1\n")
        elif os.path.exists(os.path.join(self.up, "GOOD")):
            os.remove(os.path.join(self.up, "GOOD"))
        git(self.up, "add", "-A")
        git(self.up, "commit", "-q", "-m", tag)
        git(self.up, "tag", tag)
        if os.path.exists(self.bare):
            git(self.up, "push", "-q", "origin", "main", "--tags")

    def head(self):
        return git(self.repo, "rev-parse", "HEAD")

    def test_versions(self):
        self.assertEqual(updater.bump("v5.3.1", "v5.3.2"), "patch")
        self.assertEqual(updater.bump("v5.3.1", "v5.4.0"), "minor")
        self.assertEqual(updater.bump("v5.3.1", "v6.0.0"), "major")
        self.assertIsNone(updater.bump("v5.3.1", "v5.3.1"))
        self.assertIsNone(updater.bump("v5.3.1", "v5.3.0"))

    def test_patch_is_staged_applied_and_rolled_back(self):
        self.assertEqual(updater.check(self.repo)["target"], None)          # up to date
        self.release("v1.0.1")
        before = self.head()
        info = updater.check(self.repo)
        self.assertEqual((info["current"], info["target"], info["bump"]), ("v1.0.0", "v1.0.1", "patch"))
        staged = updater.stage(info, self.repo, gates=GATE)
        self.assertTrue(staged["ok"], staged)
        self.assertEqual(self.head(), before)                              # staging never touches the checkout
        self.assertEqual(len(git(self.repo, "worktree", "list").splitlines()), 1)  # staging copy removed
        lines = updater.auto(self.repo, gates=GATE, apply_patch=True)
        self.assertIn("applied", lines[-1])
        self.assertEqual(self.head(), git(self.repo, "rev-parse", "v1.0.1^{commit}"))
        self.assertEqual(updater.rollback(self.repo)["to"], before[:12])
        self.assertEqual(self.head(), before)
        with self.assertRaises(updater.Refused):
            updater.rollback(self.repo)                                    # once

    def test_a_release_that_fails_its_checks_is_never_applied(self):
        self.release("v1.0.1", good=False)
        before = self.head()
        lines = updater.auto(self.repo, gates=GATE, apply_patch=True)
        self.assertIn("FAILED", lines[1])
        self.assertIn("not applied", lines[-1])
        self.assertEqual(self.head(), before)
        with self.assertRaises(updater.Refused):
            updater.apply(self.repo)
        self.assertTrue(os.path.isfile(updater.status()["staged"]["log"]))

    def test_minor_waits_for_you_and_patch_respects_the_switch(self):
        self.release("v1.1.0")
        before = self.head()
        self.assertIn("waiting for you: a minor release", updater.auto(self.repo, gates=GATE, apply_patch=True)[-1])
        self.assertEqual(self.head(), before)
        self.assertEqual(updater.apply(self.repo)["to"], "v1.1.0")           # your click
        self.release("v1.1.1")
        self.assertIn("auto_update switch is off", updater.auto(self.repo, gates=GATE, apply_patch=False)[-1])

    def test_guards_protect_your_work(self):
        self.release("v1.0.1")
        updater.stage(updater.check(self.repo), self.repo, gates=GATE)
        self.write(self.repo, "VERSION", "edited by you\n")
        with self.assertRaises(updater.Refused) as e:
            updater.apply(self.repo)
        self.assertIn("edited", str(e.exception))
        git(self.repo, "checkout", "--", "VERSION")
        git(self.repo, "checkout", "-q", "-b", "mine")
        self.write(self.repo, "NOTES", "mine\n")
        git(self.repo, "add", "NOTES")
        git(self.repo, "commit", "-q", "-m", "local work")
        with self.assertRaises(updater.Refused) as e:
            updater.apply(self.repo)
        self.assertIn("local commit", str(e.exception))
        git(self.repo, "remote", "set-url", "origin", "https://example.invalid/fork.git")
        with self.assertRaises(updater.Refused) as e:
            updater.check(self.repo, fetch=False)
        self.assertIn("fork", str(e.exception))


if __name__ == "__main__":
    unittest.main()
