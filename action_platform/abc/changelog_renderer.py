"""ChangelogRenderer ABC — the entry a release adds to CHANGELOG.md, from the commits since the last tag.

The core ships `conventional`; a plugin adds another under the
`action_platform.changelog` entry-point group and `[release] changelog =
"<name>"` selects it.
"""

from abc import ABC, abstractmethod


class ChangelogRenderer(ABC):
    """ChangelogRenderer"""

    name: str

    @abstractmethod
    def render(self, version: str, commits: list[str]) -> str:
        """Markdown for one release; the core prepends it under the file header."""
