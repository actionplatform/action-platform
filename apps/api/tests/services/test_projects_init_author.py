"""app.services.projects.service.ProjectService.init_app — whose name a generated app carries."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any, cast

from app.repositories.base import DEFAULT_GIT_AUTHOR
from app.schemas import InitRequest
from app.services.projects.service import ProjectService


class Writes:
    db = None

    def __init__(self, author: tuple[str, str]) -> None:
        self.author = author

    def credentials_for(self, organization_id, host_id):
        return SimpleNamespace(as_dict=lambda: {"kind": "github", "token": "t"})

    def git_author_of(self, organization_id):
        return self.author

    def source_spec_by_name(self, organization_id, name):
        return None

    def create_app(self, project_id, registry_id, name, host_id):
        return SimpleNamespace(id="a1")


class Apps:
    registry = None
    configs = object()

    def __init__(self) -> None:
        self.requests: list[InitRequest] = []

    def init(self, request: InitRequest) -> dict:
        self.requests.append(request)

        return {"id": "r1", "name": "demo", "pushed": False}


class InitAuthorTest(unittest.TestCase):
    def author(self, identity: tuple[str, str], given: str | None = None) -> str:
        apps = Apps()
        writes: Any = Writes(identity)
        service = ProjectService(writes, cast(Any, apps))
        org: Any = SimpleNamespace(id="o1")
        project: Any = SimpleNamespace(id="p1")
        service.init_app(
            org,
            project,
            InitRequest(type="web", name="Demo", author=given),
            "h1",
            None,
        )

        return apps.requests[0].author or ""

    def test_the_organization_s_commit_identity_authors_it(self):
        self.assertEqual(self.author(("Acme Inc", "dev@acme.example")), "Acme Inc")

    def test_the_platform_s_default_identity_authors_nothing(self):
        self.assertEqual(self.author(DEFAULT_GIT_AUTHOR), "")

    def test_the_caller_s_author_wins(self):
        self.assertEqual(self.author(("Acme Inc", "dev@acme.example"), "Bo"), "Bo")
