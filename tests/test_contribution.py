"""Tests for the community contribution gate (scripts/check_contribution.py)."""
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import check_contribution as gate  # noqa: E402

GOOD = "---\nname: flutter-fix\ndescription: How to fix Flutter bugs safely.\n---\n\n1. Reproduce with a test.\n"


class ContributionGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def skill(self, text, folder="flutter-fix"):
        path = os.path.join(self.tmp.name, "skills", folder, "SKILL.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def test_repo_public_files_pass(self):
        self.assertEqual(gate.main([]), 0)

    def test_good_skill_passes(self):
        self.assertEqual(gate.check(self.skill(GOOD)), [])

    def test_rejections(self):
        cases = {
            "privacy": GOOD + "key = sk-ant-api03-" + "a" * 40 + "\n",
            "draft": GOOD + "<!-- DRAFT by TIDOS 2026-10-24 -->\n",
            "private learned": GOOD + "## How it was done (learned from 61 successful tasks)\n",
            "standing rules": GOOD + "## The user's standing rules (they repeated these: obey them)\n",
            "frontmatter": "# no frontmatter\n",
            "does not match": GOOD.replace("name: flutter-fix", "name: other"),
            "too large": GOOD + "x" * (gate.MAX_BYTES + 1),
        }
        for expected, text in cases.items():
            problems = gate.check(self.skill(text))
            self.assertTrue(any(expected in p for p in problems), (expected, problems))
        self.assertTrue(gate.check(self.skill(GOOD + "see C:\\Users\\Jane\\notes.md\n")))


if __name__ == "__main__":
    unittest.main()
