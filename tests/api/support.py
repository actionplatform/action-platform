"""Base class for API tests: an app registry under a temporary AP_HOME and a TestClient over the built app."""

from __future__ import annotations

import unittest

from action_platform.settings import settings
from tests.support import TempCase, git, platform_repo

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ApiCase(TempCase):
    """`self.client` talks to a fresh API; `self.repo` / `self.url` are a platform project reachable as file://."""

    def setUp(self):
        super().setUp()
        from action_platform.api.main import build

        self.setenv("AP_HOME", str(self.tmp_path / "home"))
        self.patch(settings, "ALLOW_FILE_URLS", True)
        self.repo = platform_repo(self.tmp_path)
        self.url = self.repo.as_uri()
        self.client = TestClient(build())

    def add_app(self, on_main: bool = True) -> str:
        if on_main:
            git(self.repo, "checkout", "-q", "main")

        res = self.client.post("/api/apps", json={"url": self.url})
        assert res.status_code == 201, res.text

        return res.json()["id"]

    @property
    def workspaces(self):
        return self.tmp_path / "home" / "action-platform" / "workspaces"
