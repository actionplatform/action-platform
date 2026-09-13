"""Credentials, the device-flow login, and the remote MCP tool surface — no network."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from action_platform.core.exception import ActionPlatformError
from action_platform.remote import client, credentials


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AP_HOME", str(tmp_path))
    monkeypatch.delenv("AP_SERVER", raising=False)
    monkeypatch.delenv("AP_TOKEN", raising=False)

    return tmp_path


def test_credentials_roundtrip(home: Path):
    assert credentials.load() is None

    credentials.save(credentials.Credentials("https://p.example", "tok"))
    file = home / "action-platform" / "credentials.json"
    assert file.stat().st_mode & 0o777 == 0o600
    assert credentials.load() == credentials.Credentials("https://p.example", "tok")

    assert credentials.clear() is True
    assert credentials.load() is None


def test_env_credentials_win(monkeypatch):
    monkeypatch.setenv("AP_SERVER", "https://env.example")
    monkeypatch.setenv("AP_TOKEN", "env-tok")

    assert credentials.load() == credentials.Credentials(
        "https://env.example", "env-tok"
    )


def test_login_polls_until_approved(monkeypatch):
    calls: list[tuple[str, str]] = []
    answers = iter(
        [
            {
                "device_code": "dc",
                "user_code": "ABCD-EFGH",
                "verification_uri": "/device",
                "interval": 0,
                "expires_in": 60,
            },
            client.RemoteError(400, "authorization_pending"),
            client.RemoteError(400, "slow_down"),
            client.ActionPlatformError("cannot reach https://p.example: timed out"),
            {"access_token": "session-token", "token_type": "Bearer"},
        ]
    )

    def fake_request(method, url, body=None, token=None, timeout=60):
        calls.append((method, url))
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(client, "_request", fake_request)
    monkeypatch.setattr(client.time, "sleep", lambda s: None)
    opened: list[str] = []
    monkeypatch.setattr(client.webbrowser, "open", lambda u: opened.append(u))

    shown: list[str] = []
    creds = client.login("https://p.example/", echo=shown.append)

    assert creds == credentials.Credentials("https://p.example", "session-token")
    assert credentials.load() == creds
    assert opened == ["https://p.example/device"]
    assert any("ABCD-EFGH" in line for line in shown)
    assert calls[0] == ("POST", "https://p.example/api/auth/device/code")
    assert calls[-1] == ("POST", "https://p.example/api/auth/device/token")
    assert len(calls) == 5


def test_login_denied(monkeypatch):
    answers = iter(
        [
            {"device_code": "dc", "user_code": "X", "interval": 0, "expires_in": 60},
            client.RemoteError(400, "access_denied"),
        ]
    )

    def fake_request(method, url, body=None, token=None, timeout=60):
        answer = next(answers)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(client, "_request", fake_request)
    monkeypatch.setattr(client.time, "sleep", lambda s: None)

    with pytest.raises(ActionPlatformError, match="denied"):
        client.login("https://p.example", open_browser=False, echo=lambda _: None)


def test_remote_calls_v1_with_bearer(monkeypatch):
    seen = {}

    def fake_request(method, url, body=None, token=None, timeout=60):
        seen.update(method=method, url=url, body=body, token=token)
        return {"ok": True}

    monkeypatch.setattr(client, "_request", fake_request)
    remote = client.Remote("https://p.example", "tok")

    remote.release("p1", "minor", dry_run=False)
    assert seen["method"] == "POST"
    assert seen["url"] == "https://p.example/api/v1/apps/p1/release"
    assert seen["body"] == {"level": "minor", "dry_run": False, "branch": None}
    assert seen["token"] == "tok"

    remote.commits("p1", limit=5)
    assert seen["url"] == "https://p.example/api/v1/apps/p1/commits?limit=5"


def test_from_credentials_requires_login():
    with pytest.raises(ActionPlatformError, match="login"):
        client.Remote.from_credentials()


def test_remote_mcp_tools():
    pytest.importorskip("mcp")
    from action_platform.mcp import build

    credentials.save(credentials.Credentials("https://p.example", "tok"))
    server = build(remote="")
    names = {t.name for t in asyncio.run(server.list_tools())}

    assert {
        "whoami",
        "list_apps",
        "add_app",
        "sync_app",
        "release",
        "deploy",
        "gitflow_rules",
    } <= names
    assert "init_project" not in names
    assert "install_hooks" not in names


def _device_login(monkeypatch, *answers):
    replies = iter(
        [
            {
                "device_code": "dc",
                "user_code": "X",
                "verification_uri": "/device",
                "interval": 0,
                "expires_in": 60,
            },
            *answers,
        ]
    )

    def fake_request(method, url, body=None, token=None, timeout=60):
        answer = next(replies)
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(client, "_request", fake_request)
    monkeypatch.setattr(client.time, "sleep", lambda s: None)
    monkeypatch.setattr(client.webbrowser, "open", lambda u: None)


def test_login_reports_denied_and_expired(monkeypatch):
    _device_login(monkeypatch, client.RemoteError(400, "access_denied"))
    with pytest.raises(client.ActionPlatformError, match="denied"):
        client.login("https://p.example", echo=lambda s: None)

    _device_login(monkeypatch, client.RemoteError(400, "expired_token"))
    with pytest.raises(client.ActionPlatformError, match="expired"):
        client.login("https://p.example", echo=lambda s: None)

    _device_login(monkeypatch, client.RemoteError(400, "request pending review"))
    with pytest.raises(client.RemoteError):
        client.login("https://p.example", echo=lambda s: None)


def test_login_gives_up_after_repeated_network_failures(monkeypatch):
    _device_login(
        monkeypatch, *[client.ActionPlatformError("cannot reach") for _ in range(7)]
    )
    with pytest.raises(client.ActionPlatformError, match="giving up"):
        client.login("https://p.example", echo=lambda s: None)
