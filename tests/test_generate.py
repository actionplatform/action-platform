"""platform.toml bookkeeping: deploy target, services, source host."""

from pathlib import Path

from action_platform.core.manifest import read_platform, write_deploy_target

BASE = '[project]\nname = "x"\ntype = "web"\nlanguage = "python"\n'


def test_appends_deploy_section(tmp_path: Path):
    p = tmp_path / "platform.toml"
    p.write_text(BASE)
    write_deploy_target(p, "aws/lambda")
    assert p.read_text().endswith('\n[deploy]\ntarget = "aws/lambda"\n')
    assert read_platform(tmp_path)["language"] == "python"


def test_replaces_existing_target(tmp_path: Path):
    p = tmp_path / "platform.toml"
    p.write_text(BASE + '\n[deploy]\ntarget = "docker"\n')
    write_deploy_target(p, "aws/lambda")
    assert p.read_text().count("[deploy]") == 1
    assert 'target = "aws/lambda"' in p.read_text()
    assert 'target = "docker"' not in p.read_text()


def test_services_section(tmp_path: Path):
    from action_platform.core.manifest import write_service

    p = tmp_path / "platform.toml"
    p.write_text(BASE + '\n[deploy]\ntarget = "docker"\n')
    write_service(p, "postgres", "docker")
    write_service(p, "redis", "docker")
    write_service(p, "postgres", "aws-rds")
    text = p.read_text()
    assert text.count("[services]") == 1
    assert 'postgres = "aws-rds"' in text and 'postgres = "docker"' not in text
    assert 'redis = "docker"' in text
    assert 'target = "docker"' in text


def test_write_source_host_replaces_and_adds(tmp_path: Path):
    from action_platform.core.manifest import write_source_host

    p = tmp_path / "platform.toml"
    p.write_text(
        BASE
        + '\n[source_host]\nkind = "github"\nrepo = "a/b"\n\n[release]\nstrategy = "semver"\n'
    )
    write_source_host(p, "gitlab", "grp/b", "https://gitlab.example.com")
    text = p.read_text()
    assert text.count("[source_host]") == 1
    assert 'kind = "gitlab"' in text and 'repo = "grp/b"' in text
    assert 'base_url = "https://gitlab.example.com"' in text
    assert 'kind = "github"' not in text
    assert '[release]\nstrategy = "semver"' in text

    q = tmp_path / "plain.toml"
    q.write_text(BASE)
    write_source_host(q, "bitbucket", "ws/x")
    assert q.read_text().endswith(
        '\n[source_host]\nkind = "bitbucket"\nrepo = "ws/x"\n'
    )
