"""Effort classification (fast/guide/deep), effort-aware guidance, compacted brief and token stats."""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tidos_session import brief, effort, guide, tokens  # noqa: E402


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Isolated(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = os.path.join(self.tmp.name, "home")
        self.tidos = os.path.join(self.home, ".tidos")
        self.project = os.path.join(self.tmp.name, "APP")
        write(os.path.join(self.project, "pubspec.yaml"), "name: app\n")
        real_expanduser = os.path.expanduser
        self.patches = [
            mock.patch.dict(os.environ, {"TIDOS_HOME_DIR": self.tidos}),
            mock.patch("os.path.expanduser",
                       side_effect=lambda p: p.replace("~", self.home, 1) if p.startswith("~") else real_expanduser(p)),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()


class EffortClassificationTests(Isolated):
    def test_fast(self):
        cases = ["why does the login page take 3 seconds to show?",
                 "fix a typo in the README",
                 "rename this variable x to count",
                 "Phase 1",
                 "",
                 "what is the pubspec version field for?"]
        for request in cases:
            with self.subTest(request=request):
                self.assertEqual(effort.classify(request), "fast")

    def test_guide(self):
        cases = ["add dark mode to the settings screen",
                 "the logout button does not work, fix it",
                 "implement the offline cache feature",
                 "deploy the web version to hosting"]
        for request in cases:
            with self.subTest(request=request):
                self.assertEqual(effort.classify(request), "guide")

    def test_deep(self):
        cases = ["refactor the whole storage layer across several files",
                 "investigate the intermittent crash and find the root cause",
                 "redesign the architecture of the chat module",
                 "performance issue: audit the whole app rendering path"]
        for request in cases:
            with self.subTest(request=request):
                self.assertEqual(effort.classify(request), "deep")


class EffortGuidanceTests(Isolated):
    def setUp(self):
        super().setUp()
        pb = os.path.join(self.tidos, "playbooks", "app")
        write(os.path.join(pb, "bugfix.md"), "---\ntype: bugfix\nstack: flutter/dart\nproject: APP\n---\n"
              "# bugfix: APP\n## How it was done\n1. Screens live in lib/screens/.\n\n## Pitfalls\n- run flutter analyze\n")
        write(os.path.join(pb, "notes.md"), "---\ntype: notes\n---\n- (2026-10-24) Logout helper: lib/utils/logout.dart\n")

    def _facts(self):
        from tidos_session import detect
        return detect.project_facts(self.project)

    def test_fast_guidance_is_short_and_skips_playbooks(self):
        _, text = guide.guidance("fix a typo in the README", self.project)
        self.assertIn("effort: fast", text)
        self.assertIn("do it directly", text)
        self.assertNotIn("lib/screens/", text)        # playbook narrative is skipped
        self.assertNotIn("Logout helper", text)       # notes are skipped too
        self.assertLess(len(text.encode("utf-8")), 400)  # a fraction of a guide playbook

    def test_guide_keeps_playbook_and_counts_served(self):
        from tidos_session import pbstate
        _, text = guide.guidance("the logout button does not work", self.project)
        self.assertIn("effort: guide", text)
        self.assertIn("lib/screens/", text)
        self.assertIn("run flutter analyze", text)
        self.assertEqual(pbstate.load()["served"]["app/bugfix.md"]["n"], 1)

    def test_deep_guidance_adds_plan_discipline(self):
        _, text = guide.guidance("systematically fix the logout crash and investigate the root cause", self.project)
        self.assertIn("effort: deep", text)
        self.assertIn("plan first", text)
        self.assertIn("Reproduce first", text)

    def test_deep_never_capped_harder_than_before(self):
        _, text = guide.guidance("investigate the intermittent crash with a systematic root cause plan", self.project)
        self.assertLessEqual(len(text.encode("utf-8")), guide.GUIDE_LIMIT)


class CompactBriefTests(Isolated):
    def facts(self):
        return {"name": "APP", "stack": ["flutter/dart"], "checks": ["flutter analyze"], "notes": []}

    def test_playbook_sections_dropped_from_the_brief(self):
        body = ("# bugfix: APP\n## How it was done\n1. Screens live in lib/screens/.\n\n"
                "## Checks that confirmed the work\n- flutter analyze (passed 3 of 3 tasks)\n\n"
                "## Pitfalls\n- run flutter analyze\n\n## Example requests\n- fix the logout crash")
        compact = brief._compact(body)
        self.assertIn("lib/screens/", compact)
        self.assertIn("run flutter analyze", compact)
        self.assertNotIn("passed 3 of 3", compact)
        self.assertNotIn("Example requests", compact)

    def test_per_request_policy_replaces_every_request(self):
        text = brief.guide_brief({"model": "m", "tier": "weak"}, self.facts())
        self.assertIn(brief.PER_REQUEST_HEADING, text)
        self.assertIn("NO guide call", text)
        self.assertIn("effort fast/guide/deep", text)
        self.assertNotIn("For EVERY new request", text)
        self.assertIn("targeted test beats the whole", text)   # rule 4 keeps verification, drops the ceremony
        self.assertLessEqual(len(text.encode("utf-8")), brief.GUIDE_LIMIT)

    def test_commands_footer_compacts_the_python_path_once(self):
        footer = brief.commands_footer()
        self.assertIn('CL "pkg" args` = `python -I "', footer)          # the full python.exe path appears once
        self.assertIn("Run: CL \"tidos_learn\" status", footer)
        self.assertIn("Run: CL \"tidos_session\" start --project .", footer)

    def test_every_command_still_listed_and_runnable(self):
        from tidos_session import commands
        footer = brief.commands_footer()
        for c in commands.COMMANDS:
            self.assertIn("/" + c.name, footer)                        # no capability dropped
        self.assertIn("python -I", footer)
        self.assertIn("/pkg/__main__.py", footer)                      # the CL legend is complete

    def test_tool_with_installed_commands_gets_a_pointer_not_the_list(self):
        from tidos_session import commands
        write(os.path.join(os.path.expanduser("~"), ".config", "opencode", "command", "TIDOSZIT.md"),
              "installed\n" + commands.MARK_TEXT)
        footer = brief.commands_footer({"tool": "opencode"})
        self.assertIn("/TIDOSZIT", footer)
        self.assertIn("/ menu", footer)                                # points at the tool's own menu
        self.assertIn("Never ask for, accept or repeat the control password", footer)
        self.assertNotIn("Run: CL", footer)                            # no 13-item list in the brief
        self.assertIn("Run: CL", brief.commands_footer({"tool": "unknown"}))  # no menu: the full list stays


class TokenStatsTests(Isolated):
    def test_est_and_sections(self):
        text = "# TIDOS GUIDE MODE\nhello short\n"
        st = tokens.stats(text)
        self.assertEqual(st["chars"], len(text.encode("utf-8")))
        self.assertEqual(st["tokens"], (len(text.encode("utf-8")) + 3) // 4)
        self.assertIn("TIDOS GUIDE MODE", st["sections"])

    def test_save_then_compare_baseline(self):
        from tidos_session import detect
        facts = {"name": "APP", "stack": ["flutter/dart"], "checks": ["flutter analyze"], "notes": []}
        before = brief.guide_brief({"model": "m", "tier": "weak"}, facts)
        tokens.save(before)
        self.assertTrue(os.path.isfile(os.path.join(self.tidos, tokens.STATS_FILE)))
        after = tokens.load()
        self.assertEqual(after["chars"], detect and len(before.encode("utf-8")))
        cur, _ = tokens.comparison(before)
        self.assertEqual((cur["tokens"], cur["chars"]), (after["tokens"], after["chars"]))


if __name__ == "__main__":
    unittest.main()
