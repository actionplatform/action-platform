import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
FILES = {
    DEPLOY / "docker-compose.yml": "worker",
    DEPLOY / "docker-compose.dokploy.yml": "ap-worker",
    DEPLOY / "dokploy" / "docker-compose.yml": "ap-worker",
}


class WorkerMailTest(unittest.TestCase):
    def test_the_light_worker_can_send_the_invitations_an_import_creates(self):
        for path, name in FILES.items():
            body = path.read_text().split(f"\n  {name}:\n")[1].split("\n\n")[0]

            for variable in ("AP_SMTP_HOST", "AP_SMTP_FROM", "AP_GOOGLE_CLIENT_ID"):
                self.assertIn(f"{variable}: ${{{variable}:-}}", body, path)
