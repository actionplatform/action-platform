"""action_platform.remote.credentials — the token file under AP_HOME, and environment overrides."""

from __future__ import annotations

from action_platform.remote import credentials
from tests.support import TempCase


class CredentialsTest(TempCase):
    def setUp(self):
        super().setUp()
        self.setenv("AP_HOME", str(self.tmp_path))
        self.delenv("AP_SERVER")
        self.delenv("AP_TOKEN")

    def test_roundtrip_with_private_file(self):
        self.assertIsNone(credentials.load())

        credentials.save(credentials.Credentials("https://p.example", "tok"))

        file = self.tmp_path / "action-platform" / "credentials.json"
        self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        self.assertEqual(
            credentials.load(), credentials.Credentials("https://p.example", "tok")
        )
        self.assertTrue(credentials.clear())
        self.assertIsNone(credentials.load())

    def test_environment_wins(self):
        self.setenv("AP_SERVER", "https://env.example")
        self.setenv("AP_TOKEN", "env-tok")

        self.assertEqual(
            credentials.load(),
            credentials.Credentials("https://env.example", "env-tok"),
        )
