"""Plugin ABC — what a package installed next to the CLI can add: MCP tools, CLI commands, cloud overlays, and a word after a release, a deploy or a pull request.

Deploy targets and CI runners are not declared here: they keep their own
entry-point groups (`action_platform.deploy_target`, `action_platform.ci_runner`)
and a plugin package ships them alongside. Everything a plugin does runs
in-process on the machine that installed it; there is no sandbox, and the
hosted platform never loads one.
"""

import logging
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

from action_platform.logging import attach

if TYPE_CHECKING:
    from action_platform.core.context import Context, DeployResult, PRRef
    from action_platform.core.wiring import Wiring
    from action_platform.plugins.options import Options


@dataclass
class Surface:
    """What a plugin registers on: the MCP server (tools come out as `<slug>_<name>`), the Typer app, the core's wiring where a slot can be replaced with a subclass, and `options` — the plugin's own key/value store, a file on a machine and a table on the hosted platform. `mcp` and `cli` are None in a process that has no such surface."""

    core: "Wiring"
    options: "Options"
    mcp: Any = None
    cli: Any = None


@dataclass(frozen=True)
class Option:
    """One setting a plugin asks its users for — the platform draws the form and stores the value in the plugin's options store under `key`."""

    key: str
    label: str
    kind: Literal["text", "url", "secret", "bool"] = "text"
    help: str = ""
    required: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "help": self.help,
            "required": self.required,
        }


class Plugin(ABC):
    """Plugin"""

    slug: str
    name: str = ""
    description: str = ""
    min_core: str = ""
    needs: list[str] = []
    options: list[Option] = []

    @property
    def title(self) -> str:
        return self.name or self.slug

    @property
    def logger(self) -> logging.Logger:
        """The plugin's own logger, routed to whoever follows the job on the platform — `self.logger.info(...)` inside a deploy shows up in the run log."""
        name = type(self).__module__.split(".")[0]
        attach(name)

        return logging.getLogger(name)

    @property
    def overlays(self) -> Optional[Path]:
        """A directory shaped like the templates repository (`index.json` with `clouds`, `cloud/<name>/` overlays) or None."""
        return None

    def register(self, surface: Surface) -> None:
        """Declare tools on `surface.mcp`, commands on `surface.cli`, replacements on `surface.core`. No I/O here."""

    def after_release(self, ctx: "Context") -> None:
        """Called once a release was really cut (never on a dry run)."""

    def after_deploy(self, results: list["DeployResult"]) -> None:
        """Called once a deploy really ran (never on preflight)."""

    def after_pull_request(self, ref: "PRRef") -> None:
        """Called once a pull request was opened."""
