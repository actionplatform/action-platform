"""ReleaseStrategy ABC — how the next version is computed from the current one.

The core ships `semver`; a plugin adds another under the
`action_platform.release_strategy` entry-point group and `[release]
strategy = "<name>"` in platform.toml selects it. Everything after the number —
changelog, commit, tag, push, publish — stays in the core.
"""

from abc import ABC, abstractmethod


class ReleaseStrategy(ABC):
    """ReleaseStrategy"""

    name: str

    @abstractmethod
    def next(self, current: str, level: str, prerelease: bool, taken: list[str]) -> str:
        """The version after `current` for `level` (patch, minor, major or an explicit version). `taken` lists the tags already on the component, without its prefix (`v1.2.0`, `v1.3.0-rc.1`), so a pre-release can pick a free number."""

    def is_prerelease(self, version: str) -> bool:
        """Whether `version` is a pre-release; decides how the code host marks the release."""
        return "-" in version
