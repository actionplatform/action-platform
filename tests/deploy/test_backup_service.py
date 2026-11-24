"""deploy compose files — the daily pg_dump service and its retention."""

import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"


class BackupServiceTest(unittest.TestCase):
    def test_plain_compose_has_an_opt_in_backup_profile_on_the_host(self):
        text = (DEPLOY / "docker-compose.yml").read_text()
        service = text.split("\n  backup:\n")[1].split("\n\n")[0]

        self.assertIn('profiles: ["backup"]', service)
        self.assertIn("${AP_BACKUP_DIR:-./backups}:/backups", service)
        self.assertIn("/run/secrets/postgres_password", service)

    def test_dokploy_backs_up_into_a_volume(self):
        text = (DEPLOY / "dokploy" / "docker-compose.yml").read_text()
        service = text.split("\n  ap-backup:\n")[1].split("\n\n")[0]

        self.assertNotIn("profiles", service)
        self.assertIn("PGHOST: ap-postgres", service)
        self.assertIn("- backups:/backups", service)
        self.assertIn("\n  backups:\n", text.split("\nvolumes:\n")[1] + "\n")

    def test_both_keep_the_configured_number_of_days(self):
        for path in (
            DEPLOY / "docker-compose.yml",
            DEPLOY / "dokploy" / "docker-compose.yml",
        ):
            text = path.read_text()

            self.assertIn("AP_BACKUP_KEEP_DAYS: ${AP_BACKUP_KEEP_DAYS:-7}", text, path)
            self.assertIn('-mtime +"$$AP_BACKUP_KEEP_DAYS" -delete', text, path)
            self.assertIn("image: postgres:16-alpine", text.split("backup:\n")[1], path)
