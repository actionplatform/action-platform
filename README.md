# action-platform

Standardize **init**, **release**, and **deploy** across any stack.

Pluggable CLI — SourceHost, CIRunner and DeployTarget are abstract contracts; providers plug in through entry points.

## Install

```bash
pipx install action-platform
```

## Commands

```bash
action-platform init                        # interactive: type → stack → template → name → ci
action-platform init web python             # default template for the stack
action-platform init web python fastapi --name "My API" --ci gitlab
action-platform init web python fastapi --cloud aws/lambda
action-platform init --list                 # show projects and clouds
action-platform cloud set docker            # apply a deploy overlay to an existing project
action-platform cloud list                  # clouds compatible with this project
action-platform release patch
action-platform deploy                      # ships to the [deploy] target in platform.toml
action-platform rollback | diagnose | destroy
```

Templates come from [actionplatform/templates](https://github.com/actionplatform/templates), cached in `~/.cache/action-platform/templates` (`--update` refreshes it). Point `ACTION_PLATFORM_TEMPLATES` to a local checkout to develop templates.

## Programmatic API

```python
from action_platform import ActionPlatform, Config
from action_platform.providers import SourceGithub

config = Config(source_host=SourceGithub(repo="owner/my-project"))
ActionPlatform(config=config).release("patch")
```

Deploy targets are resolved from `[deploy] target` in `platform.toml` through the `action_platform.deploy_target` entry-point group — install a provider package to enable one.
