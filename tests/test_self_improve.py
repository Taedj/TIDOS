"""prepare_branch: self-improvement must survive its own leftovers (merged recycle, unmerged refusal)."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location("self_improve", os.path.join(ROOT, "scripts", "self_improve.py"))
self_improve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(self_improve)


def git(cwd, *argv):
    r = subprocess.run(["git"] + list(argv), cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError("%s failed: %s%s" % (argv, r.stdout, r.stderr))
    return r.stdout


class Repo(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "config", "user.email", "t@t")
        git(self.repo, "config", "user.name", "T")
        self.commit("one")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp.name, ignore_errors=True)     # worktrees under tempdirs go with it

    def commit(self, text, name="f.txt"):
        with open(os.path.join(self.repo, name), "w") as f:
            f.write(text)
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", text)

    def off(self, work, branch):
        for attempt in range(3):                             # Windows file locks settle after a moment
            r = subprocess.run(["git", "worktree", "remove", "--force", work], cwd=self.repo,
                               capture_output=True, text=True)
            if r.returncode == 0:
                break
        git(self.repo, "branch", "-D", branch)


class PrepareBranchTests(Repo):
    def test_1_fresh_branch_just_creates_the_worktree(self):
        refused, work = self_improve.prepare_branch("auto/9-fresh", root=self.repo)
        self.assertIsNone(refused)
        self.assertTrue(work.endswith("wt"))
        self.off(work, "auto/9-fresh")

    def test_2_a_merged_leftover_is_recycled_not_a_crash(self):
        branch = "auto/1-weak"
        self.off(*self.call(branch))                          # first attempt leaves its branch behind
        self.commit("later")                                  # work moved on: the leftover is merged now
        refused, work = self_improve.prepare_branch(branch, root=self.repo)   # the 16:27 crash scenario
        self.assertIsNone(refused)
        self.assertEqual(git(self.repo, "rev-parse", "--short", branch).strip(),
                         git(self.repo, "rev-parse", "--short", "HEAD").strip())
        self.off(work, branch)

    def test_3_an_unmerged_attempt_is_refused_and_left_alone(self):
        branch = "auto/2-unmerged"
        git(self.repo, "checkout", "-q", "-b", branch)
        self.commit("agent work", "g.txt")
        git(self.repo, "checkout", "-q", "main")
        tip = git(self.repo, "rev-parse", "--short", branch).strip()
        refused, work = self_improve.prepare_branch(branch, root=self.repo)
        self.assertIn("UNMERGED", refused)
        self.assertIn("git branch -D", refused)               # the human decides; code never destroys work
        self.assertIsNone(work)
        self.assertEqual(git(self.repo, "rev-parse", "--short", branch).strip(), tip)  # untouched

    def test_4_recycling_is_announced_not_silent(self):
        branch = "auto/3-loud"
        self.call(branch)
        with mock.patch("builtins.print") as said:
            self.call(branch)
        self.assertTrue(any("Recycled" in str(c) for c in said.call_args_list), said.call_args_list)

    def call(self, branch):
        refused, work = self_improve.prepare_branch(branch, root=self.repo)
        self.assertIsNone(refused)
        return work, branch


class ImplementFallbackTests(unittest.TestCase):
    """A dead free model (server 'Unexpected server error') may not waste a run: the next free model tries."""

    @staticmethod
    def _proc(text, code):
        return subprocess.CompletedProcess([], code, text + "\n", "")

    def setUp(self):
        self.work = tempfile.mkdtemp(prefix="t-imp-")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.work, ignore_errors=True)

    def impl(self, runs):
        with mock.patch.object(self_improve.shutil, "which", return_value="C:/oc/opencode.cmd"), \
             mock.patch.object(self_improve.subprocess, "run", side_effect=runs) as called, \
             mock.patch("builtins.print"):
            code = self_improve.implement("opencode:opencode/muse-spark-1.3-contributor-free", "prompt", self.work)
        return code, [c.args[0][5] for c in called.call_args_list]

    def test_1_dead_model_falls_through_to_the_next_free_one(self):
        runs = [self._proc("Unexpected server error", 1), self._proc("made some edits", 0)]
        code, models = self.impl(runs)
        self.assertTrue(code)
        self.assertEqual(models, ["opencode/muse-spark-1.3-contributor-free", "opencode/big-pickle"])

    def test_2_every_model_dead_reports_it_instead_of_fake_success(self):
        code, _ = self.impl([self._proc("Unexpected server error", 1),
                             self._proc("unexpected server error", 1),
                             self._proc("nope", 1)])
        self.assertFalse(code)      # main() then exits 1: the journal/job shows a failure, nothing fake

    def test_3_claude_path_is_untouched_by_fallback(self):
        with mock.patch.object(self_improve.shutil, "which", return_value="C:/c/claude.exe"), \
             mock.patch.object(self_improve.subprocess, "run",
                               return_value=self._proc('{"is_error": false, "result": "r"}', 0)), \
             mock.patch("builtins.print"):
            self.assertTrue(self_improve.implement("claude:sonnet", "prompt", self.work))


if __name__ == "__main__":
    unittest.main()
