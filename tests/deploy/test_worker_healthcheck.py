"""deploy compose files — each worker reports its heartbeat as its healthcheck."""

import unittest
from pathlib import Path

DEPLOY = Path(__file__).resolve().parents[2] / "deploy"
FILES = {
    DEPLOY / "docker-compose.yml": {"worker": "worker", "worker-deploy": "deploy"},
    DEPLOY / "dokploy" / "docker-compose.yml": {
        "ap-worker": "worker",
        "ap-worker-deploy": "deploy",
    },
}


def service(text: str, name: str) -> str:
    return text.split(f"\n  {name}:\n")[1].split("\n\n")[0]


class WorkerHealthcheckTest(unittest.TestCase):
    def test_each_worker_checks_its_own_name(self):
        for path, workers in FILES.items():
            text = path.read_text()

            for name, worker in workers.items():
                body = service(text, name)

                self.assertIn(
                    f'test: ["CMD", "action-platform-api", "worker", "--check", "--name", "{worker}"]',
                    body,
                    (path, name),
                )
                self.assertIn(f'"--name", "{worker}"]', body, (path, name))

    def test_the_light_worker_takes_the_install_kind(self):
        for path, workers in FILES.items():
            light = next(iter(workers))

            self.assertIn(",install", service(path.read_text(), light), path)
