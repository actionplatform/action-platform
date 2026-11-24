"""Bulk adoption: a plan per app, one install pull request per repository, reruns that open nothing twice, and the state of each app."""

from __future__ import annotations

import subprocess
from pathlib import Path

from action_platform.core.context import PRRef
from action_platform.core.flow.workflow import GitFlow
from action_platform.testing.fixtures import git, template_repo
from app.core.db.models import RegistryEntry
from tests.test_access import GateCase

ARCHIVED = """#!/bin/sh
echo "This repository was archived so it is read-only." >&2
exit 1
"""


def remote(root: Path, name: str, files: dict[str, str], tag: str = "") -> Path:
    bare = root / "remotes" / f"{name}.git"
    git(root, "init", "-q", "--bare", "-b", "main", str(bare))
    work = root / "work" / name
    work.mkdir(parents=True)

    for rel, text in files.items():
        (work / rel).write_text(text)

    git(work, "init", "-q", "-b", "main")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "chore: init")

    if tag:
        git(work, "tag", tag)

    git(work, "remote", "add", "origin", bare.as_uri())
    git(work, "push", "-q", "--tags", "origin", "main")

    return bare


class AdoptionTest(GateCase):
    def setUp(self):
        super().setUp()
        from app.core.db.models import App, RegistryEntry

        self.setenv(
            "ACTION_PLATFORM_TEMPLATES", str(template_repo(self.tmp_path / "official"))
        )
        self.project = self.client.post(
            "/api/v1/projects", json={"name": "Storefront"}, headers=self.h()
        ).json()["id"]
        self.remotes = {
            "shop": remote(
                self.tmp_path,
                "shop",
                {"pyproject.toml": '[project]\nname = "shop"\n'},
                tag="v1.4.0",
            ),
            "docs": remote(self.tmp_path, "docs", {"README.md": "docs\n"}),
            "done": remote(
                self.tmp_path,
                "done",
                {"platform.toml": '[project]\nname = "done"\n', "app.py": ""},
            ),
            "vault": remote(self.tmp_path, "vault", {"main.py": "print(1)\n"}),
        }
        hook = self.remotes["vault"] / "hooks" / "pre-receive"
        hook.write_text(ARCHIVED)
        hook.chmod(0o755)

        with self.app.state.db.session() as s:
            for name, bare in self.remotes.items():
                s.add(
                    RegistryEntry(
                        id=f"r-{name}",
                        name=name,
                        url=bare.as_uri(),
                        default_branch="main",
                    )
                )
                s.add(
                    App(
                        id=f"a-{name}",
                        project_id=self.project,
                        registry_id=f"r-{name}",
                        name=name,
                    )
                )

        self.opened: list[str] = []

        def open_pr(flow, base=None, title=None, body=None, draft=False, config=None):
            flow.repo.push_upstream(flow.repo.branch)
            self.opened.append(flow.repo.branch)
            number = len(self.opened)

            return PRRef(number=number, url=f"https://code.example/pr/{number}")

        self.patch(GitFlow, "open_pr", open_pr)

    def install(self, **body) -> dict:
        from app.services.jobs.worker import Worker

        queued = self.client.post(
            f"/api/v1/projects/{self.project}/install", json=body, headers=self.h()
        )
        self.assertEqual(queued.status_code, 202, queued.text)
        Worker(self.app.state.db, self.app.state.secrets, "test").run(once=True)
        done = self.client.get(
            f"/api/v1/jobs/{queued.json()['job']}", headers=self.h()
        ).json()
        self.assertEqual(done["status"], "done", done)

        return {r["name"]: r for r in done["result"]["apps"]} | {
            "_summary": done["result"]
        }

    def states(self) -> dict:
        res = self.client.get(
            f"/api/v1/projects/{self.project}/adoption", headers=self.h()
        )
        self.assertEqual(res.status_code, 200, res.text)

        return {r["name"]: r for r in res.json()}

    def branches(self, name: str) -> str:
        return subprocess.run(
            ["git", "ls-remote", "--heads", str(self.remotes[name])],
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def test_every_app_is_unchecked_before_a_run(self):
        self.assertEqual(
            {n: r["state"] for n, r in self.states().items()},
            {
                "shop": "unchecked",
                "docs": "unchecked",
                "done": "unchecked",
                "vault": "unchecked",
            },
        )

    def test_a_dry_run_plans_each_app_and_pushes_nothing(self):
        result = self.install()

        shop = result["shop"]
        self.assertEqual(shop["state"], "missing")
        self.assertIn("platform.toml", shop["plan"]["created"])
        self.assertIn(".code_quality/", shop["plan"]["created"])
        self.assertEqual(shop["plan"]["language"], "python")
        self.assertEqual(shop["plan"]["ci"], "github")
        self.assertEqual(
            (shop["plan"]["version"], shop["plan"]["version_source"]),
            ("1.4.0", "tag v1.4.0"),
        )
        self.assertEqual(shop["plan"]["branch"], "chore/platform")
        self.assertEqual(result["docs"]["state"], "failed")
        self.assertTrue(result["docs"]["reason"].startswith("unknown language"))
        self.assertEqual(
            (result["done"]["state"], result["done"]["skipped"]), ("installed", True)
        )
        self.assertTrue(result["_summary"]["dry_run"])
        self.assertEqual(self.opened, [])
        self.assertNotIn("chore/platform", self.branches("shop"))

        states = self.states()
        self.assertEqual(
            {n: r["state"] for n, r in states.items()},
            {
                "shop": "missing",
                "docs": "failed",
                "done": "installed",
                "vault": "missing",
            },
        )
        self.assertEqual(states["shop"]["version"], "1.4.0")

    def test_confirm_opens_one_pull_request_per_repository_and_a_rerun_opens_none(self):
        result = self.install(dry_run=False)

        self.assertEqual(result["shop"]["state"], "pr_open")
        self.assertEqual(
            result["shop"]["pull_request"]["url"], "https://code.example/pr/1"
        )
        self.assertIn("chore/platform", self.branches("shop"))
        shown = subprocess.run(
            ["git", "show", "chore/platform:platform.toml"],
            cwd=self.remotes["shop"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        self.assertIn('name = "shop"', shown)
        self.assertEqual(result["vault"]["state"], "failed")
        self.assertTrue(result["vault"]["reason"].startswith("archived"))
        self.assertEqual(result["docs"]["state"], "failed")
        self.assertEqual(result["done"]["state"], "installed")
        self.assertEqual(result["_summary"]["opened"], 1)
        self.assertEqual(result["_summary"]["failed"], 2)

        with self.app.state.db.session() as s:
            self.assertEqual(s.get(RegistryEntry, "r-shop").branch, "chore/platform")
            self.assertEqual(s.get(RegistryEntry, "r-vault").branch, "")

        states = self.states()
        self.assertEqual(states["shop"]["state"], "pr_open")
        self.assertEqual(states["shop"]["pull_request"]["number"], 1)
        self.assertEqual(
            states["vault"]["reason"], "archived: the repository is read-only"
        )

        again = self.install(dry_run=False)

        self.assertEqual(
            (again["shop"]["state"], again["shop"]["skipped"]), ("pr_open", True)
        )
        self.assertEqual(again["shop"]["pull_request"]["number"], 1)
        self.assertEqual(again["_summary"]["opened"], 0)
        self.assertEqual(self.opened, ["chore/platform"])
        self.assertEqual(self.states()["shop"]["language"], "python")

    def test_a_merged_install_pull_request_reads_as_installed(self):
        from datetime import datetime

        from app.core.db.models import PullRequest

        self.install(dry_run=False, apps=["a-shop"])

        with self.app.state.db.session() as s:
            s.add(
                PullRequest(
                    id="pr1",
                    app_id="a-shop",
                    number=1,
                    title="chore(platform): install the platform",
                    url="https://code.example/pr/1",
                    head="chore/platform",
                    base="main",
                    state="merged",
                    draft=False,
                    created_at=datetime(2026, 1, 1),
                    updated_at=datetime(2026, 1, 2),
                    source="github",
                )
            )

        self.assertEqual(self.states()["shop"]["state"], "installed")

    def test_only_the_apps_named_run(self):
        result = self.install(apps=["a-docs"])

        self.assertEqual([k for k in result if not k.startswith("_")], ["docs"])
        self.assertEqual(self.states()["shop"]["state"], "unchecked")

    def test_refusals(self):
        from app.core.db.models import Member

        url = f"/api/v1/projects/{self.project}/install"
        self.assertEqual(
            self.client.post(
                url, json={"apps": ["nope"]}, headers=self.h()
            ).status_code,
            404,
        )
        self.assertEqual(
            self.client.post(url, json={"ci": "travis"}, headers=self.h()).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(url, json={"code": "a b"}, headers=self.h()).status_code,
            400,
        )
        self.assertEqual(
            self.client.post(
                "/api/v1/projects/nope/install", json={}, headers=self.h()
            ).status_code,
            404,
        )

        with self.app.state.db.session() as s:
            s.query(Member).update({"role": "developer"})

        self.assertEqual(
            self.client.post(url, json={}, headers=self.h()).status_code, 403
        )
        self.assertEqual(
            self.client.get(
                f"/api/v1/projects/{self.project}/adoption", headers=self.h()
            ).status_code,
            200,
        )


class ReasonTest(GateCase):
    def test_reasons_name_archived_and_permission_refusals(self):
        from app.services.projects.adoption.install import reason_of

        denied = subprocess.CalledProcessError(
            128,
            ["git", "push"],
            "",
            "remote: Permission to acme/shop.git denied to bot.\nfatal: unable to access\n",
        )

        self.assertEqual(
            reason_of(denied),
            "no permission: remote: Permission to acme/shop.git denied to bot.",
        )
        self.assertEqual(reason_of(ValueError("boom\nmore")), "boom")
