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
        Option("role_arn", "Deploy role ARN", "text", help="The deploy role of your connected AWS account.", required=True),
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
- `surface.core` is the wiring. `replace(slot, cls)` puts a **subclass** of the core's class in a slot; anything else is refused. Slots: `gitflow_rules` (`core.flow.gitflow.Rules`), `gitflow` (`core.flow.workflow.GitFlow`), `releaser` (`core.release.release.Releaser`), `deployer` (`core.release.deploy.Deployer`), `installer` (`core.scaffold.installer.Installer`), `scaffolder` (`core.scaffold.scaffolder.Scaffolder`). Disabling the plugin restores what it replaced.
- `overlays` points at a directory shaped like the templates repository: an `index.json` with `clouds` (`id`, `description`, `types`, `languages`) and one `cloud/<name>/` directory per cloud. A directory with a `cookiecutter.json` is rendered like the official overlays; without one it is copied as it is, file over file — enough for most plugins. Together with a `DeployTarget` of the same name, that is a complete cloud.
- `surface.options` is the plugin's key/value store — `get(key, default)`, `set(key, value)` (anything JSON carries), `delete(key)`, `all()`. A file per plugin on a machine, a table on the hosted platform; the plugin never cares which.
- `options` declares the settings a user fills in: `Option(key, label, kind, help, required)` with `kind` one of `text`, `url`, `secret`, `bool`. The hosted platform draws the form behind **Configure** on the plugin's card under **Plugins** from this list and stores each value under `key`, per organization; the CLI reads the same keys from the file. A plugin with no `options` shows up as installed and nothing else. `name` is the title shown; the slug when empty.
- `after_release(ctx)`, `after_deploy(results)`, `after_pull_request(ref)` run after the real thing; an exception is logged and never undoes the action.
- `access(options)` brings access on the plugin's service — see [Access](#access).

## Providers

| ABC | Entry-point group | Picked by |
|---|---|---|
| `abc.DeployTarget` — `preflight`, `create`, `deploy`, `switch_traffic`, `rollback`, `diagnose`, `delete` for a target the platform runs; `verify(version)`, `url(version)` for every kind; `readiness(ctx) -> list[Check]` for what the target can verify about a deploy of `ctx.next_version` to `ctx.stage` without building or changing anything — credentials, permissions, the destination's state — each a `Check(id, ok, detail, level, severity, fix)`; an `error` severity blocks the deploy, a `warning` informs, a raised `DeployError` becomes one failed check; `ctx.observed` is true when someone else deploys the target and the platform only records it, and its checks then never block | `action_platform.deploy_target` | `[deploy] target`, `[[deploy.targets]] kind` |
| `abc.CIRunner` — `test`, `runs(job, limit)`, `run`, `start(job, ref)`, and `trigger`, `wait`, `logs` where the system allows it | `action_platform.ci_runner` | `[ci]`; a CI host's `kind` on the hosted platform |
| `abc.SourceHost` | `action_platform.source_host` | `[source_host] kind` |
| `abc.ReleaseStrategy` — `next(current, level, prerelease, taken)`, `is_prerelease` | `action_platform.release_strategy` | `[release] strategy` |
| `abc.ChangelogRenderer` — `render(version, commits)` | `action_platform.changelog` | `[release] changelog` |

A disabled plugin's providers disappear from every lookup.

## Access

A plugin that owns a service can also own who has access to it. It returns an `AccessProvider` from `Plugin.access(options)`, and the platform's [service access](concept_service_access.md) — `access_audit`, `access_sync`, `access_grant`, `access_revoke`, `access_offboard`, `access_who` — runs over every installed plugin that does.

