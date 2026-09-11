# devtool

Standardize **init**, **release**, and **deploy** across any stack.

Pluggable CLI — SourceHost (GitHub, GitLab), CIRunner (Jenkins, GitHub Actions), and DeployTarget (PyPI, Docker, Dokploy) are interchangeable providers.

## Install

```bash
pipx install devtoolcli
```

## Commands

```bash
devtool init python
devtool release patch
devtool deploy --target dokploy
```

## Programmatic API

```python
from devtool import DevTool, Config
from devtool.providers import SourceGithub, CIJenkins, DeployDokploy

config = Config(
    source_host=SourceGithub(repo="owner/my-project"),
    ci=[CIJenkins(url="https://jenkins.internal", job="my-job")],
    deploy=[DeployDokploy(url="https://dokploy.internal", app="my-project-prod")],
)

DevTool(config=config).release("patch")
```
