"""The GitHub REST client: one `Http` with the token in its headers."""

from __future__ import annotations

from action_platform.core.service_access import Http

API_URL = "https://api.github.com"


def client(token: str, url: str = API_URL) -> Http:
    return Http(
        "github",
        url,
        {
            "authorization": f"Bearer {token}",
            "x-github-api-version": "2022-11-28",
            "accept": "application/vnd.github+json",
        },
    )
