"""Whether a release can reach a stage, answered before anyone deploys it.

Static checks look at the repository at the release tag: targets declared, tag well-formed, manifests at the tag's version, lockfiles beside their manifests. Target checks are what each DeployTarget can verify without building or changing anything — credentials, permissions, the destination's state. Neither builds; a green readiness says nothing about compiling."""

from __future__ import annotations

import re
from pathlib import Path

from action_platform.abc.deploy_target import DeployTarget
from action_platform.core.config import Config
from action_platform.core.context import Check, Context
from action_platform.core.exception import ActionPlatformError
from action_platform.core.release.versioning import VERSION_PATTERNS
from action_platform.core.scopes import ScopeSpec, shape_check, shape_of
from action_platform.core.targets import VERSION
from action_platform.core.wiring import slot, wired
from action_platform.logging import logger

LOCKFILES = {
    "pyproject.toml": ("uv.lock", "poetry.lock", "pdm.lock", "requirements.txt"),
    "package.json": ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb"),
    "Gemfile": ("Gemfile.lock",),
    "Cargo.toml": ("Cargo.lock",),
    "composer.json": ("composer.lock",),
    "go.mod": ("go.sum",),
}


@slot("readiness")
class Readiness:
    def __init__(self, config: Config, repo_root: Path, deployer) -> None:
        self.config = config
        self.root = Path(repo_root)
        self.deployer = deployer

    def check(
        self,
        stage: str,
        version: str | None = None,
        target: str | None = None,
        shape: str | None = None,
    ) -> list[Check]:
        checks: list[Check] = []
        scope = self._scope(stage)
        checks.append(self._stage(stage, scope))

        try:
            tag, shipped = self.deployer.release_tag(version)
        except ActionPlatformError as e:
            checks.append(
                Check(
                    "release.tag",
                    False,
                    str(e),
                    level="static",
                    fix="release first, then check readiness of that release",
                )
            )

            return checks

        checks.append(self._tag(tag))

        if scope is not None:
            checks.append(shape_check(scope, shipped, shape or shape_of(shipped)))

        try:
            targets = self.deployer.targets(target)
        except ActionPlatformError as e:
            checks.append(
                Check(
                    "deploy.targets",
                    False,
                    str(e),
                    level="static",
                    fix="declare a target under [deploy] in platform.toml",
                )
            )

            return checks

        checks.append(
            Check(
                "deploy.targets",
                True,
                ", ".join(t.name for t in targets),
                level="static",
            )
        )

        with self.deployer.at_release(tag):
            checks.extend(self._manifests(shipped))
            checks.extend(self._lockfiles())
            ctx = self.deployer._context(stage=stage)
            ctx.current_version = ctx.next_version = shipped

            for t in targets:
                checks.extend(self._target(t, ctx))

        return checks

    def _scope(self, stage: str) -> ScopeSpec | None:
        try:
            return next((s for s in self.config.scopes if s.name == stage), None)
        except ActionPlatformError:
            return None

    def _stage(self, stage: str, scope: ScopeSpec | None) -> Check:
        if scope is not None:
            return Check(
                "deploy.stage",
                True,
                f"{scope.name} · {scope.kind} · {scope.criticality}",
                level="static",
            )

        names = [s.name for s in self._scopes()]

        return Check(
            "deploy.stage",
            False,
            f"no scope {stage!r}"
            + (
                f" (scopes: {', '.join(names)})" if names else "; the app has no scopes"
            ),
            level="static",
            fix="create the scope first — no scope, no deploy",
        )

    def _scopes(self) -> list[ScopeSpec]:
        try:
            return self.config.scopes
        except ActionPlatformError:
            return []

    def _tag(self, tag: str) -> Check:
        ok = VERSION.match(tag) is not None

        return Check(
            "release.tag",
            ok,
            tag if ok else f"{tag!r} is not <component/>v<major.minor.patch>",
            level="static",
            fix=None if ok else "tag releases as v1.2.3 or <component>/v1.2.3",
        )

    def _manifests(self, version: str) -> list[Check]:
        checks: list[Check] = []

        for name, pattern in VERSION_PATTERNS.items():
            path = self.root / name

            if not path.exists():
                continue

            found = pattern.search(path.read_text(errors="replace"))
            declared = _between(found) if found else None

            if declared is None:
                continue

            ok = declared == version

            checks.append(
                Check(
                    f"manifest.{name}",
                    ok,
                    f"{name} declares {declared}"
                    + ("" if ok else f", the release is {version}"),
                    level="static",
                    fix=None
                    if ok
                    else f"set version = {version} in {name} and re-tag, or let the platform cut the release",
                )
            )

        return checks

    def _lockfiles(self) -> list[Check]:
        checks: list[Check] = []

        for manifest, locks in LOCKFILES.items():
            if not (self.root / manifest).exists():
                continue

            present = [lock for lock in locks if (self.root / lock).exists()]
            checks.append(
                Check(
                    f"lockfile.{manifest}",
                    bool(present),
                    present[0] if present else f"{manifest} has no lockfile beside it",
                    level="static",
                    severity="warning",
                    fix=None
                    if present
                    else f"commit one of {', '.join(locks)} so the build resolves the same versions everywhere",
                )
            )

        return checks

    def _target(self, target: DeployTarget, ctx: Context) -> list[Check]:
        try:
            found = target.readiness(ctx)
        except ActionPlatformError as e:
            return [
                Check(
                    "target.readiness",
                    False,
                    str(e),
                    level="target",
                    target=target.name,
                )
            ]
        except Exception as e:
            logger.warning("readiness of %s failed", target.name, exc_info=True)

            return [
                Check(
                    "target.readiness",
                    False,
                    f"{type(e).__name__}: {e}",
                    level="target",
                    target=target.name,
                )
            ]

        for check in found:
            check.target = check.target or target.name
            check.level = check.level or "target"

        return found


def _between(found: re.Match) -> str:
    return found.group(0)[len(found.group(1)) : -len(found.group(2))]


def readiness(
    config: Config,
    repo_root: Path,
    stage: str,
    version: str | None = None,
    target: str | None = None,
) -> list[Check]:
    return wired.readiness(config, repo_root, wired.deployer(config, repo_root)).check(
        stage, version=version, target=target
    )
