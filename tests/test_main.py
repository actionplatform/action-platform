"""action_platform.main — the CLI entry point."""

import os
from unittest import mock

from action_platform import bootstrap, main
from tests.support import TempCase


class MainTest(TempCase):
    def test_a_dotenv_in_the_working_directory_is_loaded_before_the_command_runs(self):
        (self.tmp_path / ".env").write_text("AP_PROBE=from-dotenv\n")
        self.delenv("AP_PROBE")
        seen = {}
        self.patch(
            bootstrap,
            "observe",
            lambda component, config, version=None: seen.setdefault(
                "component", component
            ),
        )
        self.patch(
            main, "app", lambda: seen.setdefault("probe", os.environ.get("AP_PROBE"))
        )

        with mock.patch("pathlib.Path.cwd", return_value=self.tmp_path):
            main.main()

        self.assertEqual(seen, {"component": "cli", "probe": "from-dotenv"})
