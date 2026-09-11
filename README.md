# devtool

🛠️ Devtool padroniza **init**, **release** e **deploy** em qualquer stack.

CLI plugável — SourceHost (GitHub, GitLab), CIRunner (Jenkins, GitHub Actions), DeployTarget (PyPI, Docker, Dokploy) e Notifier (Slack, Webhook) são providers intercambiáveis.

## Instalação

```bash
pipx install devtool
```

## Comandos

```bash
devtool init python
devtool release patch
devtool deploy --target dokploy
```

## API programática

```python
from devtool import DevTool, Config
from devtool.providers import SourceGithub, CIJenkins, DeployDokploy, NotifySlack

config = Config(
    source_host=SourceGithub(repo="FernandoCelmer/owline-api"),
    ci=[CIJenkins(url="https://jenkins.internal", job="owline-api-build")],
    deploy=[DeployDokploy(url="https://dokploy.internal", app="owline-api-prod")],
    notify=[NotifySlack(webhook_env="SLACK_WEBHOOK")],
)

DevTool(config=config).release("patch")
```

Ver [PLAN.md](PLAN.md) para arquitetura completa.
