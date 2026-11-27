from datetime import datetime, timedelta, timezone

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


def context(tmp_path, criticality="high"):
    return Context(
        repo_root=tmp_path,
        next_version="1.2.0",
        stage="prod",
        criticality=criticality,
        tag="v1.2.0",
    )


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


def test_a_test_scope_publishes_to_the_test_registry(tmp_path, monkeypatch):
    monkeypatch.setattr("action_platform.providers.deploy.dispatched.POLL_SECONDS", 0)
    inner = DeployPypi(package="my-lib")
    asked = []
    monkeypatch.setattr(
        inner, "_exists", lambda url, headers=None: asked.append(url) or True
    )
    runner = FakeRunner(["success"])
    target = DispatchedTarget(inner, runner, "publish.yml")

    result = target.deploy(context(tmp_path, criticality="test"))

    assert runner.started[0][2] == {"version": "1.2.0", "registry": "testpypi"}
    assert asked == ["https://test.pypi.org/pypi/my-lib/1.2.0/json"]
    assert result.url == "https://test.pypi.org/project/my-lib/1.2.0/"


def test_the_target_may_fix_its_registry(tmp_path):
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
                        "registry": "internal",
                    },
                ]
            },
        }
    )

    assert config.dispatched()[0].registry(context(tmp_path, "test")) == "internal"


class FakeJenkins(CIRunner):
    name = "jenkins"

    def __init__(self, statuses, waits=1):
        self.statuses = list(statuses)
        self.waits = waits
        self.started = []

    def test(self):
        return None

    def start(self, job, ref, params=None):
        self.started.append((job, ref, params))
        return RunRef(id="queue:9")

    def run_of(self, job, ref):
        if self.waits:
            self.waits -= 1
            return None

        status = self.statuses.pop(0) if len(self.statuses) > 1 else self.statuses[0]

        return Run(
            number=31,
            status=status,
            url="https://ci.acme.io/job/team/job/app-prod/31/",
            params={"RELEASE_TAG": "v1.2.0"},
        )

    def stages(self, job, number):
        return [("Migrate", "SUCCESS"), ("Publish", "IN_PROGRESS")]


def jenkins_config(ci=None):
    config = Config.from_dict(
        {
            "project": {"name": "app"},
            "deploy": {
                "targets": [
                    {
                        "name": "lambda-prod",
                        "kind": "pypi",
                        "package": "app",
                        "run_by": "jenkins",
                        "observe": False,
                        "job": "team/app-prod",
                        "version_parameter": "RELEASE_TAG",
                        "stages": ["prod-lambda"],
                    },
                    {
                        "name": "container-prod",
                        "kind": "pypi",
                        "package": "app",
                        "run_by": "jenkins",
                        "observe": False,
                        "job": "team/app-prod",
                        "version_parameter": "RELEASE_TAG",
                        "stages": ["prod-container"],
                    },
                    {
                        "name": "watched",
                        "kind": "pypi",
                        "package": "app",
                        "run_by": "jenkins",
                        "job": "team/app-prod",
                    },
                ]
            },
        }
    )
    config.ci = list(ci or [])

    return config


def test_a_jenkins_job_starts_with_the_release_parameter_alone(tmp_path, monkeypatch):
    monkeypatch.setattr("action_platform.providers.deploy.dispatched.POLL_SECONDS", 0)
    runner = FakeJenkins(["running", "success"])
    target = jenkins_config([runner]).dispatched()[0]
    target.inner.verify = lambda version, stage=None: False

    result = target.deploy(context(tmp_path))

    assert runner.started == [("team/app-prod", "", {"RELEASE_TAG": "v1.2.0"})]
    assert result.ok is True
    assert result.url == "https://ci.acme.io/job/team/job/app-prod/31/"


def test_a_failed_jenkins_build_fails_the_deploy(tmp_path, monkeypatch):
    monkeypatch.setattr("action_platform.providers.deploy.dispatched.POLL_SECONDS", 0)
    target = jenkins_config([FakeJenkins(["failure"])]).dispatched()[0]

    result = target.deploy(context(tmp_path))

    assert result.ok is False
    assert result.error == "jenkins run ended failure"


