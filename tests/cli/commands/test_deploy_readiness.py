"""action_platform.cli.commands.deploy.readiness — checks print as written, brackets included."""

from __future__ import annotations

from types import SimpleNamespace

import typer
from rich.console import Console

from action_platform.cli.commands import deploy
from action_platform.core.context import Check
from tests.support import TempCase


class ReadinessPrintsChecksVerbatimTest(TempCase):
    def setUp(self):
        super().setUp()
        self.console = Console(record=True, width=200)
        self.patch(deploy, "console", self.console)
        tool = SimpleNamespace(
            check_readiness=lambda stage, version=None, target=None: [
                Check(
                    "deploy.targets",
                    False,
                    "no target [x]",
                    level="static",
                    fix="declare a target under [deploy] in platform.toml",
                )
            ]
        )
        self.patch(deploy, "_tool", lambda: tool)

    def test_a_fix_keeps_its_table_name(self):
        with self.assertRaises(typer.Exit):
            deploy.readiness(target=None, stage="prod", version=None)

        out = self.console.export_text()
        self.assertIn("fix: declare a target under [deploy] in platform.toml", out)
        self.assertIn("no target [x]", out)
