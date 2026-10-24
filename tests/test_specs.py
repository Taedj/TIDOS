"""The spec validator (scripts/validate_specs.py) must pass on the repository."""
import io
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import validate_specs  # noqa: E402


class SpecTests(unittest.TestCase):
    def test_repository_specs_are_valid(self):
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            code = validate_specs.main()
        self.assertEqual(code, 0, out.getvalue())

    def test_detects_problems(self):
        errors = []
        with mock.patch.object(validate_specs, "read", side_effect=lambda rel: {
                "VERSION.md": "**Current Version**: 4.1.0", "config/framework.md": "  current: 4.0.0"}[rel]):
            validate_specs.check_versions(errors)
        self.assertEqual(errors, ["version mismatch: VERSION.md 4.1.0 vs config/framework.md 4.0.0"])


if __name__ == "__main__":
    unittest.main()
