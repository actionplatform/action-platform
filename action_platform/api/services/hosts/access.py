"""What a connected account may create with, in one shape for every provider."""

from __future__ import annotations

import re
from typing import Any

from action_platform.api.services.shared.http import get_json
from action_platform.core.exception import ProviderError


def _get(url: str, headers: dict[str, str]) -> tuple[int, Any]:
    try:
        return 200, get_json(url, headers)
    except ProviderError as e:
        digits = re.match(r"(\d{3}) from", str(e))

        return (int(digits.group(1)) if digits else 0), None


def _owner(
    account: str,
    kind: str,
    repositories: str,
    administration: str,
    contents: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "account": account,
        "kind": kind,
        "repositories": repositories,
        "administration": administration,
        "contents": contents,
        "canCreateRepos": administration == "write" and contents == "write",
        "selected": extra.get("selected"),
        "configureUrl": extra.get("configure_url"),
    }
