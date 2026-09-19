from datetime import datetime, timedelta, timezone
from pathlib import Path

from action_platform.abc.ci_runner import CIRunner
from action_platform.core.config import Config
from action_platform.core.context import Context, Run, RunRef
from action_platform.providers.deploy.dispatched import DispatchedTarget
from action_platform.providers.deploy.pypi import DeployPypi


class FakeRunner(CIRunner):
    name = "github_actions"

    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.started = []

    def test(self):
        return None

    def start(self, job, ref, params=None):
        self.started.append((job, ref, params))
        return RunRef(id=f"{job}@{ref}")

    def runs(self, job, limit=50):
        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]
        return [
            Run(
                number=7,
                status=status,
                url="https://github.com/o/r/actions/runs/7",
                branch="v1.2.0",
                trigger="workflow_dispatch",
                started_at=datetime.now(timezone.utc) + timedelta(seconds=1),
            )
        ]


def context(tmp_path):
    return Context(repo_root=tmp_path, next_version="1.2.0", stage="pypi", tag="v1.2.0")


def test_deploy_dispatches_the_workflow_on_the_tag_and_follows_the_run(
    tmp_path, monkeypatch
):
    monkeypatch.setattr("action_platform.providers.deploy.dispatched.POLL_SECONDS", 0)
    inner = DeployPypi(package="my-lib")
    monkeypatch.setattr(inner, "verify", lambda version, stage=None: True)
    runner = FakeRunner(["queued", "running", "success"])
    target = DispatchedTarget(inner, runner, "publish.yml")

    result = target.deploy(context(tmp_path))

    assert runner.started == [
        ("publish.yml", "v1.2.0", {"version": "1.2.0", "registry": "pypi"})
    ]
    assert result.ok
    assert result.url == "https://pypi.org/project/my-lib/1.2.0/"


def test_a_failed_run_fails_the_deploy(tmp_path, monkeypatch):
    monkeypatch.setattr("action_platform.providers.deploy.dispatched.POLL_SECONDS", 0)
    target = DispatchedTarget(
        DeployPypi(package="my-lib"), FakeRunner(["failure"]), "publish.yml"
    )

    result = target.deploy(context(tmp_path))

    assert not result.ok
    assert "failure" in result.error
    assert result.url == "https://github.com/o/r/actions/runs/7"


def test_config_wraps_ci_run_targets_and_keeps_stages(tmp_path):
    config = Config.from_dict(
        {
            "project": {"name": "lib"},
            "source_host": {"kind": "github", "repo": "o/r"},
            "deploy": {
                "targets": [
                    {
                        "name": "pypi",
                        "kind": "pypi",
                        "run_by": "github_actions",
                        "workflow": "publish.yml",
                        "package": "lib",
                    },
                    {
                        "name": "testpypi",
                        "kind": "pypi",
                        "run_by": "github_actions",
                        "workflow": "publish.yml",
                        "package": "lib",
                        "index_url": "https://test.pypi.org",
                        "stages": ["testpypi"],
                    },
                ]
            },
        }
    )

    dispatched = config.dispatched()

    assert [t.name for t in dispatched] == ["pypi", "testpypi"]
    assert all(isinstance(t, DispatchedTarget) for t in dispatched)
    assert dispatched[0].runner.name == "github_actions"
    assert config.deploy == []
    assert [t.name for t in config.targets if t.serves("pypi")] == ["pypi"]
