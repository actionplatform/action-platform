"""BranchProtection ABC: how one code host is told to enforce git-flow on a repository, and what it enforces now."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from action_platform.core.flow.protection import (
        Identity,
        Policy,
        ProtectionState,
    )


class BranchProtection(ABC):
    kind: str

    @abstractmethod
    def identity(self) -> Optional["Identity"]:
        """The account the platform pushes with on this host, the only one a protected branch lets push; None when the host cannot tell."""

    @abstractmethod
    def status(self, policy: "Policy") -> "ProtectionState":
        """What the host enforces now, rule by rule, with what differs from `policy` in `drift`. Reads only."""

    @abstractmethod
    def apply(self, policy: "Policy") -> "ProtectionState":
        """Make the host enforce `policy`, then answer `status`. Raises nothing for a host that refuses: the state says why."""

    def contexts(self, origin: str) -> tuple[str, ...]:
        """Status contexts reported on recent pull requests by a CI living at `origin` (a Jenkins, say)."""
        return ()
