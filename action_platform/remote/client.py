"""HTTP client for a hosted Action Platform (apps/web at `server`).

Every call goes to `/api/v1/...` on the web app, which checks the bearer
token and forwards to the Python API running next to it. Standard library
only, so the CLI stays dependency-free.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from typing import Any, Optional

from action_platform.core.exception import ActionPlatformError
from action_platform.remote.credentials import Credentials, load, save

CLIENT_ID = "action-platform-cli"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"


class RemoteError(ActionPlatformError):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


def _request(
    method: str,
    url: str,
    body: Optional[dict] = None,
    token: Optional[str] = None,
    timeout: float = 60,
) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"accept": "application/json"}

    if data is not None:
        headers["content-type"] = "application/json"

    if token:
        headers["authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, method=method, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            raw = res.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = {"detail": raw.decode(errors="replace") or e.reason}
        detail = (
            payload.get("detail")
            or payload.get("error_description")
            or payload.get("error")
            or str(payload)
        )
        raise RemoteError(e.code, detail) from e
    except urllib.error.URLError as e:
        raise ActionPlatformError(f"cannot reach {url}: {e.reason}") from e


class Remote:
    def __init__(self, server: str, token: str) -> None:
        self.server = server.rstrip("/")
        self.token = token

    @classmethod
    def from_credentials(cls, server: Optional[str] = None) -> "Remote":
        creds = load()

        if creds is None or (server and creds.server.rstrip("/") != server.rstrip("/")):
            raise ActionPlatformError(
                "not logged in: run `action-platform login "
                + (server or "https://<your-platform>")
                + "`"
            )

        return cls(creds.server, creds.token)

    def _call(
        self, method: str, path: str, body: Optional[dict] = None, **query: Any
    ) -> Any:
        q = {k: v for k, v in query.items() if v is not None}
        url = f"{self.server}/api/v1/{path.lstrip('/')}"

        if q:
            url += "?" + urllib.parse.urlencode(q)

        return _request(method, url, body, self.token)

    # apps
    def apps(self) -> list[dict]:
        return self._call("GET", "apps")

    def add_app(self, url: str, name: Optional[str] = None) -> dict:
        return self._call("POST", "apps", {"url": url, "name": name})

    def remove_app(self, id: str) -> None:
        self._call("DELETE", f"apps/{id}")

    def sync_app(self, id: str) -> dict:
        return self._call("POST", f"apps/{id}/sync")

    def app(self, id: str) -> dict:
        return self._call("GET", f"apps/{id}")

    def gitflow(self, id: str) -> dict:
        return self._call("GET", f"apps/{id}/gitflow")

    def commits(self, id: str, limit: int = 20) -> list[dict]:
        return self._call("GET", f"apps/{id}/commits", limit=limit)

    def branches(self, id: str) -> list[dict]:
        return self._call("GET", f"apps/{id}/branches")

    def tags(self, id: str) -> list[str]:
        return self._call("GET", f"apps/{id}/tags")

    def release(self, id: str, level: str = "patch", dry_run: bool = True) -> dict:
        return self._call(
            "POST", f"apps/{id}/release", {"level": level, "dry_run": dry_run}
        )

    def deploy(
        self, id: str, stage: Optional[str] = None, dry_run: bool = True
    ) -> list[dict]:
        return self._call(
            "POST", f"apps/{id}/deploy", {"stage": stage, "dry_run": dry_run}
        )

    def diagnose(self, id: str, stage: Optional[str] = None) -> list[dict]:
        return self._call("GET", f"apps/{id}/diagnose", stage=stage)

    # static
    def matrix(self) -> dict:
        return self._call("GET", "matrix")

    def version(self) -> dict:
        return self._call("GET", "version")

    def whoami(self) -> dict:
        return (
            _request("GET", f"{self.server}/api/auth/get-session", token=self.token)
            or {}
        )


def login(server: str, open_browser: bool = True, echo=print) -> Credentials:
    """OAuth device flow against the web app: show a code, open the browser, poll for the token."""
    server = server.rstrip("/")
    start = _request("POST", f"{server}/api/auth/device/code", {"client_id": CLIENT_ID})

    user_code = start["user_code"]
    device_code = start["device_code"]
    interval = int(start.get("interval", 5))
    expires = time.monotonic() + int(start.get("expires_in", 600))
    verify = (
        start.get("verification_uri_complete")
        or start.get("verification_uri")
        or f"{server}/device"
    )

    if not verify.startswith("http"):
        verify = f"{server}{verify}"

    echo(f"Open {verify}")
    echo(f"and confirm the code: {user_code}")

    if open_browser:
        webbrowser.open(verify)

    while time.monotonic() < expires:
        time.sleep(interval)

        try:
            token = _request(
                "POST",
                f"{server}/api/auth/device/token",
                {
                    "grant_type": DEVICE_GRANT,
                    "device_code": device_code,
                    "client_id": CLIENT_ID,
                },
            )
        except RemoteError as e:
            if (
                e.detail in ("authorization_pending", "slow_down")
                or "pending" in e.detail
            ):
                if e.detail == "slow_down":
                    interval += 5
                continue
            if "denied" in e.detail:
                raise ActionPlatformError("login denied in the browser") from e
            raise

        access = token.get("access_token")

        if not access:
            raise ActionPlatformError(f"unexpected token response: {token}")

        creds = Credentials(server=server, token=access)
        save(creds)

        return creds

    raise ActionPlatformError("login timed out — run it again")
