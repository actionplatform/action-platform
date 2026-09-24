"""Local tags: listing, finding the one HEAD sits on or descends from, creating and deleting."""

from __future__ import annotations

from action_platform.core.flow.repo.runner import GitCommands


NO_TAG = ("No names found", "No tags can describe", "no tag exactly matches")


class Tags(GitCommands):
    def tags(self) -> list[str]:
        return [
            t for t in self.run(["tag", "--list", "--sort=v:refname"]).split("\n") if t
        ]

    def has_tag(self, glob: str) -> bool:
        return bool(self.run(["tag", "--list", glob]))

    def tag_at_head(self, match: str | None = None) -> str | None:
        """The tag HEAD sits on exactly, None when it sits on none."""
        args = ["describe", "--tags", "--exact-match"]

        if match:
            args += ["--match", match]

        return self.lookup(args, markers=NO_TAG) or None

    def latest_tag(self, match: str | None = None) -> str | None:
        args = ["describe", "--tags", "--abbrev=0"]

        if match:
            args += ["--match", match]

        return self.lookup(args, markers=NO_TAG) or None

    def tag(self, name: str, message: str | None = None) -> None:
        self.run(["tag", "-a", name, "-m", message or name])

    def delete_tag(self, name: str) -> None:
        self.run(["tag", "-d", name])
