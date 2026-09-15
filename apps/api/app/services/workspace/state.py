from dataclasses import asdict
from pathlib import Path

from action_platform.core.wiring import wired
from action_platform.core.flow import gitflow
from action_platform.core.flow.repository import Repository
from action_platform.core.release.release import STABLE_BRANCHES
from app.repositories.workspace.registry import Registry
from app.services.workspace.checkout import Workspaces


class GitStateService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _root(self, id: str) -> Path:
        return Workspaces(self.registry).checkout(id)[1]

    def gitflow(self, id: str) -> dict:
        report = wired.gitflow(self._root(id)).audit()
        data = asdict(report)
        data["ok"] = report.ok

        return data

    def commits(self, id: str, limit: int) -> list[dict]:
        out = Repository(self._root(id)).run(
            ["log", f"-{limit}", "--format=%h%x1f%s%x1f%an%x1f%ad", "--date=short"]
        )

        return [
            dict(zip(("sha", "subject", "author", "date"), line.split("\x1f")))
            for line in out.splitlines()
            if line
        ]

    def tags(self, id: str) -> list[str]:
        return list(reversed(Repository(self._root(id)).tags()))

    def releases(self, id: str) -> list[dict]:
        out = Repository(self._root(id)).run(
            [
                "for-each-ref",
                "--sort=-creatordate",
                "--format=%(refname:short)|%(creatordate:short)|%(*objectname:short)%(objectname:short)|%(subject)",
                "refs/tags",
            ]
        )
        rows = [line.split("|", 3) for line in out.splitlines() if line]
        releases = []

        for i, (tag, date, sha, subject) in enumerate(rows):
            version = tag.split("/")[-1].removeprefix("v")
            releases.append(
                {
                    "tag": tag,
                    "version": version,
                    "date": date,
                    "sha": sha[:7],
                    "subject": subject,
                    "prerelease": "-" in version,
                    "latest": i == 0,
                }
            )

        return releases

    def branches(self, id: str) -> list[dict]:
        out = Repository(self._root(id)).run(
            [
                "for-each-ref",
                "--sort=-committerdate",
                "--format=%(refname:short)|%(committerdate:short)|%(objectname:short)",
                "refs/remotes/origin",
            ]
        )
        rows = [line.rsplit("|", 2) for line in out.splitlines() if line]
        names = [
            (ref.removeprefix("origin/"), date, sha)
            for ref, date, sha in rows
            if ref != "origin/HEAD"
        ]

        return [
            {
                "name": name,
                "date": date,
                "sha": sha,
                "kind": gitflow.kind_of(name),
                "protected": name in gitflow.current().protected,
                "stable": name in STABLE_BRANCHES,
                "problem": gitflow.check_branch(name),
            }
            for name, date, sha in names
        ]
