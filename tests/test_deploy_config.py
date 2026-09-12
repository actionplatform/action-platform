"""[deploy] table → DeployTarget provider via entry points."""

from pathlib import Path

import pytest

from action_platform.core import config as config_module
from action_platform.core.config import Config
from action_platform.core.exception import ConfigError

BASE = '[project]\nname = "my-api"\nlanguage = "python"\n'


class FakeTarget:
    name = "fake"

    def __init__(self, region: str = "us-east-1") -> None:
        self.region = region


def _config(tmp_path: Path, deploy: str) -> Config:
    p = tmp_path / "platform.toml"
    p.write_text(BASE + deploy)
    return Config.from_toml(p)


def test_no_deploy_section(tmp_path: Path):
    assert _config(tmp_path, "").deploy == []


def test_target_resolved_from_entry_points(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(
        "action_platform.core.module.load_deploy_targets", lambda: {"fake": FakeTarget}
    )
    (t,) = _config(tmp_path, '[deploy]\ntarget = "fake"\nregion = "sa-east-1"\n').deploy
    assert isinstance(t, FakeTarget)
    assert t.region == "sa-east-1"


def test_unknown_target(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("action_platform.core.module.load_deploy_targets", lambda: {})
    with pytest.raises(ConfigError, match="no provider installed"):
        _config(tmp_path, '[deploy]\ntarget = "aws/lambda"\n').deploy


def test_config_module_has_no_provider_imports():
    import inspect

    src = inspect.getsource(config_module)
    assert "deploy_aws" not in src and "deploy_docker" not in src


def test_loading_never_needs_a_provider(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("action_platform.core.module.load_deploy_targets", lambda: {})
    config = _config(tmp_path, '[deploy]\ntarget = "aws/lambda"\n')
    assert config.project_name == "my-api"
    with pytest.raises(ConfigError):
        config.deploy
