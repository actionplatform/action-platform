"""Base class for API tests: an app registry under a temporary AP_HOME and a TestClient over the built app."""

from __future__ import annotations

import unittest

from action_platform.settings import settings
from action_platform.testing.fixtures import TempCase, git, platform_repo

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ApiCase(TempCase):
    """`self.client` talks to a fresh API; `self.repo` / `self.url` are a platform project reachable as file://."""

    def setUp(self):
        super().setUp()
        from app.api.app import build

        self.setenv("AP_HOME", str(self.tmp_path / "home"))
        self.patch(
            settings,
            "WORKSPACES",
            self.tmp_path / "home" / "action-platform" / "workspaces",
        )
        self.patch(settings, "WORKSPACE_TTL", 0)
        self.patch(settings, "ALLOW_UNAUTHENTICATED_API", True)
        self.patch(settings, "ALLOW_FILE_URLS", True)
        self.repo = platform_repo(self.tmp_path)
        self.url = self.repo.as_uri()
        self.client = TestClient(
            build(database_url=f"sqlite:///{self.tmp_path / 'api.db'}")
        )

    def add_app(self, on_main: bool = True) -> str:
        if on_main:
            git(self.repo, "checkout", "-q", "main")

        res = self.client.post("/api/apps", json={"url": self.url})
        assert res.status_code == 201, res.text

        return res.json()["id"]

    def fake_push(self):
        """Make `init` push into a bare repository under the temp dir instead of a code host."""
        from app.services.apps import generate as apps
        from action_platform.core.flow.repository import Repository

        remotes = self.tmp_path / "remotes"
        remotes.mkdir(exist_ok=True)

        def push(path, private=False, credentials=None):
            remote = remotes / f"{path.name}.git"
            git(remotes, "init", "-q", "--bare", str(remote))
            repo = Repository.init(path, branch="main")
            repo.add_all()
            repo.commit("chore: bootstrap project from action-platform")
            repo.add_remote(remote.as_uri())
            repo.push_upstream("main")

            return remote.as_uri()

        self.patch(apps, "push_project", push)

    @property
    def workspaces(self):
        return self.tmp_path / "home" / "action-platform" / "workspaces"
