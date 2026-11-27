"""Deploy targets as platform.toml declares them: where a version goes and who puts it there.

    [deploy]
    target = "aws/lambda"          # one target, run by the platform (short form)
    region = "us-east-1"

    [[deploy.targets]]
    name = "pypi"
    kind = "pypi"
    run_by = "github_actions"      # platform | github_actions | gitlab_ci | bitbucket_pipelines | <a CI server> | manual
    workflow = "python-publish-pypi.yml"
    package = "action-platform"

The platform executes `run_by = "platform"` targets itself and dispatches the
CI-run ones (`github_actions`, `gitlab_ci`, `bitbucket_pipelines`, and a CI
server a plugin brings, named by its runner, with `observe = false`): it starts
the workflow or job on the release and follows the run. `manual` targets, CI
servers by default, and CI-run ones with `observe = true` are observed — their
runs become deployment records and are verified, a platform deploy never runs
them.
`stages` limits a target to some scopes. An observed run names its release by
the tag it built or, with `version_parameter`, by a build parameter; its scope
comes from `stage_parameter`, else the target's only stage. A dispatched workflow receives the
registry the kind pairs with the scope's criticality — a `test` scope publishes
to TestPyPI or the npm `next` tag — unless the target fixes one with `registry`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from action_platform.core.exception import ConfigError

EMBEDDED_EXECUTORS = ("github_actions", "gitlab_ci", "bitbucket_pipelines")
EXECUTORS = ("platform", *EMBEDDED_EXECUTORS, "manual")
SERVER_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")
RESERVED = {"name", "kind", "run_by", "stages", "observe", "target", "targets"}
VERSION = re.compile(
    r"^(?:refs/)?(?:tags/)?(?:(?P<component>[A-Za-z0-9_.-]+)/)?v?(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)$"
)


@dataclass(frozen=True)
class TargetSpec:
    name: str
    kind: str
    run_by: str = "platform"
    stages: tuple[str, ...] = ()
    options: dict[str, Any] = field(default_factory=dict)
    observe: bool | None = None

    @property
    def platform(self) -> bool:
        return self.run_by == "platform"

    @property
    def server(self) -> bool:
        """Run by a CI server of its own — a runner a plugin brings, connected with its own credentials — rather than the platform, a person or the source host's CI."""
        return self.run_by not in EXECUTORS

    @property
    def dispatched(self) -> bool:
        """Run by a CI the platform can start and follow: the deploy is a run of the repository's own pipeline."""
        return (self.run_by in EMBEDDED_EXECUTORS or self.server) and not self.observing

    @property
    def observing(self) -> bool:
        """`observe` as written, else true for a CI server, which the platform only reads unless told otherwise."""
        if self.observe is not None:
            return self.observe

        return self.server

    @property
    def observed(self) -> bool:
        """Deployed by someone else — a CI server, a person, or a CI target with `observe = true`: its runs are recorded and verified, a platform deploy never runs it."""
        return not self.platform and not self.dispatched

    def serves(self, stage: str) -> bool:
        return not self.stages or stage in self.stages

    @property
    def workflow(self) -> str:
        return str(self.options.get("workflow") or "")

    @property
    def job(self) -> str:
        return str(self.options.get("job") or "")

    @property
    def component(self) -> str:
        return str(self.options.get("component") or "")

    @property
    def version_parameter(self) -> str:
        return str(self.options.get("version_parameter") or "")

    @property
    def stage_parameter(self) -> str:
        return str(self.options.get("stage_parameter") or "")

    def run_version(self, ref: str | None, params: dict[str, str]) -> str | None:
        """The release a run shipped: the tag it built, else the value of `version_parameter` — `v1.2.3`, `1.2.3` or `<component>/v1.2.3`."""
        found = version_from_ref(ref, self.component)

        if found is not None or not self.version_parameter:
            return found

        value = (params.get(self.version_parameter) or "").strip()
        found = version_from_ref(value, self.component)

        if found is None and "/" not in value:
            found = version_from_ref(value)

        return found

    def run_stage(self, params: dict[str, str]) -> str | None:
        """The scope a run deployed to: the value of `stage_parameter`, else the target's only stage."""
        if self.stage_parameter:
            value = (params.get(self.stage_parameter) or "").strip()

            if value:
                return value

        return self.stages[0] if len(self.stages) == 1 else None


def parse_targets(cfg: dict) -> list[TargetSpec]:
    """Every target of `[deploy]`: the short form as one platform target named after its kind, then `[[deploy.targets]]`."""
    specs: list[TargetSpec] = []

    if cfg.get("target"):
        specs.append(
            TargetSpec(
                name=str(cfg["target"]),
                kind=str(cfg["target"]),
                options={k: v for k, v in cfg.items() if k not in RESERVED},
            )
        )

    for raw in cfg.get("targets") or []:
        if not isinstance(raw, dict) or not raw.get("kind"):
            raise ConfigError("[[deploy.targets]] needs a kind")

        run_by = str(raw.get("run_by") or "platform")

        if run_by not in EXECUTORS and not SERVER_NAME.match(run_by):
            raise ConfigError(
                f"[[deploy.targets]] run_by {run_by!r} is not one of {', '.join(EXECUTORS)} nor the name of a CI server's runner"
            )

        observe = raw.get("observe")

        if observe is not None and not isinstance(observe, bool):
            raise ConfigError("[[deploy.targets]] observe is true or false")

        if observe and run_by == "platform":
            raise ConfigError(
                '[[deploy.targets]] observe applies to a target another executor runs, not to run_by = "platform"'
            )

        stages = raw.get("stages") or ()
        specs.append(
            TargetSpec(
                name=str(raw.get("name") or raw["kind"]),
                kind=str(raw["kind"]),
                run_by=run_by,
                stages=tuple(str(s) for s in stages),
                options={k: v for k, v in raw.items() if k not in RESERVED},
                observe=observe,
            )
        )

    names = [s.name for s in specs]

    if len(names) != len(set(names)):
        raise ConfigError("[[deploy.targets]] names must be unique")

    return specs


def version_from_ref(ref: str | None, component: str = "") -> str | None:
    """The release a git ref names — `v1.2.3`, `refs/tags/v1.2.3`, `web/v1.2.3` — or None for a branch. With `component`, only that component's tags count; without, only the root's."""
    if not ref:
        return None

    found = VERSION.match(ref.strip())

    if found is None:
        return None

    if (found.group("component") or "") != component:
        return None

    return found.group("version")


__all__ = [
    "EMBEDDED_EXECUTORS",
    "EXECUTORS",
    "TargetSpec",
    "parse_targets",
    "version_from_ref",
]
