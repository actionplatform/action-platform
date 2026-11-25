import unittest
from types import SimpleNamespace
from unittest import mock

from action_platform.core.flow import git
from app.schemas import ReleaseRequest
from app.schemas.common import SourceCredentials
from app.services.releases.service import ReleasesService


class ReleaseCredentialsTest(unittest.TestCase):
    def test_the_fresh_checkout_runs_with_the_source_host_credentials(self):
        seen = {}

        def tool(id, fresh=False):
            seen["fresh"] = fresh
            seen["env"] = dict(git.AUTH_ENV.get() or {})
            context = SimpleNamespace(
                current_version="1.0.0",
                next_version="1.0.1",
                changelog="",
                branch="main",
            )

            return SimpleNamespace(
                config=SimpleNamespace(source_host=None),
                repo_root="/nowhere",
                release=lambda **_: context,
            )

        service = ReleasesService(mock.Mock(), configs=mock.Mock())
        body = ReleaseRequest(
            dry_run=False,
            credentials=SourceCredentials(kind="github", token="t0ken"),
        )

        with mock.patch.object(service, "_tool", side_effect=tool):
            result = service.release("app", body)

        self.assertTrue(seen["fresh"])
        self.assertEqual(seen["env"].get("AP_GIT_TOKEN"), "t0ken")
        self.assertEqual(result["next"], "1.0.1")
