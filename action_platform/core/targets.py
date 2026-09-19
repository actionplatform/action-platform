"""Deploy targets as platform.toml declares them: where a version goes and who puts it there.

    [deploy]
    target = "aws/lambda"          # one target, run by the platform (short form)
    region = "us-east-1"

    [[deploy.targets]]
    name = "pypi"
    kind = "pypi"
    run_by = "github_actions"      # platform | github_actions | jenkins | manual
    workflow = "python-publish-pypi.yml"
    package = "action-platform"

The platform executes `run_by = "platform"` targets itself and dispatches the
CI-run ones (`github_actions`, `gitlab_ci`, `bitbucket_pipelines`): it starts
the workflow on the release tag and follows the run. `jenkins` and `manual`
targets are observed — their runs become deployment records — and verified.
`stages` limits a target to some scopes. A dispatched workflow receives the
registry the kind pairs with the scope's criticality — a `test` scope publishes
to TestPyPI or the npm `next` tag — unless the target fixes one with `registry`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from action_platform.core.exception import ConfigError

EXECUTORS = (
    "platform",
    "github_actions",
    "gitlab_ci",
    "bitbucket_pipelines",
    "jenkins",
    "manual",
)
RESERVED = {"name", "kind", "run_by", "stages", "target", "targets"}
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

    @property
    def platform(self) -> bool:
        return self.run_by == "platform"

    @property
    def dispatched(self) -> bool:
        """Run by a CI the platform can start and follow: the deploy is a run of the repository's own pipeline."""
        return self.run_by in ("github_actions", "gitlab_ci", "bitbucket_pipelines")

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

        if run_by not in EXECUTORS:
            raise ConfigError(
                f"[[deploy.targets]] run_by {run_by!r} is not one of {', '.join(EXECUTORS)}"
            )

        stages = raw.get("stages") or ()
        specs.append(
            TargetSpec(
                name=str(raw.get("name") or raw["kind"]),
                kind=str(raw["kind"]),
                run_by=run_by,
                stages=tuple(str(s) for s in stages),
                options={k: v for k, v in raw.items() if k not in RESERVED},
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


__all__ = ["EXECUTORS", "TargetSpec", "parse_targets", "version_from_ref"]
