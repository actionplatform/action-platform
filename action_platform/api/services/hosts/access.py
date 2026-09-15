"""The one shape every provider answers an access check in."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from action_platform.api.services.shared.http import http
from action_platform.core.exception import ProviderError


@dataclass
class Owner:
    """An account, installation or workspace the token may create repositories in."""

    account: str
    kind: str
    repositories: str
    administration: str
    contents: str
    selected: Optional[list[str]] = None
    configure_url: Optional[str] = None

    @property
    def can_create_repos(self) -> bool:
        return self.administration == "write" and self.contents == "write"

    def as_dict(self) -> dict[str, Any]:
        return {
            "account": self.account,
            "kind": self.kind,
            "repositories": self.repositories,
            "administration": self.administration,
            "contents": self.contents,
            "canCreateRepos": self.can_create_repos,
            "selected": self.selected,
            "configureUrl": self.configure_url,
        }


@dataclass
class AccessReport:
    kind: str
    login: str
    installations: list[Owner] = field(default_factory=list)
    install_url: Optional[str] = None
    problems: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": True,
            "kind": self.kind,
            "login": self.login,
            "installations": [o.as_dict() for o in self.installations],
            "installUrl": self.install_url,
            "problems": self.problems,
        }

    @staticmethod
    def refused(label: str, status: int) -> dict[str, Any]:
        return {
            "ok": False,
            "error": f"token rejected by {label} ({status}); reconnect the host",
        }


class Probe:
    """GET that answers (status, body) instead of raising, for checks that read what they can."""

    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers

    def get(self, url: str) -> tuple[int, Any]:
        try:
            return 200, http.get_json(url, self.headers)
        except ProviderError as e:
            digits = re.match(r"(\d{3}) from", str(e))

            return (int(digits.group(1)) if digits else 0), None
