"""Base class for API tests: an app registry under a temporary AP_HOME and a TestClient over the built app."""

from __future__ import annotations

import unittest
from unittest import mock

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.exception import ProviderError
from action_platform.core.flow.repository import Repository
from action_platform.core.scaffold.scaffolder import Scaffolder
from action_platform.testing.fixtures import TempCase, git, platform_repo

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


class ServerRunner(CIRunner):
    """The runner a CI server's plugin registers, standing in for it: built from the CI host's url and credentials, answering what a test patches on it."""

    name = "jenkins"

    def __init__(self, base_url: str, token=None, username=None) -> None:
        if not base_url:
            raise ProviderError("jenkins needs a base_url")

        self.base_url = base_url.rstrip("/")
        self.token = token
        self.username = username

    def test(self) -> None:
        return None

    def runs(self, job: str, limit: int = 50):
        return []


def plug_ci_server(case: unittest.TestCase) -> None:
    patch = mock.patch(
        "action_platform.core.module.load_ci_runners",
        return_value={ServerRunner.name: ServerRunner},
    )
    patch.start()
    case.addCleanup(patch.stop)


@unittest.skipUnless(TestClient, "fastapi is not installed")
class ApiCase(TempCase):
    """`self.client` talks to a fresh API; `self.repo` / `self.url` are a platform project reachable as file://."""

    def setUp(self):
        super().setUp()
        from app.api.app import build

        self.setenv("AP_HOME", str(self.tmp_path / "home"))
        self.setenv(
            "AP_WORKSPACES",
            str(self.tmp_path / "home" / "action-platform" / "workspaces"),
        )
        self.setenv("AP_WORKSPACE_TTL", "0")
        self.setenv("AP_ALLOW_UNAUTHENTICATED", "1")
        self.setenv("AP_ALLOW_FILE_URLS", "1")
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
        remotes = self.tmp_path / "remotes"
        remotes.mkdir(exist_ok=True)
        self.pushed_private: list[bool] = []

        def push(path, private=False, branch="main", credentials=None):
            self.pushed_private.append(private)
            remote = remotes / f"{path.name}.git"
            git(remotes, "init", "-q", "--bare", str(remote))
            repo = Repository.init(path, branch="main")
            repo.add_all()
            repo.commit("chore: bootstrap project from action-platform")
            repo.add_remote(remote.as_uri())
            repo.push_upstream("main")

            return remote.as_uri()

        self.patch(Scaffolder, "push", staticmethod(push))

    @property
    def workspaces(self):
        return self.tmp_path / "home" / "action-platform" / "workspaces"
