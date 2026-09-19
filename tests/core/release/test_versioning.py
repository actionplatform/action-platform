"""action_platform.core.release.versioning — bumps, rc counters and version constants kept in sync."""

from __future__ import annotations

import unittest

from action_platform.core.exception import ActionPlatformError
from action_platform.core.release import versioning
from tests.support import TempCase


class BumpTest(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(versioning.bump("1.2.3", "patch"), "1.2.4")
        self.assertEqual(versioning.bump("1.2.3", "minor"), "1.3.0")
        self.assertEqual(versioning.bump("1.2.3", "major"), "2.0.0")
        self.assertEqual(versioning.bump("1.2.3", "2.5.0"), "2.5.0")

    def test_invalid(self):
        with self.assertRaises(ActionPlatformError):
            versioning.bump("not-a-version", "patch")

    def test_strip_pre_and_next_rc(self):
        self.assertEqual(versioning.strip_pre("0.3.2-rc.1"), "0.3.2")
        self.assertEqual(versioning.next_rc("0.3.2", []), "0.3.2-rc.1")
        self.assertEqual(
            versioning.next_rc("0.3.2", ["v0.3.2-rc.1", "v0.3.2-rc.2", "v0.3.1"]),
            "0.3.2-rc.3",
        )


class SyncFilesTest(TempCase):
    def test_manifests(self):
        (self.tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n\n[tool.poetry]\nversion = "0.1.0"\n'
        )
        (self.tmp_path / "package.json").write_text(
            '{\n  "name": "x",\n  "version": "0.1.0"\n}\n'
        )
        (self.tmp_path / "pkg").mkdir()
        (self.tmp_path / "pkg" / "__init__.py").write_text('__version__ = "0.1.0"\n')

        touched = versioning.sync_files(self.tmp_path, "0.2.0")

        self.assertEqual(touched, ["pyproject.toml", "package.json", "pkg/__init__.py"])
        self.assertEqual(
            (self.tmp_path / "pyproject.toml").read_text().count('version = "0.2.0"'), 2
        )
        self.assertIn(
            '"version": "0.2.0"', (self.tmp_path / "package.json").read_text()
        )
        self.assertIn(
            '__version__ = "0.2.0"', (self.tmp_path / "pkg" / "__init__.py").read_text()
        )
        self.assertEqual(versioning.sync_files(self.tmp_path, "0.2.0"), [])

    def test_version_constants_per_language(self):
        files = {
            "mylib.go": 'package mylib\n\nconst Version = "0.1.0"\n',
            "internal/app/app.go": 'package app\n\nconst Version = "0.1.0"\n',
            "manifest.json": '{\n  "name": "x",\n  "version": "0.1.0"\n}\n',
            "pom.xml": "<project>\n  <groupId>g</groupId>\n  <version>0.1.0</version>\n  <dependencies>\n    <dependency>\n      <version>5.0.0</version>\n    </dependency>\n  </dependencies>\n</project>\n",
            "src/lib.rs": 'pub const VERSION: &str = "0.1.0";\n',
            "src/index.ts": 'export const VERSION = "0.1.0";\n',
            "src/Version.php": "<?php\nfinal class Version\n{\n    public const VERSION = '0.1.0';\n}\n",
            "src/main/java/com/acme/Version.java": 'public final class Version {\n    public static final String VERSION = "0.1.0";\n}\n',
            "app/version.rb": 'module Acme\n  VERSION = "0.1.0"\nend\n',
        }
        for rel, text in files.items():
            path = self.tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)

        touched = versioning.sync_files(self.tmp_path, "0.2.0")

        self.assertEqual(set(touched), set(files))
        for rel in files:
            self.assertIn("0.2.0", (self.tmp_path / rel).read_text())
            self.assertNotIn("0.1.0", (self.tmp_path / rel).read_text())
        self.assertIn(
            "<version>5.0.0</version>", (self.tmp_path / "pom.xml").read_text()
        )

    def test_version_constants_inside_templates_are_left_alone(self):
        path = self.tmp_path / "projects" / "{{cookiecutter.project_slug}}" / "app.go"
        path.parent.mkdir(parents=True)
        path.write_text('package app\n\nconst Version = "0.0.0"\n')

        self.assertEqual(versioning.sync_files(self.tmp_path, "0.2.0"), [])
        self.assertIn('"0.0.0"', path.read_text())
