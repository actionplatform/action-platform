"""platform.toml [deploy] bookkeeping."""

from pathlib import Path

from action_platform.core.generate import _write_deploy_target, read_platform

BASE = '[project]\nname = "x"\ntype = "web"\nlanguage = "python"\n'


def test_appends_deploy_section(tmp_path: Path):
    p = tmp_path / "platform.toml"
    p.write_text(BASE)
    _write_deploy_target(p, "aws/lambda")
    assert p.read_text().endswith('\n[deploy]\ntarget = "aws/lambda"\n')
    assert read_platform(tmp_path)["language"] == "python"


def test_replaces_existing_target(tmp_path: Path):
    p = tmp_path / "platform.toml"
    p.write_text(BASE + '\n[deploy]\ntarget = "docker"\n')
    _write_deploy_target(p, "aws/lambda")
    assert p.read_text().count("[deploy]") == 1
    assert 'target = "aws/lambda"' in p.read_text()
    assert 'target = "docker"' not in p.read_text()
