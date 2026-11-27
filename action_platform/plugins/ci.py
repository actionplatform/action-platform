"""The CI servers plugins bring, read through the CIRunner contract: which runner a machine is connected to, and the plain answers the `ci_*` tools and `action-platform ci` commands give — the same ones a plugin's own tools hand back.

A server runner is built from three settings, read from the process environment (`AP_<KIND>_URL`, `AP_<KIND>_USER`, `AP_<KIND>_TOKEN`) and then the options of the plugin that registers it (`url`, `user`, `token`).
"""

from __future__ import annotations

import dataclasses
import os
from datetime import datetime
from typing import Any, Callable, Optional

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.exception import ConfigError, ProviderError
from action_platform.core.redact import redact
from action_platform.plugins.options import FileOptions, Options
from action_platform.providers.ci.factory import CI_RUNNERS, build_ci_runner, ci_kinds

KEYS = ("url", "user", "token")


def server_kinds() -> tuple[str, ...]:
    """The CI servers the installed plugins register, built-in runners left out."""
    return tuple(k for k in ci_kinds() if k not in CI_RUNNERS.classes)


def setting(kind: str, key: str, options: Optional[Options] = None) -> Optional[str]:
    found = os.environ.get(f"AP_{kind}_{key}".upper().replace("-", "_"))

    if not found:
        found = (options or FileOptions(kind)).get(key)

    return str(found) if found else None


def runner(kind: str = "", options: Optional[Options] = None) -> CIRunner:
    """The runner of CI server `kind` — the only one installed when empty — connected with its settings."""
    kinds = server_kinds()

    if not kind:
        if len(kinds) != 1:
            raise ConfigError(
                "name the CI server with kind"
                + (f" ({', '.join(kinds)})" if kinds else "; none is installed")
            )

        kind = kinds[0]

    values = {k: setting(kind, k, options) for k in KEYS}

    if not values["url"]:
        raise ConfigError(
            f"{kind}: set AP_{kind.upper().replace('-', '_')}_URL or the plugin's url option"
        )

    return build_ci_runner(
        kind,
        base_url=values["url"],
        username=values["user"],
        token=values["token"],
    )


def plain(value: Any) -> Any:
    """A contract answer as JSON-ready values: dataclasses as dicts, times in ISO 8601."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        out = {f.name: plain(getattr(value, f.name)) for f in dataclasses.fields(value)}

        for name, attr in vars(type(value)).items():
            if isinstance(attr, property):
                out[name] = plain(getattr(value, name))

        return out

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {k: plain(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]

    return value


def _ask(call: Callable[..., Any], *args: Any) -> Any:
    try:
        return call(*args)
    except NotImplementedError as e:
        raise ProviderError(str(e)) from e


def _masked(run: dict[str, Any]) -> dict[str, Any]:
    run["params"] = {k: redact(str(v)) for k, v in run["params"].items()}
    run["parameters"] = run["params"]

    return run


def runs(ci: CIRunner, job: str, limit: int = 20) -> list[dict[str, Any]]:
    """The latest runs of `job`, parameters masked."""
    return [_masked(r) for r in plain(_ask(ci.runs, job, limit))]


def run(ci: CIRunner, job: str, number: int = 0) -> dict[str, Any]:
    """Run `number` of `job`, the latest when 0, its parameters masked."""
    if number <= 0:
        latest = _ask(ci.runs, job, 1)

        if not latest:
            raise ProviderError(f"{job} has no runs")

        number = latest[0].number

    return _masked(plain(_ask(ci.run, job, number)))


def log(
    ci: CIRunner,
    job: str,
    number: int,
    start: int = 0,
    node: Optional[str] = None,
    limit: Optional[int] = None,
) -> dict[str, Any]:
    """One window of a run's log, secrets masked."""
    found = plain(_ask(ci.log, job, number, start, node or None, limit))
    found["text"] = redact(found["text"])

    return found


def queue(ci: CIRunner) -> list[dict[str, Any]]:
    return plain(_ask(ci.queue))


__all__ = ["log", "plain", "queue", "run", "runner", "runs", "server_kinds", "setting"]
