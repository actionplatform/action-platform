"""Context and pipeline value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


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


@dataclass
class DeployResult:
    ok: bool
    target: str
    version: str
    url: str | None = None
    error: str | None = None


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
