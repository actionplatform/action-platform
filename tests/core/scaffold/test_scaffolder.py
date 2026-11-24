"""action_platform.core.scaffold.scaffolder — a plain repository copied as a new project."""

from __future__ import annotations

import tomllib

from action_platform.core.exception import TemplateError
from action_platform.core.scaffold.scaffolder import generate_project
from action_platform.core.scaffold.catalog import Leaf
from tests.support import TempCase


class PlainRepositoryTest(TempCase):
    def setUp(self):
        super().setUp()
        self.source = self.tmp_path / "starter"
        self.source.mkdir()
        (self.source / "README.md").write_text("# starter\n")
        (self.source / ".git").mkdir()
        self.output = self.tmp_path / "out"
        self.output.mkdir()

    def test_renames_the_manifest_and_moves_the_owner(self):
        (self.source / "platform.toml").write_text(
            '[project]\nname = "starter"\ntype = "web"\n\n'
            '[source_host]\nkind = "github"\nrepo = "someone/starter"\n'
        )

        project = generate_project(
            self.source,
            Leaf("web", "", "starter", plain=True),
            "My Shop",
            None,
            self.output,
            {"github_owner": "acme"},
        )
        data = tomllib.loads((project / "platform.toml").read_text())

        self.assertEqual(project, self.output / "my-shop")
        self.assertEqual(data["project"]["name"], "my-shop")
        self.assertEqual(data["source_host"]["repo"], "acme/starter")
        self.assertEqual((project / "LAST_VERSION").read_text(), "0.0.0\n")
        self.assertFalse((project / ".git").exists())

    def test_a_manifest_without_a_source_host_gets_the_owner_s(self):
        (self.source / "platform.toml").write_text('[project]\nname = "starter"\n')

        project = generate_project(
            self.source,
            Leaf("web", "", "starter", plain=True),
            "My Shop",
            None,
            self.output,
            {"github_owner": "acme", "source_host": "gitlab"},
        )
        data = tomllib.loads((project / "platform.toml").read_text())

        self.assertEqual(
            data["source_host"], {"kind": "gitlab", "repo": "acme/my-shop"}
        )

    def test_seeds_a_manifest_when_the_repository_has_none(self):
        project = generate_project(
            self.source,
            Leaf("library", "", "starter", plain=True),
            "tool",
            "gitlab",
            self.output,
            {"description": 'says "hi"'},
        )
        data = tomllib.loads((project / "platform.toml").read_text())

        self.assertEqual(
            data["project"],
            {
                "description": 'says "hi"',
                "name": "tool",
                "type": "library",
                "ci": "gitlab",
            },
        )
        self.assertEqual(data["release"]["strategy"], "semver")
        self.assertFalse((project / ".git").exists())

    def test_refuses_an_existing_target(self):
        (self.output / "tool").mkdir()

        with self.assertRaises(TemplateError):
            generate_project(
                self.source,
                Leaf("library", "", "starter", plain=True),
                "tool",
                None,
                self.output,
            )


class RenderedOwnerTest(TempCase):
    def setUp(self):
        super().setUp()
        from action_platform.testing.fixtures import template_repo

        self.repo = template_repo(self.tmp_path / "templates")
        self.leaf = Leaf("web", "python", "fastapi")
        self.output = self.tmp_path / "out"
        self.output.mkdir()

    def generate(self, extra: dict):
        return generate_project(
            self.repo, self.leaf, "Demo", "gitlab", self.output, extra
        )

    def test_the_owner_and_host_name_the_repository(self):
        project = self.generate(
            {
                "github_owner": "alice",
                "source_host": "gitlab",
                "author": "Alice",
                "license": "mit",
            }
        )
        data = tomllib.loads((project / "platform.toml").read_text())

        self.assertEqual(data["source_host"], {"kind": "gitlab", "repo": "alice/demo"})
        self.assertEqual((project / "LICENSE").read_text(), "mit Alice\n")

    def test_without_an_owner_there_is_no_source_host_and_nobody_s_name(self):
        project = self.generate({})
        data = tomllib.loads((project / "platform.toml").read_text())

        self.assertNotIn("source_host", data)
        self.assertEqual((project / "LICENSE").read_text(), "none Demo\n")
