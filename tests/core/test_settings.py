import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from unittest import skipUnless

from action_platform.settings import Settings, database_url_from_parts, secret
from tests.support import TempCase


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
            "import action_platform.main, action_platform.mcp.server\n"
            "from action_platform.settings import settings\n"
            "print(sorted(vars(settings)))"
        )

        self.assertEqual(out, "[]")


class LazySettingsTest(TempCase):
    def test_the_environment_is_read_on_first_use(self):
        fresh = Settings()
        self.setenv("AP_SENTRY_DSN", "https://key@example.com/1")

        self.assertEqual(fresh.SENTRY_DSN, "https://key@example.com/1")

    def test_an_unknown_setting_is_an_attribute_error(self):
        with self.assertRaises(AttributeError):
            Settings().NOT_A_SETTING
