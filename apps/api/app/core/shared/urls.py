"""What a git URL says about the repository behind it."""

import re
from typing import Optional

REPO_IN_URL = re.compile(r"[:/]([^/:]+/[^/]+?)(?:\.git)?$")
PATH_IN_URL = re.compile(
    r"^(?:[a-z][a-z0-9+.-]*://[^/]+/|[^@/]+@[^:/]+:)(.+?)(?:\.git)?/?$"
)


class GitUrl:
    def __init__(self, url: Optional[str]) -> None:
        self.url = url or ""

    @property
    def repo(self) -> Optional[str]:
        """owner/name, whatever the scheme."""
        match = REPO_IN_URL.search(self.url)

        return match.group(1) if match else None

    @property
    def path(self) -> Optional[str]:
        """Everything after the host: owner/name, or group/subgroup/name on GitLab."""
        match = PATH_IN_URL.match(self.url)

        return match.group(1) if match else self.repo

    @property
    def kind(self) -> Optional[str]:
        """Which code host serves it: github, gitlab, bitbucket, or None."""
        if "github.com" in self.url:
            return "github"

        if "gitlab" in self.url:
            return "gitlab"

        if "bitbucket.org" in self.url:
            return "bitbucket"

        return None
