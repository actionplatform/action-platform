# Writing a plugin

Start from the template repository [actionplatform/action-platform-plugin](https://github.com/actionplatform/action-platform-plugin); [actionplatform/action-platform-plugin-aws](https://github.com/actionplatform/action-platform-plugin-aws) is a complete one (deploy targets, overlays, CLI, tools).

## Names

| | Format | Example |
|---|---|---|
| repository | `actionplatform/action-platform-plugin-<slug>` or `<you>/action-platform-plugin-<slug>` | `action-platform-plugin-aws` |
| PyPI | `action-platform-plugin-<slug>` | `action-platform-plugin-aws` |
| module | `action_platform_plugin_<slug>` | `action_platform_plugin_aws` |
| slug | `[a-z][a-z0-9-]*`, 2–32 chars; not `core platform official admin system test internal` | `aws` |

## The package

```toml
[project]
name = "action-platform-plugin-aws"
dependencies = ["action-platform>=0.16"]

[project.entry-points."action_platform.plugins"]
aws = "action_platform_plugin_aws:AwsPlugin"

[project.entry-points."action_platform.deploy_target"]
"aws/lambda" = "action_platform_plugin_aws.lambda_:LambdaTarget"
"aws/amplify" = "action_platform_plugin_aws.amplify:AmplifyTarget"

[project.entry-points."action_platform.release_strategy"]
calver = "action_platform_plugin_calver:Calver"

[project.entry-points."action_platform.changelog"]
plain = "action_platform_plugin_calver:Plain"
```

`action_platform.plugins` is the one group every plugin declares; the others are optional and name providers `platform.toml` picks (`[deploy] target`, `[release] strategy`, `[release] changelog`, `[source_host] kind`).

## The class

```python
from pathlib import Path

from action_platform.abc import Plugin, Surface


class AwsPlugin(Plugin):
    slug = "aws"
    description = "Deploy to AWS Lambda and Amplify"
    min_core = "0.16"
    needs = ["env: AWS_PROFILE or AWS_ACCESS_KEY_ID", "tool: sam, aws"]

    @property
    def overlays(self) -> Path:
        return Path(__file__).parent / "overlays"

    def register(self, surface: Surface) -> None:
        if surface.mcp is not None:
            @surface.mcp.tool()
            def logs(function: str, minutes: int = 15) -> dict:
                ...

        if surface.cli is not None:
            surface.cli.add_typer(cli.app, name="aws")

        surface.core.replace("deployer", RetryingDeployer)

    def after_deploy(self, results) -> None:
        ...
```

- `register` only declares. No I/O, no threads, no connections at import or in `register`; the tools and commands do the work when called.
- `surface.mcp.tool()` is the core's own decorator: the tool comes out as `aws.logs`, gets input and output schemas from the annotations (return a pydantic model or a typed dict), and a raised `ActionPlatformError` reaches the model as the tool's error text. While the plugin is disabled the tool answers with an error instead of running.
- `surface.core` is the wiring. `replace(slot, cls)` puts a **subclass** of the core's class in a slot; anything else is refused. Slots: `gitflow_rules` (`core.flow.gitflow.Rules`), `gitflow` (`core.flow.workflow.GitFlow`), `releaser` (`core.release.release.Releaser`), `deployer` (`core.release.deploy.Deployer`), `installer` (`core.scaffold.install.Installer`), `scaffolder` (`core.scaffold.generate.Scaffolder`). Disabling the plugin restores what it replaced.
- `overlays` points at a directory shaped like the templates repository: an `index.json` with `clouds` (`id`, `description`, `types`, `languages`) and `cloud/<name>/` cookiecutter directories. Together with a `DeployTarget` of the same name, that is a complete cloud.
- `after_release(ctx)`, `after_deploy(results)`, `after_pull_request(ref)` run after the real thing; an exception is logged and never undoes the action.

## Providers

| ABC | Entry-point group | Picked by |
|---|---|---|
| `abc.DeployTarget` — `preflight`, `create`, `deploy`, `switch_traffic`, `rollback`, `diagnose`, `delete` | `action_platform.deploy_target` | `[deploy] target` |
| `abc.CIRunner` | `action_platform.ci_runner` | `[ci]` |
| `abc.SourceHost` | `action_platform.source_host` | `[source_host] kind` |
| `abc.ReleaseStrategy` — `next(current, level, prerelease, taken)`, `is_prerelease` | `action_platform.release_strategy` | `[release] strategy` |
| `abc.ChangelogRenderer` — `render(version, commits)` | `action_platform.changelog` | `[release] changelog` |

A disabled plugin's providers disappear from every lookup.

## Rules for the official index

- No side effects at import; nothing outside `register` and the tools themselves.
- No assignment to `action_platform.*` attributes (monkey-patching): replace a slot or propose a hook in the core.
- `needs` says every host the plugin talks to and every environment variable it reads.
- Tests with `action_platform.testing.fixtures` (`TempCase`, `platform_repo`, `git`); the core's `tests/plugins/test_registry.py` shows how to drive a plugin through `Plugins([...])` without installing it.
- A pull request to `actionplatform/plugins-index` with the `<slug>.json`; `verified: true` is set by the reviewer.
