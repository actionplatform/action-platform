"""deploy/dokploy — unique service names and a template.b64 that matches its sources."""

import base64
import json
import re
import unittest
from pathlib import Path

DOKPLOY = Path(__file__).resolve().parents[2] / "deploy" / "dokploy"


class DokployTemplateTest(unittest.TestCase):
    def setUp(self):
        self.compose = (DOKPLOY / "docker-compose.yml").read_text()
        self.toml = (DOKPLOY / "template.toml").read_text()

    def test_every_service_has_a_prefixed_name(self):
        services = re.findall(
            r"(?m)^  ([a-z][a-z0-9-]*):$", self.compose.split("\nvolumes:")[0]
        )

        self.assertIn("ap-api", services)
        self.assertEqual([s for s in services if not s.startswith("ap-")], [])

    def test_hosts_point_at_the_prefixed_services(self):
        self.assertIn("AP_API: http://ap-api:7788", self.compose)
        self.assertIn("${AP_DB_HOST:-ap-postgres}", self.compose)
        self.assertNotRegex(self.compose, r"//(api|postgres)[:/]")
        self.assertIn('serviceName = "ap-web"', self.toml)

    def test_images_are_pinned_in_the_template(self):
        for key in ("AP_IMAGE_API", "AP_IMAGE_WORKER", "AP_IMAGE_WEB"):
            self.assertRegex(self.toml, rf'(?m)^{key} = "[^"]+:\d+\.\d+\.\d+"$')

    def test_template_b64_is_built_from_the_current_files(self):
        packed = json.loads(base64.b64decode((DOKPLOY / "template.b64").read_text()))

        self.assertEqual(packed["compose"], self.compose)
        self.assertEqual(packed["config"], self.toml)
        self.assertEqual(
            (DOKPLOY.parent / "docker-compose.dokploy.yml").read_text(), self.compose
        )
