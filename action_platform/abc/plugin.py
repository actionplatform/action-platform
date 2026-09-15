"""Plugin ABC — what a package installed next to the CLI can add: MCP tools, CLI commands, cloud overlays, and a word after a release, a deploy or a pull request.

Deploy targets and CI runners are not declared here: they keep their own
entry-point groups (`action_platform.deploy_target`, `action_platform.ci_runner`)
and a plugin package ships them alongside. Everything a plugin does runs
in-process on the machine that installed it; there is no sandbox, and the
hosted platform never loads one.
"""

from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from action_platform.core.context import Context, DeployResult, PRRef
    from action_platform.core.wiring import Wiring


@dataclass
class Surface:
    """What a plugin registers on: the MCP server (tools come out as `<slug>_<name>`), the Typer app, and the core's wiring where a slot can be replaced with a subclass. `mcp` and `cli` are None in a process that has no such surface."""

    core: "Wiring"
    mcp: Any = None
    cli: Any = None


class Plugin(ABC):
    """Plugin"""

    slug: str
    description: str = ""
    min_core: str = ""
    needs: list[str] = []

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
