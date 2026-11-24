"""action_platform.cli.commands.init — owner, author, licence and visibility come from the user."""

from __future__ import annotations

import tomllib
from unittest import mock

from action_platform.cli.commands import init
from action_platform.core.exception import TemplateError
from action_platform.core.scaffold import identity
from action_platform.core.wiring import wired
from action_platform.testing.fixtures import template_repo
from tests.support import TempCase


class InitOwnerTest(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv(
            "ACTION_PLATFORM_TEMPLATES", str(template_repo(self.tmp_path / "t"))
        )
        self.out = self.tmp_path / "out"
        self.out.mkdir()
        self.patch(identity, "git_author", lambda: "Ana Lima")
        self.patch(init.sys.stdin, "isatty", lambda: False)
        self.pushed: list[tuple] = []
        self.patch(
            type(wired.scaffolder()),
            "push",
            lambda _self, project, private=False, **kw: self.pushed.append(
                (project.name, private)
            )
            or "url",
        )

    def run_init(self, **options):
        defaults = dict(
            type_="web",
            stack="python",
            template="fastapi",
            name="Demo",
            ci="github",
            cloud=None,
            output=self.out,
            owner=None,
            author=None,
            license_=None,
            host=None,
            push=True,
            public=False,
            list_=False,
            update=False,
            source=None,
        )
        init.run(**{**defaults, **options})

        return tomllib.loads((self.out / "demo" / "platform.toml").read_text())

    def test_the_account_of_the_host_owns_a_private_repository(self):
        self.patch(identity, "account", lambda kind: "alice")

        data = self.run_init()

        self.assertEqual(data["source_host"], {"kind": "github", "repo": "alice/demo"})
        self.assertEqual(self.pushed, [("demo", True)])
        self.assertEqual((self.out / "demo" / "LICENSE").read_text(), "none Ana Lima\n")

    def test_without_an_owner_nothing_is_pushed(self):
        self.patch(identity, "account", lambda kind: "")

        with self.assertRaisesRegex(TemplateError, "pass --owner"):
            self.run_init()

        self.assertEqual(self.pushed, [])
        self.assertNotIn("source_host", self.run_init(push=False))

    def test_flags_win(self):
        self.patch(
            identity, "account", mock.Mock(side_effect=AssertionError("not asked"))
        )

        data = self.run_init(
            owner="acme", author="Bo", license_="apache-2.0", ci="gitlab", public=True
        )

        self.assertEqual(data["source_host"], {"kind": "gitlab", "repo": "acme/demo"})
        self.assertEqual(self.pushed, [("demo", False)])
        self.assertEqual((self.out / "demo" / "LICENSE").read_text(), "apache-2.0 Bo\n")
