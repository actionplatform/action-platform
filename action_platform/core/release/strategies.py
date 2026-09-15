"""The release strategies and changelog renderers the core ships, and how `[release]` in platform.toml picks one — built-in or from a plugin."""

from __future__ import annotations

from action_platform.abc.changelog_renderer import ChangelogRenderer
from action_platform.abc.release_strategy import ReleaseStrategy
from action_platform.core import module
from action_platform.core.exception import ConfigError
from action_platform.core.release import changelog
from action_platform.core.release.versioning import Version


class Semver(ReleaseStrategy):
    """Stable: plain bump. Pre-release: bump the stable base (or keep it when already on an rc) and add -rc.N."""

    name = "semver"

    def next(self, current: str, level: str, prerelease: bool, taken: list[str]) -> str:
        version = Version.parse(current)
        base = version.stable

        if not prerelease:
            return str(base.bump(level))

        if Version.is_valid(level):
            target = Version.parse(level).stable
        elif version.is_prerelease:
            target = base
        else:
            target = base.bump(level)

        return str(target.next_rc(taken))

    def is_prerelease(self, version: str) -> bool:
        return Version.parse(version).is_prerelease


class Conventional(ChangelogRenderer):
    """Sections by Conventional Commit type, breaking changes first."""

    name = "conventional"

    def render(self, version: str, commits: list[str]) -> str:
        return changelog.render(version, commits)


BUILTIN_STRATEGIES: dict[str, type[ReleaseStrategy]] = {"semver": Semver}
BUILTIN_RENDERERS: dict[str, type[ChangelogRenderer]] = {"conventional": Conventional}


def strategy(name: str) -> ReleaseStrategy:
    found = {**BUILTIN_STRATEGIES, **module.load_release_strategies()}

    if name not in found:
        raise ConfigError(
            f"unknown release strategy {name!r} (available: {', '.join(sorted(found))})"
        )

    return found[name]()


def renderer(name: str) -> ChangelogRenderer:
    found = {**BUILTIN_RENDERERS, **module.load_changelog_renderers()}

    if name not in found:
        raise ConfigError(
            f"unknown changelog renderer {name!r} (available: {', '.join(sorted(found))})"
        )

    return found[name]()
