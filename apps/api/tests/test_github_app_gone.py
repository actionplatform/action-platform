"""A GitHub App deleted on GitHub: installing and creating it again forget the stored one."""

from __future__ import annotations

from unittest import mock

from action_platform.core.exception import ProviderError
from app.services.integrations.hosts import GithubProvider
from app.services.integrations.hosts.directory import IntegrationsDirectory
from tests.test_access import GateCase

ORIGIN = {"origin": "https://ap.example.com", "host": "ap.example.com"}
INSTALL = {"origin": "https://ap.example.com", "return_to": "/connect/git"}


class GithubAppGoneTest(GateCase):
    def store(self) -> None:
        with self.app.state.db.session() as s:
            IntegrationsDirectory(s, self.app.state.sealer).save_oauth_app(
                "github", "cid", "sec", None, "ap", app_id="1", private_key="pem"
            )

    def configured(self) -> bool:
        rows = self.client.get("/api/v1/oauth/apps", headers=self.h()).json()

        return rows[0]["configured"]

    def post(self, path: str, body: dict, exists):
        with mock.patch.object(GithubProvider, "app_exists", return_value=exists):
            return self.client.post(
                f"/api/v1/oauth/github/{path}", json=body, headers=self.h()
            )

    def test_install_of_a_deleted_app_clears_it(self):
        self.store()
        res = self.post("install", INSTALL, False)

        self.assertEqual(res.status_code, 409)
        self.assertIn("deleted on GitHub", res.json()["detail"])
        self.assertFalse(self.configured())

    def test_install_of_an_existing_app_returns_the_url(self):
        self.store()
        res = self.post("install", INSTALL, True)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            res.json()["url"].startswith(
                "https://github.com/apps/ap/installations/select_target?state="
            )
        )
        self.assertTrue(self.configured())

    def test_install_when_github_cannot_say_keeps_the_app(self):
        self.store()
        res = self.post("install", INSTALL, None)

        self.assertEqual(res.status_code, 200)
        self.assertTrue(self.configured())

    def test_manifest_of_a_deleted_app_clears_it_and_answers(self):
        self.store()
        res = self.post("manifest", ORIGIN, False)

        self.assertEqual(res.status_code, 200, res.text)
        self.assertTrue(res.json()["target"].startswith("https://github.com/"))
        self.assertFalse(self.configured())

    def test_manifest_of_an_existing_app_is_refused(self):
        self.store()

        self.assertEqual(self.post("manifest", ORIGIN, True).status_code, 409)
        self.assertTrue(self.configured())

    def test_manifest_when_github_cannot_say_is_refused(self):
        self.store()

        self.assertEqual(self.post("manifest", ORIGIN, None).status_code, 409)
        self.assertTrue(self.configured())


class AppExistsTest(GateCase):
    def answer(self, status: int):
        def get(url, headers=None):
            if status == 200:
                return {"slug": "ap"}
            if status == 0:
                raise ProviderError("cannot reach api.github.com: down")
            raise ProviderError(f"{status} from api.github.com")

        with mock.patch("app.core.shared.http.http.get_json", side_effect=get):
            return GithubProvider().app_exists("ap")

    def test_statuses(self):
        self.assertIs(self.answer(200), True)
        self.assertIs(self.answer(404), False)
        self.assertIsNone(self.answer(500))
        self.assertIsNone(self.answer(0))
