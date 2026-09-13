"""action_platform.core.release.changelog — rendering and prepending."""

from __future__ import annotations

import unittest

from action_platform.core.release import changelog
from tests.support import TempCase


class RenderTest(unittest.TestCase):
    def test_buckets_by_type_and_drops_non_conventional(self):
        out = changelog.render(
            "0.2.0",
            [
                "feat(api): new provider",
                "fix: crash on empty tag",
                "ci: release v0.1.9",
                "feat!: drop python 3.9",
                "not a conventional commit",
            ],
        )

        self.assertIn("## v0.2.0", out)
        self.assertIn("### Breaking Changes", out)
        self.assertIn("- drop python 3.9", out)
        self.assertIn("### Features", out)
        self.assertIn("- **api:** new provider", out)
        self.assertIn("### Bug Fixes", out)
        self.assertIn("- crash on empty tag", out)
        self.assertIn("### CI", out)
        self.assertNotIn("not a conventional", out)

    def test_empty(self):
        self.assertTrue(changelog.render("0.1.0", []).startswith("## v0.1.0"))


class PrependTest(TempCase):
    def test_accumulates_newest_first(self):
        path = self.tmp_path / "CHANGELOG.md"
        changelog.prepend(path, changelog.render("0.1.0", ["feat: first"]))
        changelog.prepend(path, changelog.render("0.2.0", ["fix: second"]))
        text = path.read_text()

        self.assertTrue(text.startswith("# Changelog\n"))
        self.assertEqual(text.count("# Changelog"), 1)
        self.assertLess(text.index("## v0.2.0"), text.index("## v0.1.0"))
        self.assertIn("- second", text)
        self.assertIn("- first", text)
