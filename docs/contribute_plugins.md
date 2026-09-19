# Writing a plugin

Start from the template repository [actionplatform/apx-example](https://github.com/actionplatform/apx-example); [actionplatform/apx-aws-lambda](https://github.com/actionplatform/apx-aws-lambda) is a complete one (deploy target, overlay, CLI, tools).

## Names

| | Format | Example |
|---|---|---|
| repository | `actionplatform/apx-example-<slug>` or `<you>/apx-<slug>` | `apx-aws-lambda` |
| PyPI | `apx-<slug>` | `apx-aws-lambda` |
| module | `apx_<slug>` | `apx_aws_lambda` |
| slug | `[a-z][a-z0-9-]*`, 2–32 chars; not `core platform official admin system test internal` | `aws-lambda` |

## The package

```toml
[project]
name = "apx-aws-lambda"
dependencies = ["action-platform>=0.16"]

[project.entry-points."action_platform.plugins"]
aws-lambda = "apx_aws_lambda:AwsLambdaPlugin"

[project.entry-points."action_platform.deploy_target"]
"aws/lambda" = "apx_aws_lambda.lambda_:LambdaTarget"

[project.entry-points."action_platform.release_strategy"]
calver = "apx_calver:Calver"

[project.entry-points."action_platform.changelog"]
plain = "apx_calver:Plain"
```

`action_platform.plugins` is the one group every plugin declares; the others are optional and name providers `platform.toml` picks (`[deploy] target`, `[release] strategy`, `[release] changelog`, `[source_host] kind`).

## The class

```python
from pathlib import Path

from action_platform.abc import Option, Plugin, Surface


class AwsLambdaPlugin(Plugin):
    slug = "aws-lambda"
    name = "AWS Lambda"
    description = "Deploy to AWS Lambda with SAM"
    min_core = "0.16"
    needs = ["env: AWS_PROFILE or AWS_ACCESS_KEY_ID", "tool: sam, aws"]
    options = [
        Option("proxy_url", "Deploy proxy URL", "url", help="The deploy proxy in your AWS account.", required=True),
    ]

    @property
    def overlays(self) -> Path:
        return Path(__file__).parent / "overlays"

    def register(self, surface: Surface) -> None:
        if surface.mcp is not None:
            @surface.mcp.tool()
            def logs(function: str, minutes: int = 15) -> dict:
                ...

        if surface.cli is not None:
            surface.cli.add_typer(cli.app, name="aws-lambda")

        surface.core.replace("deployer", RetryingDeployer)

    def after_deploy(self, results) -> None:
        ...
```

- `register` only declares. No I/O, no threads, no connections at import or in `register`; the tools and commands do the work when called.
- `surface.mcp.tool()` is the core's own decorator: the tool comes out as `aws_lambda_logs` (slug with hyphens as underscores, then the name — MCP clients accept `[A-Za-z0-9_-]` only), gets input and output schemas from the annotations (return a pydantic model or a typed dict), and a raised `ActionPlatformError` reaches the model as the tool's error text. While the plugin is disabled the tool answers with an error instead of running.
- `surface.core` is the wiring. `replace(slot, cls)` puts a **subclass** of the core's class in a slot; anything else is refused. Slots: `gitflow_rules` (`core.flow.gitflow.Rules`), `gitflow` (`core.flow.workflow.GitFlow`), `releaser` (`core.release.release.Releaser`), `deployer` (`core.release.deploy.Deployer`), `installer` (`core.scaffold.install.Installer`), `scaffolder` (`core.scaffold.generate.Scaffolder`). Disabling the plugin restores what it replaced.
- `overlays` points at a directory shaped like the templates repository: an `index.json` with `clouds` (`id`, `description`, `types`, `languages`) and one `cloud/<name>/` directory per cloud. A directory with a `cookiecutter.json` is rendered like the official overlays; without one it is copied as it is, file over file — enough for most plugins. Together with a `DeployTarget` of the same name, that is a complete cloud.
- `surface.options` is the plugin's key/value store — `get(key, default)`, `set(key, value)` (anything JSON carries), `delete(key)`, `all()`. A file per plugin on a machine, a table on the hosted platform; the plugin never cares which.
- `options` declares the settings a user fills in: `Option(key, label, kind, help, required)` with `kind` one of `text`, `url`, `secret`, `bool`. The hosted platform draws the form behind **Configure** on the plugin's card under **Plugins** from this list and stores each value under `key`, per organization; the CLI reads the same keys from the file. A plugin with no `options` shows up as installed and nothing else. `name` is the title shown; the slug when empty.
- `after_release(ctx)`, `after_deploy(results)`, `after_pull_request(ref)` run after the real thing; an exception is logged and never undoes the action.

## Providers

| ABC | Entry-point group | Picked by |
|---|---|---|
| `abc.DeployTarget` — `preflight`, `create`, `deploy`, `switch_traffic`, `rollback`, `diagnose`, `delete` for a target the platform runs; `verify(version)`, `url(version)` for every kind; `readiness(ctx) -> list[Check]` for what the target can verify about a deploy of `ctx.next_version` to `ctx.stage` without building or changing anything — credentials, permissions, the destination's state — each a `Check(id, ok, detail, level, severity, fix)`; an `error` severity blocks the deploy, a `warning` informs, a raised `DeployError` becomes one failed check | `action_platform.deploy_target` | `[deploy] target`, `[[deploy.targets]] kind` |
| `abc.CIRunner` — `test`, `runs(job, limit)`, `run`, `start(job, ref)`, and `trigger`, `wait`, `logs` where the system allows it | `action_platform.ci_runner` | `[ci]`; a CI host's `kind` on the hosted platform |
| `abc.SourceHost` | `action_platform.source_host` | `[source_host] kind` |
| `abc.ReleaseStrategy` — `next(current, level, prerelease, taken)`, `is_prerelease` | `action_platform.release_strategy` | `[release] strategy` |
| `abc.ChangelogRenderer` — `render(version, commits)` | `action_platform.changelog` | `[release] changelog` |

A disabled plugin's providers disappear from every lookup.

Log through `self.logger` (the plugin's own logger, wired at load to the platform's job log) or `action_platform.logging.logger`; a logger of your own named after your package works too — every plugin's package is attached when it is discovered. Long commands should stream: run them through `action_platform.core.process.stream(args, cwd, env)` — every line reaches whoever follows the job (the web's run log, `action-platform logs -f`) as it appears, and the tail comes back for the error — or `emit(line)` from `action_platform.logging` for lines of your own. Output the platform never sees is output nobody can debug.

`readiness` is optional — the default answers nothing and the release is checked statically only. Keep it read-only and cheap: it runs on the worker right after every release, for every stage, and again whenever someone asks. Name checks `<area>.<what>` (`aws.permissions`, `stack.state`, `destination.version`), put the way out in `fix`, and never let it build — that is what `deploy` is for. `apx-aws-lambda`'s `LambdaTarget.readiness` is the reference: tooling, template present, stack name, credentials, stack state, `iam:SimulatePrincipalPolicy` for the actions the template needs, `sam validate --lint`.

## Rules for the official index

- No side effects at import; nothing outside `register` and the tools themselves.
- No assignment to `action_platform.*` attributes (monkey-patching): replace a slot or propose a hook in the core.
- `needs` says every host the plugin talks to and every environment variable it reads.
- Tests with `action_platform.testing.fixtures` (`TempCase`, `platform_repo`, `git`); the core's `tests/plugins/test_registry.py` shows how to drive a plugin through `Plugins([...])` without installing it.
- A pull request to `actionplatform/plugins-index` with the `<slug>.json`; `verified: true` is set by the reviewer.
