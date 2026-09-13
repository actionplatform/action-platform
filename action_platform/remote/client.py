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
MAX_POLL_FAILURES = 5


class RemoteError(ActionPlatformError):
    """An HTTP error from the platform: `detail` is the human message, `code` the machine one when the server sends both (OAuth's `error` + `error_description`)."""

    def __init__(self, status: int, detail: str, code: str | None = None) -> None:
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail
        self.code = code or detail


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
        if not isinstance(payload, dict):
            payload = {"detail": str(payload)}
        detail = (
            payload.get("detail")
            or payload.get("error_description")
            or payload.get("error")
            or str(payload)
        )
        code = payload.get("error") if isinstance(payload.get("error"), str) else None
        raise RemoteError(e.code, str(detail), code) from e
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

    def apps(self) -> list[dict]:
        return self._call("GET", "apps")

    def add_app(
        self, url: str, name: Optional[str] = None, install: Optional[dict] = None
    ) -> dict:
        return self._call(
            "POST", "apps", {"url": url, "name": name, "install": install}
        )

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

    def release(
        self,
        id: str,
        level: str = "patch",
        dry_run: bool = True,
        branch: Optional[str] = None,
    ) -> dict:
        return self._call(
            "POST",
            f"apps/{id}/release",
            {"level": level, "dry_run": dry_run, "branch": branch},
        )

    def releases(self, id: str) -> list[dict]:
        return self._call("GET", f"apps/{id}/releases")

    def start_branch(
        self, id: str, kind: str, code: str, slug: Optional[str], push: bool
    ) -> dict:
        return self._call(
            "POST",
            f"apps/{id}/branches",
            {"kind": kind, "code": code, "slug": slug, "push": push},
        )

    def checkout(self, id: str, branch: str) -> dict:
        return self._call("POST", f"apps/{id}/checkout", {"branch": branch})

    def propose_pr(
        self, id: str, base: Optional[str] = None, title: Optional[str] = None
    ) -> dict:
        return self._call("GET", f"apps/{id}/pull-request", base=base, title=title)

    def open_pr(
        self,
        id: str,
        base: Optional[str],
        title: Optional[str],
        body: Optional[str],
        draft: bool,
    ) -> dict:
        return self._call(
            "POST",
            f"apps/{id}/pull-request",
            {"base": base, "title": title, "body": body, "draft": draft},
        )

    def manifest(self, id: str) -> dict:
        return self._call("GET", f"apps/{id}/manifest")

    def write_manifest(self, id: str, content: str) -> dict:
        return self._call("PUT", f"apps/{id}/manifest", {"content": content})

    def set_cloud(self, id: str, target: str, source: Optional[str] = None) -> dict:
        return self._call(
            "POST", f"apps/{id}/cloud", {"target": target, "source": source}
        )

    def add_service(
        self,
        id: str,
        name: str,
        provider: Optional[str] = None,
        source: Optional[str] = None,
    ) -> dict:
        return self._call(
            "POST",
            f"apps/{id}/services",
            {"name": name, "provider": provider, "source": source},
        )

    def commit(
        self,
        id: str,
        message: str,
        push: bool = False,
        branch: Optional[dict] = None,
        pull_request: bool = False,
    ) -> dict:
        return self._call(
            "POST",
            f"apps/{id}/commit",
            {
                "message": message,
                "push": push,
                "branch": branch,
                "pull_request": pull_request,
            },
        )

    def init(self, body: dict) -> dict:
        return self._call("POST", "apps/init", body)

    def deploy(
        self, id: str, stage: Optional[str] = None, dry_run: bool = True
    ) -> list[dict]:
        return self._call(
            "POST", f"apps/{id}/deploy", {"stage": stage, "dry_run": dry_run}
        )

    def diagnose(self, id: str, stage: Optional[str] = None) -> list[dict]:
        return self._call("GET", f"apps/{id}/diagnose", stage=stage)

    def matrix(self) -> dict:
        return self._call("GET", "matrix")

    def version(self) -> dict:
        return self._call("GET", "version")

    def whoami(self) -> dict:
        return _request("GET", f"{self.server}/api/v1/me", token=self.token) or {}


SCOPES = ("read", "write", "release", "admin")
DEFAULT_SCOPE = "read,write"


def parse_scope(value: str) -> list[str]:
    """`read,write` / `read write` → ordered, deduplicated, validated; `read` is always included."""
    wanted = {part for part in value.replace(",", " ").split() if part}
    unknown = sorted(wanted - set(SCOPES))

    if unknown:
        raise ActionPlatformError(
            f"unknown scope: {', '.join(unknown)} (choose from {', '.join(SCOPES)})"
        )

    wanted.add("read")

    return [s for s in SCOPES if s in wanted]


def login(
    server: str,
    open_browser: bool = True,
    echo=print,
    scope: str = DEFAULT_SCOPE,
    name: str | None = None,
) -> Credentials:
    """OAuth device flow against the web app: show a code, open the browser, poll for approval, then swap the session for a scoped bearer token."""
    server = server.rstrip("/")
    scopes = parse_scope(scope)
    start = _request(
        "POST",
        f"{server}/api/auth/device/code",
        {"client_id": CLIENT_ID, "scope": " ".join(scopes)},
    )

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

    failures = 0

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
            if e.code == "authorization_pending":
                continue
            if e.code == "slow_down":
                interval += 5
                continue
            if e.code == "access_denied":
                raise ActionPlatformError("login denied in the browser") from e
            if e.code == "expired_token":
                raise ActionPlatformError(
                    "the code expired before it was confirmed — run login again"
                ) from e
            raise
        except ActionPlatformError as e:
            failures += 1

            if failures > MAX_POLL_FAILURES:
                raise ActionPlatformError(
                    f"cannot reach {server} — giving up after {failures} attempts: {e}"
                ) from e

            echo(f"({e}; retrying)")
            continue

        failures = 0

        access = token.get("access_token")

        if not access:
            raise ActionPlatformError(f"unexpected token response: {token}")

        granted = (token.get("scope") or " ".join(scopes)).replace(",", " ")
        minted = _request(
            "POST",
            f"{server}/api/v1/tokens",
            {"scope": granted, "name": name or _device_name()},
            token=access,
        )
        creds = Credentials(
            server=server,
            token=minted["token"],
            scope=minted.get("scope") or granted,
        )
        save(creds)

        return creds

    raise ActionPlatformError("login timed out — run it again")


def _device_name() -> str:
    import getpass
    import socket

    try:
        return f"{getpass.getuser()}@{socket.gethostname()}"
    except Exception:
        return "cli"
