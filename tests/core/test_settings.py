import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock, skipUnless

from action_platform.options import WorkspacesConfig
from action_platform.settings import Settings, database_url_from_parts, secret
from tests.support import TempCase

RECORD_READS = """
import action_platform.settings as s
seen = []
for key, read in list(s.SLICES.items()):
    s.SLICES[key] = (lambda key, read: lambda env: (seen.append(key), read(env))[1])(key, read)
"""


def test_secret_prefers_file(tmp_path, monkeypatch):
    path = tmp_path / "token"
    path.write_text("from-file\n")
    monkeypatch.setenv("AP_API_TOKEN_FILE", str(path))
    monkeypatch.setenv("AP_API_TOKEN", "from-env")

    assert secret("AP_API_TOKEN") == "from-file"


def test_secret_falls_back_across_names(monkeypatch):
    monkeypatch.delenv("AP_AUTH_SECRET", raising=False)
    monkeypatch.delenv("AP_AUTH_SECRET_FILE", raising=False)
    monkeypatch.setenv("BETTER_AUTH_SECRET", "legacy")

    assert secret("AP_AUTH_SECRET", "BETTER_AUTH_SECRET") == "legacy"


def test_secret_skips_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AP_API_TOKEN_FILE", str(tmp_path / "missing"))
    monkeypatch.setenv("AP_API_TOKEN", "from-env")

    assert secret("AP_API_TOKEN") == "from-env"


def test_database_url_from_parts(tmp_path, monkeypatch):
    path = tmp_path / "pw"
    path.write_text("p@ss:word")
    monkeypatch.setenv("AP_DB_HOST", "db")
    monkeypatch.setenv("AP_DB_PASSWORD_FILE", str(path))
    monkeypatch.delenv("AP_DB_PASSWORD", raising=False)

    assert (
        database_url_from_parts()
        == "postgres://action_platform:p%40ss%3Aword@db:5432/action_platform"
    )


def test_database_url_needs_host(monkeypatch):
    monkeypatch.delenv("AP_DB_HOST", raising=False)

    assert database_url_from_parts() == ""


class ImportIsPureTest(TempCase):
    def run_python(self, code: str) -> str:
        env = {k: v for k, v in os.environ.items() if k != "AP_PROBE"}
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2])

        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=self.tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def test_importing_settings_leaves_a_dotenv_alone(self):
        (self.tmp_path / ".env").write_text("AP_PROBE=from-dotenv\n")

        out = self.run_python(
            "import os, action_platform.settings; print(os.environ.get('AP_PROBE', '-'))"
        )

        self.assertEqual(out, "-")

    @skipUnless(importlib.util.find_spec("mcp"), "mcp is not installed")
    def test_importing_the_entry_points_reads_no_setting(self):
        out = self.run_python(
            RECORD_READS
            + "import action_platform.main, action_platform.mcp.server\nprint(seen)"
        )

        self.assertEqual(out, "[]")


class LazySettingsTest(TempCase):
    def test_the_environment_is_read_when_a_setting_is_asked_for(self):
        fresh = Settings()
        self.setenv("AP_SENTRY_DSN", "https://key@example.com/1")

        self.assertEqual(fresh.observability.dsn, "https://key@example.com/1")

        self.setenv("AP_SENTRY_DSN", "https://key@example.com/2")

        self.assertEqual(fresh.observability.dsn, "https://key@example.com/2")

    def test_from_env_answers_from_its_own_mapping(self):
        self.setenv("AP_WORKSPACE_TTL", "99")

        own = Settings.from_env(
            {"AP_WORKSPACE_TTL": "3", "AP_DB_HOST": "db", "AP_DB_PASSWORD": "pw"}
        )

        self.assertEqual(own.workspaces.ttl, 3)
        self.assertEqual(
            own.database.url, "postgres://action_platform:pw@db:5432/action_platform"
        )
        self.assertEqual(own.env("AP_WORKSPACE_TTL"), "3")
        self.assertEqual(Settings.from_env({}).workspaces.ttl, 15)

    def test_secret_reads_the_mapping_it_is_given(self):
        self.setenv("AP_API_TOKEN", "from-process")

        self.assertEqual(secret("AP_API_TOKEN", env={"AP_API_TOKEN": "given"}), "given")
        self.assertEqual(secret("AP_API_TOKEN", env={}), "")

    def test_a_patched_setting_follows_the_environment_again_once_unpatched(self):
        fresh = Settings()
        self.setenv("AP_WORKSPACE_TTL", "7")

        with mock.patch.object(fresh, "workspaces", WorkspacesConfig(ttl=0)):
            self.assertEqual(fresh.workspaces.ttl, 0)

        self.setenv("AP_WORKSPACE_TTL", "8")

        self.assertEqual(fresh.workspaces.ttl, 8)

    def test_an_unknown_setting_is_an_attribute_error(self):
        with self.assertRaises(AttributeError):
            Settings().NOT_A_SETTING
