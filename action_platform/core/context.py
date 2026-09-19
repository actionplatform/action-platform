"""Context and pipeline value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional


@dataclass
class ReleaseRef:
    id: str
    tag: str
    url: str


@dataclass
class PRRef:
    number: int
    url: str


@dataclass
class RunRef:
    id: str
    url: str | None = None


@dataclass
class RunResult:
    ok: bool
    duration: float
    output: str = ""


RUN_STATUSES = (
    "queued",
    "running",
    "success",
    "failure",
    "unstable",
    "aborted",
    "unknown",
)


@dataclass
class Run:
    """One CI run (a Jenkins build, an Actions workflow run, a GitLab pipeline) in the platform's shape."""

    number: int
    status: str
    url: str | None = None
    branch: str | None = None
    sha: str | None = None
    trigger: str | None = None
    started_at: Optional[datetime] = None
    duration_ms: int | None = None
    name: str | None = None


@dataclass
class DeployResult:
    ok: bool
    target: str
    version: str
    url: str | None = None
    error: str | None = None


CHECK_LEVELS = ("static", "target", "plan", "proof")
CHECK_SEVERITIES = ("error", "warning")


@dataclass
class Check:
    """One answer to "can this release reach this stage?": what was looked at, whether it holds, and what to do when it does not."""

    id: str
    ok: bool
    detail: str = ""
    level: str = "target"
    severity: str = "error"
    fix: str | None = None
    target: str | None = None

    @property
    def blocking(self) -> bool:
        return not self.ok and self.severity == "error"


@dataclass
class Diagnosis:
    ok: bool
    target: str
    status: str = ""
    version: str | None = None
    url: str | None = None
    details: dict[str, str] = field(default_factory=dict)


@dataclass
class Context:
    repo_root: Path
    remote_url: str = ""
    branch: str = ""
    current_version: str = "0.0.0"
    next_version: str = "0.0.0"
    changelog: str = ""
    artifacts: list[Path] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    dry_run: bool = False
    stage: str = "dev"
    criticality: str = ""
    tag: str = ""
    identity: Optional[Callable[[str], str]] = None

    def identity_token(self, audience: str) -> Optional[str]:
        """A short-lived OIDC token the platform signs for this deploy, for `audience` (`sts.amazonaws.com`…); None when nothing can issue one — a plain machine without a login."""
        return self.identity(audience) if self.identity else None
