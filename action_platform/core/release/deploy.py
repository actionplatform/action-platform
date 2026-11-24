"""Deploy, rollback, diagnose, destroy against the [deploy] targets of one repository.

A deploy ships a release, never a working tree: it names a version (or takes the tag HEAD sits on), checks that tag out for the duration, and puts the repository back afterwards."""

from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Iterator
from typing import Callable

from action_platform.abc.deploy_target import DeployTarget
from action_platform.core.config import Config
from action_platform.core.context import Context, DeployResult, Diagnosis
from action_platform.core.exception import DeployError
from action_platform.core.flow.repository import Repository
from action_platform.core.targets import TargetSpec
from action_platform.core.wiring import Wiring, slot, wired
from action_platform.logging import logger


@slot("deployer")
class Deployer:
    wiring: Wiring | None = None

    def __init__(
        self,
        config: Config,
        repo: Repository | Path,
        identity: Callable[[str], str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.config = config
        self.repo = repo if isinstance(repo, Repository) else Repository(repo)
        self.identity = identity
        self.env = dict(env or {})

    def runnable(
        self, name: str | None = None, stage: str | None = None
    ) -> list[DeployTarget]:
        """The targets a deploy runs: the platform's own and the dispatched ones, those serving `stage` when a target lists stages, `name` alone when given; only those are built."""
        return self.config.runnable(name, stage)

    def observed(
        self, name: str | None = None, stage: str | None = None
    ) -> list[TargetSpec]:
        """The targets someone else deploys and the platform only records, filtered like `runnable`."""
        return [
            t
            for t in self.config.targets
            if t.observed
            and (name is None or t.name == name)
            and (stage is None or t.serves(stage))
        ]

    def targets(
        self, name: str | None = None, stage: str | None = None
    ) -> list[DeployTarget]:
        """The targets a deploy runs; refused when there are none, naming who deploys the observed ones that matched."""
        targets = self.runnable(name, stage)

        if targets:
            return targets

        observed = self.observed(name, stage)

        if observed:
            raise DeployError(
                "; ".join(
                    f"{t.name} is deployed by {t.run_by}; the platform records it, it does not run it"
                    for t in observed
                )
            )

        raise DeployError(missing_target(name, stage))

    def _context(self, dry_run: bool = False, stage: str | None = None) -> Context:
        ctx = (
            (self.wiring or wired)
            .releaser(self.config, self.repo)
            .context(dry_run=dry_run, stage=stage)
        )
        ctx.next_version = ctx.current_version
        ctx.identity = self.identity
        ctx.env = {**ctx.env, **self.env}

        return ctx

    def release_tag(self, version: str | None = None) -> tuple[str, str]:
        """The tag a deploy ships and its version: `v<version>` (or the tag itself when `version` names one), else the tag HEAD sits on. Anything else is refused — a deploy is always a release."""
        if version:
            candidates = [version, f"v{version.lstrip('v')}"]
            tag = next((c for c in candidates if self.repo.has_tag(c)), None)

            if tag is None:
                raise DeployError(
                    f"no release {version!r}: tags are {', '.join(self.repo.tags()[-5:]) or 'none'} — release first"
                )
        else:
            tag = self.repo.tag_at_head()

            if tag is None:
                raise DeployError(
                    "a deploy ships a release: pass the version to deploy, or check out a release tag"
                )

        found = re.search(r"v?(\d[^/]*)$", tag)

        return tag, found.group(1) if found else tag

    @contextmanager
    def at_release(self, tag: str) -> Iterator[None]:
        """The repository checked out at `tag` for the block, then back where it was."""
        before = self.repo.branch
        moved = self.repo.tag_at_head() != tag

        if moved:
            self.repo.checkout(tag)

        try:
            yield
        finally:
            if moved and before and before != "HEAD":
                self.repo.checkout(before)

    def deploy(
        self,
        target: str | None = None,
        dry_run: bool = False,
        stage: str | None = None,
        version: str | None = None,
    ) -> list[DeployResult]:
        ctx = self._context(dry_run=dry_run, stage=stage)
        ctx.criticality = self.config.scope(ctx.stage).criticality
        tag, shipped = self.release_tag(version)
        ctx.current_version = ctx.next_version = shipped
        ctx.tag = tag
        results: list[DeployResult] = []
        covered: set[str] = set()

        with self.at_release(tag):
            for t in self.targets(target, ctx.stage):
                if t.name in covered:
                    continue

                logger.info(
                    "deploy target=%s stage=%s version=%s tag=%s",
                    t.name,
                    ctx.stage,
                    shipped,
                    tag,
                )
                t.preflight(ctx)

                if dry_run:
                    results.append(
                        DeployResult(ok=True, target=t.name, version=shipped)
                    )
                    continue

                result = t.deploy(ctx)
                results.append(result)

                for spec in self.config.runs_with(t.name):
                    covered.add(spec.name)
                    results.extend(shared(result, spec, ctx.stage))

        return results

    def rollback(
        self,
        target: str | None = None,
        to_version: str | None = None,
        stage: str | None = None,
    ) -> None:
        ctx = self._context(stage=stage)

        for t in self.targets(target, ctx.stage):
            logger.info(
                "rollback target=%s stage=%s to=%s", t.name, ctx.stage, to_version
            )
            t.preflight(ctx)
            t.rollback(ctx, to_version)

    def diagnose(
        self, target: str | None = None, stage: str | None = None
    ) -> list[Diagnosis]:
        ctx = self._context(stage=stage)

        return [t.diagnose(ctx) for t in self.targets(target, ctx.stage)]

    def destroy(self, target: str | None = None, stage: str | None = None) -> None:
        ctx = self._context(stage=stage)

        for t in self.targets(target, ctx.stage):
            logger.info("delete target=%s stage=%s", t.name, ctx.stage)
            t.preflight(ctx)
            t.delete(ctx)


def shared(
    result: DeployResult, spec: TargetSpec, stage: str | None
) -> list[DeployResult]:
    """What one run did for another target it deploys too: the same outcome, on the stage being deployed when that target serves it, else on each of its own."""
    stages = (
        [stage]
        if not spec.stages or (stage and stage in spec.stages)
        else list(spec.stages)
    )

    return [replace(result, target=spec.name, stage=s) for s in stages]


def missing_target(name: str | None, stage: str | None) -> str:
    return (
        f"no deploy target configured (filter={name!r}, stage={stage!r}) — "
        "run `action-platform cloud set <cloud>`"
    )


def deploy(
    config: Config,
    target_name: str | None,
    repo_root: Path,
    dry_run: bool = False,
    stage: str | None = None,
    version: str | None = None,
) -> list[DeployResult]:
    return wired.deployer(config, repo_root).deploy(
        target_name, dry_run=dry_run, stage=stage, version=version
    )


def rollback(
    config: Config,
    target_name: str | None,
    repo_root: Path,
    to_version: str | None = None,
    stage: str | None = None,
) -> None:
    wired.deployer(config, repo_root).rollback(
        target_name, to_version=to_version, stage=stage
    )


def diagnose(
    config: Config, target_name: str | None, repo_root: Path, stage: str | None = None
) -> list[Diagnosis]:
    return wired.deployer(config, repo_root).diagnose(target_name, stage=stage)


def destroy(
    config: Config, target_name: str | None, repo_root: Path, stage: str | None = None
) -> None:
    wired.deployer(config, repo_root).destroy(target_name, stage=stage)
