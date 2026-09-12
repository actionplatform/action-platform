# action-platform

Standardize **init**, **release**, and **deploy** across any stack.

Pluggable CLI — SourceHost (GitHub, GitLab), CIRunner (Jenkins, GitHub Actions), and DeployTarget (PyPI, Docker, Dokploy) are interchangeable providers.

## Install

```bash
pipx install action-platform
```

## Commands

```bash
action-platform init python
action-platform release patch
action-platform deploy --target dokploy
```

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
