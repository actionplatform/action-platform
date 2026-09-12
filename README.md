# action-platform

Standardize **init**, **release**, and **deploy** across any stack.

Pluggable CLI — SourceHost (GitHub, GitLab), CIRunner (Jenkins, GitHub Actions), and DeployTarget (PyPI, Docker, Dokploy) are interchangeable providers.

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
action-platform deploy --target dokploy
```

Templates come from [actionplatform/templates](https://github.com/actionplatform/templates), cached in `~/.cache/action-platform/templates` (`--update` refreshes it). Point `ACTION_PLATFORM_TEMPLATES` to a local checkout to develop templates.

## Programmatic API

```python
from action_platform import ActionPlatform, Config
from action_platform.providers import SourceGithub, CIJenkins, DeployDokploy

config = Config(
    source_host=SourceGithub(repo="owner/my-project"),
    ci=[CIJenkins(url="https://jenkins.internal", job="my-job")],
    deploy=[DeployDokploy(url="https://dokploy.internal", app="my-project-prod")],
)

ActionPlatform(config=config).release("patch")
```
