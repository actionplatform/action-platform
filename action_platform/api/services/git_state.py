from dataclasses import asdict
from pathlib import Path


from action_platform.api.repositories.registry import Registry
from action_platform.api.services.manifest import workspace_of
from action_platform.core.flow import git, gitflow


class GitStateService:
    def __init__(self, registry: Registry) -> None:
        self.registry = registry

    def _root(self, id: str) -> Path:
        return workspace_of(self.registry, id)[1]

    def gitflow(self, id: str) -> dict:
        report = gitflow.audit(self._root(id))
        data = asdict(report)
        data["ok"] = report.ok

        return data

    def commits(self, id: str, limit: int) -> list[dict]:
        out = git.run(
            ["log", f"-{limit}", "--format=%h%x1f%s%x1f%an%x1f%ad", "--date=short"],
            cwd=self._root(id),
        )

        return [
            dict(zip(("sha", "subject", "author", "date"), line.split("\x1f")))
            for line in out.splitlines()
            if line
        ]

    def tags(self, id: str) -> list[str]:
        return list(reversed(git.tags(cwd=self._root(id))))

    def releases(self, id: str) -> list[dict]:
        out = git.run(
            [
                "for-each-ref",
                "--sort=-creatordate",
                "--format=%(refname:short)|%(creatordate:short)|%(*objectname:short)%(objectname:short)|%(subject)",
                "refs/tags",
            ],
            cwd=self._root(id),
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
        out = git.run(
            [
                "for-each-ref",
                "--sort=-committerdate",
                "--format=%(refname:short)|%(committerdate:short)",
                "refs/remotes/origin",
            ],
            cwd=self._root(id),
        )
        rows = [line.rsplit("|", 1) for line in out.splitlines() if line]
        names = [
            (ref.removeprefix("origin/"), date)
            for ref, date in rows
            if ref != "origin/HEAD"
        ]

        return [
            {
                "name": name,
                "date": date,
                "kind": gitflow.kind_of(name),
                "protected": name in gitflow.PROTECTED,
                "problem": gitflow.check_branch(name),
            }
            for name, date in names
        ]
