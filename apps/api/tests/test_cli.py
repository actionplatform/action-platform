"""app.cli — the `action-platform-api` entry point."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from action_platform.testing.fixtures import TempCase

API = Path(__file__).resolve().parents[1]
RECORD_READS = """
import action_platform.settings as s
seen = []
for key, read in list(s.SLICES.items()):
    s.SLICES[key] = (lambda key, read: lambda env: (seen.append(key), read(env))[1])(key, read)
"""


class EntryPointTest(TempCase):
    def test_importing_the_api_reads_no_setting(self):
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join([str(API), str(API.parents[1])])

        out = subprocess.run(
            [
                sys.executable,
                "-c",
                RECORD_READS + "import app.cli, app.api.app\nprint(seen)",
            ],
            cwd=self.tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

        self.assertEqual(out, "[]")

    def test_a_dotenv_in_the_working_directory_is_loaded_before_the_command_runs(self):
        cli = importlib.import_module("app.cli.app")
        (self.tmp_path / ".env").write_text("AP_PROBE=from-dotenv\n")
        self.delenv("AP_PROBE")
        seen = {}
        self.patch(
            "action_platform.bootstrap.observe",
            value=lambda component, config, version=None: seen.setdefault(
                "component", component
            ),
        )
        self.patch(
            cli, "app", lambda: seen.setdefault("probe", os.environ.get("AP_PROBE"))
        )

        with mock.patch("pathlib.Path.cwd", return_value=self.tmp_path):
            cli.main()

        self.assertEqual(seen, {"component": "api", "probe": "from-dotenv"})

    def test_the_uvicorn_factory_starts_like_an_entry_point(self):
        server = importlib.import_module("app.api.app")
        calls = []
        self.patch(
            server,
            "bootstrap",
            lambda component, version=None: calls.append(component),
        )
        self.patch(server, "build", lambda origins: calls.append(("build", origins)))
        self.setenv("AP_CORS", "http://localhost:3000")

        server.create_app()

        self.assertEqual(calls, ["api", ("build", ["http://localhost:3000"])])
