"""git_auth injects a credential helper through the environment and restores it."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from action_platform.api.core.credentials import SourceCredentials, git_auth  # noqa: E402


def test_git_auth_sets_and_restores_env(monkeypatch):
    monkeypatch.delenv("GIT_CONFIG_COUNT", raising=False)
    creds = SourceCredentials(kind="gitlab", token="glpat-x")

    with git_auth(creds):
        assert os.environ["GIT_CONFIG_KEY_0"] == "credential.helper"
        assert os.environ["AP_GIT_USER"] == "oauth2"
        assert os.environ["AP_GIT_TOKEN"] == "glpat-x"
        assert os.environ["GIT_TERMINAL_PROMPT"] == "0"

    assert "GIT_CONFIG_COUNT" not in os.environ
    assert "AP_GIT_TOKEN" not in os.environ


def test_git_reads_helper_from_env(tmp_path: Path):
    """git credential fill must answer with the injected user/token."""
    creds = SourceCredentials(kind="github", token="ghp_test")

    with git_auth(creds):
        out = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            cwd=tmp_path,
            check=True,
        ).stdout

    assert "username=x-access-token" in out
    assert "password=ghp_test" in out


def test_git_auth_none_is_noop():
    before = dict(os.environ)
    with git_auth(None):
        pass
    assert dict(os.environ) == before


def test_apply_replaces_source_host_on_config(tmp_path: Path):
    from action_platform.api.core.credentials import apply
    from action_platform.core.config import Config

    (tmp_path / "platform.toml").write_text(
        '[project]\nname = "x"\n\n[source_host]\nkind = "github"\nrepo = "a/b"\n'
    )
    config = Config.from_toml(tmp_path / "platform.toml")
    apply(
        config,
        SourceCredentials(kind="gitlab", token="glpat", base_url="https://gl.example"),
    )

    assert config.source_host is not None
    assert config.source_host.name == "gitlab"
    assert config.source_host.repo == "a/b"