```python
from action_platform.abc import AccessProvider, Option, Plugin
from action_platform.core.service_access import AccessError, Grant, Http, Op


class VaultAccess(AccessProvider):
    name = "vault"
    levels = {"org": ("member", "admin"), "repo": ("read", "write")}

    def __init__(self, url: str, token: str) -> None:
        self.http = Http("vault", url, {"authorization": f"Bearer {token}"})

    def read(self) -> list[Grant]:
        return [
            Grant("vault", m["login"], "org", m["role"])
            for m in self.http.pages("members")
        ]

    def apply(self, op: Op) -> None:
        ...


class VaultPlugin(Plugin):
    slug = "vault"
    options = [Option("url", "URL", "url"), Option("token", "Token", "secret")]

    def access(self, options):
        if not options.get("url"):
            return None

        if not options.get("token"):
            raise AccessError("vault: set the token option")

        return VaultAccess(options.get("url"), options.get("token"))
```

| Member | Contract |
|---|---|
| `name` | the service, as tools and the mapping name it; one provider per service |
| `levels` | resource kind → levels, lowest first; a resource is `<kind>` or `<kind>/<name>` |
| `read()` | every grant the service holds today, `(service, account, resource, level)`; accounts compare without case |
| `apply(op)` | one `add`, `change` or `remove`; raise `AccessError` when the service refuses — the message names the service and the call, never a credential |
| `companions(resource)` | grants the service needs beside this one to be usable (a repository grant needs organization membership); `access_grant` adds the missing ones |
| `expand(grants)` | the grants the service implies alongside the wanted ones, so they are not reported as drift |
| `guard(ops, live)` | changes refused before anything is sent, with the reason — at least: never the last administrator; a refused `org`/`global` change holds every other change of that account |
| `order(op)` | the order changes are sent in; by default organization-wide adds first and removes last |

`Http(service, base, headers)` is the JSON client the bundled plugins share: `call(method, path, body=…, query=…, form=…, ok=…)` answers the decoded body and raises `AccessError` on any status of 400 or more that `ok` does not list; `pages(path)` follows `Link: rel="next"`; `text(path, tail_lines=None)` reads a plain-text body (a console log) as a stream, whole or only its last `tail_lines` lines. An error message names the service, the method and the path, never a header; an HTML error page shows up only as its `<title>`.

`access(options)` reads **only** `options`: on the hosted platform they are the calling organization's values of the plugin (secrets opened for that call), so an environment variable would leak one organization's credential into another's. Return `None` while the options do not configure the service and raise `AccessError` naming the missing key when they half do; the audit shows it as a failed service. Keep it cheap — it runs on every access call. Test with `action_platform.testing.access` (`MemoryDirectory`, and `MemoryProvider` as a reference) and the core's `Access`: the first sync imports and changes nothing, a second one is a no-op.

Log through `self.logger` (the plugin's own logger, wired at load to the platform's job log) or `action_platform.logging.logger`; a logger of your own named after your package works too — every plugin's package is attached when it is discovered. Long commands should stream: run them through `action_platform.core.process.stream(args, cwd, env)` — every line reaches whoever follows the job (the web's run log, `action-platform logs -f`) as it appears, and the tail comes back for the error — or `emit(line)` from `action_platform.logging` for lines of your own. Output the platform never sees is output nobody can debug.

`readiness` is optional — the default answers nothing and the release is checked statically only. Keep it read-only and cheap: it runs on the worker right after every release, for every stage, and again whenever someone asks. Name checks `<area>.<what>` (`aws.permissions`, `stack.state`, `destination.version`), put the way out in `fix`, and never let it build — that is what `deploy` is for. `apx-aws-lambda`'s `LambdaTarget.readiness` is the reference: tooling, template present, stack name, credentials, stack state, `iam:SimulatePrincipalPolicy` for the actions the template needs, `sam validate --lint`.

## Rules for the official index

- No side effects at import; nothing outside `register` and the tools themselves.
- No assignment to `action_platform.*` attributes (monkey-patching): replace a slot or propose a hook in the core.
- `needs` says every host the plugin talks to and every environment variable it reads.
- Tests with `action_platform.testing.fixtures` (`TempCase`, `platform_repo`, `git`); the core's `tests/plugins/test_registry.py` shows how to drive a plugin through `Plugins([...])` without installing it.
- A pull request to `actionplatform/plugins-index` with the `<slug>.json`; `verified: true` is set by the reviewer.
