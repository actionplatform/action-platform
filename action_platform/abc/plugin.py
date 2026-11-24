"""Plugin ABC — what a package installed next to the CLI can add: MCP tools, CLI commands, cloud overlays, a word after a release, a deploy or a pull request, and the organization's events on the hosted platform.

Deploy targets and CI runners are not declared here: they keep their own
entry-point groups (`action_platform.deploy_target`, `action_platform.ci_runner`)
and a plugin package ships them alongside. Everything a plugin does runs
in-process; there is no sandbox. The hosted platform runs only the plugins
its image bundles.
"""

import logging
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, Optional

from action_platform.logging import attach

if TYPE_CHECKING:
    from action_platform.core.context import Context, DeployResult, PRRef
    from action_platform.core.events import Event
    from action_platform.core.service_access.provider import AccessProvider
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
    """One setting a plugin asks its users for — the platform draws the form and stores the value in the plugin's options store under `key`. `action_url` puts a button labelled `action_label` beside the field that opens the url, and first copies `action_copy` (a command to paste there) when set; `{issuer}` and `{organization}` are filled in both — where the user goes to get the value. `default` is what the plugin uses while the field is empty, shown as its placeholder."""

    key: str
    label: str
    kind: Literal["text", "url", "secret", "bool"] = "text"
    help: str = ""
    required: bool = False
    action_label: str = ""
    action_url: str = ""
    action_copy: str = ""
    default: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "help": self.help,
            "required": self.required,
            "action_label": self.action_label,
            "action_url": self.action_url,
            "action_copy": self.action_copy,
            "default": self.default,
        }


@dataclass(frozen=True)
class Connection:
    """A connection of the organization the plugin reads through `options.credential(kind)` — `github`, `gitlab`, `bitbucket` (the code hosts) or `sentry`. Connecting asks the provider for `scopes` on top of the platform's own; a GitHub App created from the platform's manifest also carries `permissions` (`{"members": "write"}`)."""

    kind: str
    scopes: tuple[str, ...] = ()
    permissions: tuple[tuple[str, str], ...] = ()
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "scopes": list(self.scopes),
            "permissions": dict(self.permissions),
            "reason": self.reason,
        }


class Plugin(ABC):
    """Plugin"""

    slug: str
    name: str = ""
    description: str = ""
    min_core: str = ""
    needs: list[str] = []
    options: list[Option] = []
    connections: list[Connection] = []

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

    def access(self, options: "Options") -> Optional["AccessProvider"]:
        """Access on the plugin's service, built from `options` alone — the organization's values on the hosted platform, the plugin's options file on a machine — and `options.credential(kind)` for a connection the plugin declares in `connections`; None while they do not configure it. Raise `AccessError` when they are incomplete."""
        return None

    def after_release(self, ctx: "Context") -> None:
        """Called once a release was really cut (never on a dry run)."""

    def after_deploy(self, results: list["DeployResult"]) -> None:
        """Called once a deploy really ran (never on preflight)."""

    def after_pull_request(self, ref: "PRRef") -> None:
        """Called once a pull request was opened."""

    def routes(self, event: "Event", options: "Options") -> list[str]:
        """Where the plugin sends `event` under the organization's `options` — one name per destination (`slack`, `webhook`); the hosted platform queues one delivery for each and none when the list is empty. No I/O here."""
        return []

    def deliver(self, event: "Event", route: str, options: "Options") -> None:
        """Send `event` to `route`, on the worker. Raise `ActionPlatformError` when a retry cannot help (a refused URL, a 4xx); any other exception is retried with backoff."""
