"""The remote client and the MCP answer models stay level with the API's OpenAPI document: every path the client calls exists, every model names only fields the API sends."""

from __future__ import annotations

import inspect
import re
import unittest

from action_platform.remote import client as remote_client
from action_platform.remote import schemas
from action_platform.testing.fixtures import TempCase

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

CALL = re.compile(r'self\._call\(\s*"(GET|POST|PUT|DELETE|PATCH)",\s*f?"([^"]+)"', re.S)
PARAM = re.compile(r"\{[^}]+\}")

SHARED = {
    "AppDetail": "AppDetail",
    "AppEntry": "AppEntry",
    "AppRow": "AppRow",
    "BranchRow": "Branch",
    "BranchStarted": "BranchResult",
    "Commit": "Commit",
    "Deployments": "Deployments",
    "DeploymentRow": "DeploymentRow",
    "DeployResult": "DeployResult",
    "DeployTargetRow": "TargetRow",
    "Diagnosis": "Diagnosis",
    "GitflowReport": "GitflowReport",
    "Job": "JobOut",
    "JobLogs": "JobLogsOut",
    "LogLine": "LogLine",
    "Me": "Me",
    "MemberRow": "MemberRow",
    "OrganizationRow": "OrganizationRow",
    "ProjectRow": "ProjectRow",
    "PullRequestPlan": "PullRequestProposal",
    "ReleasePreview": "ReleasePreview",
    "ReleaseRow": "Release",
    "ScopeRow": "ScopeRow",
    "Scopes": "Scopes",
    "TeamRow": "TeamRow",
    "Version": "Version",
}


@unittest.skipUnless(TestClient, "fastapi is not installed")
class RemoteContractTest(TempCase):
    maxDiff = None

    def setUp(self):
        super().setUp()
        from app.api.app import build

        self.setenv("AP_HOME", str(self.tmp_path / "home"))
        self.spec = build(
            token="shared",
            database_url=f"sqlite:///{self.tmp_path / 'c.db'}",
            auth_secret="s3cret",
            public_url="https://ap.example.com",
        ).openapi()

    def _templates(self) -> set[str]:
        return {
            PARAM.sub("{}", path.removeprefix("/api/v1").removeprefix("/api"))
            for path in self.spec["paths"]
        }

    def test_every_remote_path_exists(self):
        source = inspect.getsource(remote_client)
        known = self._templates()
        missing = []

        for method, path in CALL.findall(source):
            template = PARAM.sub("{}", "/" + path.split("?")[0].lstrip("/"))

            if template not in known:
                missing.append(f"{method} {path}")

        self.assertEqual(
            missing, [], f"remote.client calls paths the API does not serve: {missing}"
        )

    def test_shared_models_name_only_fields_the_api_sends(self):
        components = self.spec["components"]["schemas"]
        problems = []

        for name, api_name in sorted(SHARED.items()):
            model = getattr(schemas, name, None)
            api = components.get(api_name)

            if model is None or api is None:
                problems.append(
                    f"{name}: {'model' if model is None else 'API schema'} missing"
                )
                continue

            extra = set(model.model_fields) - set(api.get("properties", {}))

            if extra and not model.model_config.get("extra") == "allow":
                problems.append(f"{name}: fields the API never sends: {sorted(extra)}")

            for required in api.get("required", []):
                if required not in model.model_fields:
                    problems.append(
                        f"{name}: API requires {required!r}, model lacks it"
                    )

        self.assertEqual(problems, [])