def test_jenkins_targets_need_a_connected_server():
    import pytest

    from action_platform.core.exception import ConfigError

    with pytest.raises(ConfigError, match="no jenkins server is connected"):
        jenkins_config().dispatched()


def test_jenkins_targets_observe_unless_told_otherwise():
    config = jenkins_config([FakeJenkins(["success"])])

    assert [t.name for t in config.dispatched()] == ["lambda-prod", "container-prod"]
    assert [t.name for t in config.targets if t.observed] == ["watched"]


def test_targets_on_one_job_share_its_run():
    config = jenkins_config()

    assert [t.name for t in config.runs_with("lambda-prod")] == ["container-prod"]
    assert config.runs_with("watched") == []


def test_a_jenkins_target_without_a_version_parameter_is_refused(tmp_path):
    import pytest

    from action_platform.core.exception import DeployError

    target = DispatchedTarget(
        DeployPypi(package="x"), FakeJenkins(["success"]), "team/app"
    )

    with pytest.raises(DeployError, match="version_parameter"):
        target.preflight(context(tmp_path))


def test_stages_are_logged_once_each(tmp_path, monkeypatch):
    monkeypatch.setattr("action_platform.providers.deploy.dispatched.POLL_SECONDS", 0)
    lines = []
    monkeypatch.setattr(
        "action_platform.providers.deploy.dispatched.logger.info",
        lambda msg, *args: lines.append(msg % args),
    )
    target = jenkins_config([FakeJenkins(["running", "running", "success"], waits=0)])
    target = target.dispatched()[0]

    target.deploy(context(tmp_path))

    assert lines.count("run 31: stage Migrate SUCCESS") == 1
    assert lines.count("run 31: stage Publish IN_PROGRESS") == 1


def test_a_build_cancelled_in_the_queue_fails_only_this_target(tmp_path, monkeypatch):
    from action_platform.core.exception import DeployError

    monkeypatch.setattr("action_platform.providers.deploy.dispatched.POLL_SECONDS", 0)
    runner = FakeJenkins(["success"], waits=0)

    def cancelled(job, ref):
        raise DeployError("the build of team/app-prod was cancelled in the queue")

    runner.run_of = cancelled
    target = jenkins_config([runner]).dispatched()[0]

    result = target.deploy(context(tmp_path))

    assert result.ok is False
    assert "cancelled in the queue" in result.error


def test_a_jenkins_job_dispatches_a_kind_with_no_provider(tmp_path, monkeypatch):
    monkeypatch.setattr("action_platform.providers.deploy.dispatched.POLL_SECONDS", 0)
    runner = FakeJenkins(["running", "success"])
    config = Config.from_dict(
        {
            "project": {"name": "app"},
            "deploy": {
                "targets": [
                    {
                        "name": "amplify-dev",
                        "kind": "aws/amplify",
                        "run_by": "jenkins",
                        "observe": False,
                        "job": "team/app-dev",
                        "version_parameter": "RELEASE_TAG",
                        "stages": ["dev"],
                    }
                ]
            },
        }
    )
    config.ci = [runner]
    target = config.dispatched()[0]

    result = target.deploy(context(tmp_path))

    assert runner.started == [("team/app-dev", "", {"RELEASE_TAG": "v1.2.0"})]
    assert result.ok is True
    assert target.diagnose(context(tmp_path)).status == "unknown"


def test_a_workflow_still_needs_a_provider_for_its_kind():
    import pytest

    from action_platform.core.exception import ConfigError

    config = Config.from_dict(
        {
            "project": {"name": "app"},
            "source_host": {"kind": "github", "repo": "acme/app"},
            "deploy": {
                "targets": [
                    {
                        "name": "site",
                        "kind": "aws/amplify",
                        "run_by": "github_actions",
                        "workflow": "deploy.yml",
                    }
                ]
            },
        }
    )

    with pytest.raises(ConfigError, match="no provider installed"):
        config.dispatched()
