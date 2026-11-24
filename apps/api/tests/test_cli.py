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


class DbBackupRestoreTest(TempCase):
    def setUp(self):
        super().setUp()
        from typer.testing import CliRunner

        self.db = importlib.import_module("app.cli.db")
        self.runner = CliRunner()
        self.seen = []
        test = self

        class FakePostgres:
            @classmethod
            def from_url(cls, url):
                test.seen.append(("url", url))
                return cls()

            def backup(self, out):
                test.seen.append(("backup", out))

            def restore(self, dump, force=False):
                test.seen.append(("restore", dump, force))

        self.patch(self.db, "Postgres", FakePostgres)

    def invoke(self, *args, **kwargs):
        return self.runner.invoke(self.db.app, list(args), **kwargs)

    def test_backup_names_a_timestamped_file_or_writes_stdout(self):
        named = self.invoke("backup", "--url", "postgres://h/db")
        piped = self.invoke("backup", "--url", "postgres://h/db", "--out", "-")

        self.assertEqual(named.exit_code, 0, named.output)
        self.assertEqual(piped.exit_code, 0, piped.output)
        out = self.seen[1][1]
        self.assertRegex(out.name, r"^action_platform-\d{8}T\d{6}Z\.sql$")
        self.assertIn(f"wrote {out}", named.output)
        self.assertEqual(self.seen[3], ("backup", None))

    def test_restore_reads_a_file_or_stdin_and_passes_force(self):
        dump = self.tmp_path / "dump.sql"
        dump.write_bytes(b"CREATE TABLE t ();\n")

        from_file = self.invoke("restore", str(dump), "--url", "postgres://h/db")
        from_stdin = self.invoke(
            "restore", "-", "--force", "--url", "postgres://h/db", input="SELECT 1;\n"
        )

        self.assertEqual(from_file.exit_code, 0, from_file.output)
        self.assertEqual(from_stdin.exit_code, 0, from_stdin.output)
        self.assertEqual(self.seen[1], ("restore", b"CREATE TABLE t ();\n", False))
        self.assertEqual(self.seen[3], ("restore", b"SELECT 1;\n", True))

    def test_restore_refuses_a_missing_file(self):
        result = self.invoke(
            "restore", str(self.tmp_path / "nope.sql"), "--url", "postgres://h/db"
        )

        self.assertIsInstance(result.exception, self.db.ActionPlatformError)
        self.assertEqual([s for s in self.seen if s[0] == "restore"], [])
