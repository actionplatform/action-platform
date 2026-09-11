# devtool — Plano de Projeto

CLI Python plugável para padronizar **init**, **release** e **deploy** em qualquer stack.

Baseado no `stackin-io/stackin-sdk-template/.code_quality/`, `specs/RELEASE_SPEC.md` e no estilo de código do `dotflow-io/dotflow`.

---

## 1. Escopo v0

Três comandos, nada mais:

```
devtool init <lang>       # bootstrap: .code_quality/, workflows, specs, devtool.toml
devtool release [level]   # bump semver, changelog, tag, release remoto
devtool deploy [--target] # dispara CI e/ou publica em targets configurados
```

---

## 2. Arquitetura de providers

Estilo herdado de `dotflow-io/dotflow`:

- `abc/` — ABCs por categoria.
- `providers/` — implementações concretas, **flat**, prefixadas pela categoria.
- `core/Config` central injeta providers no runtime.

| Categoria (ABC)   | Papel                          | Built-in v0                                     |
|-------------------|--------------------------------|-------------------------------------------------|
| **SourceHost**    | tag/release/PR remoto          | `source_github`                                 |
| **CIRunner**      | dispara/observa pipeline       | `ci_jenkins`                                    |
| **DeployTarget**  | publica artefato / promove app | `deploy_dokploy`                                |

Notifier fora — não integra `init`/`release`/`deploy`.

Injeção estilo dotflow:

```python
from devtool import DevTool, Config
from devtool.providers import SourceGithub, CIJenkins, DeployDokploy

config = Config(
    source_host=SourceGithub(repo="owner/my-project"),
    ci=[CIJenkins(url="https://jenkins.internal", job="my-project-build")],
    deploy=[DeployDokploy(url="https://dokploy.internal", app="my-project-prod")],
)

DevTool(config=config).release("patch")
```

Descoberta externa via `importlib.metadata` entry_points — plugin externo instala com `pip install devtool-<name>`:

```toml
[project.entry-points."devtool.ci_runner"]
jenkins = "devtool_jenkins:CIJenkins"

[project.entry-points."devtool.deploy_target"]
dokploy = "devtool_dokploy:DeployDokploy"
```

Todo texto (docstrings, logs, errors) escrito em **inglês**.

---

## 3. ABCs

Todos recebem `Context` — objeto único que atravessa pipeline (repo, versão, changelog, artifacts, env).

```python
# devtool/abc/source_host.py
class SourceHost(ABC):
    name: str
    def detect(self, remote_url: str) -> bool: ...
    def create_tag(self, ctx: "Context", tag: str) -> None: ...
    def create_release(
        self, ctx, tag, notes, assets=None, draft=False, prerelease=False
    ) -> "ReleaseRef": ...
    def open_pr(self, ctx, base, head, title, body) -> "PRRef": ...

# devtool/abc/ci_runner.py
class CIRunner(ABC):
    name: str
    def trigger(self, ctx, job, params) -> "RunRef": ...
    def wait(self, ctx, run, timeout=1800) -> "RunResult": ...
    def logs(self, ctx, run) -> Iterator[str]: ...

# devtool/abc/deploy_target.py
class DeployTarget(ABC):
    name: str
    def preflight(self, ctx) -> None: ...
    def deploy(self, ctx) -> "DeployResult": ...
    def rollback(self, ctx, to_version) -> None: ...
```

Provider não conhece outros — só ABC + `Context`.

---

## 4. Layout do repositório

Espelha estrutura `dotflow-io/dotflow`. **Implementado**.

```
devtool/
  pyproject.toml
  README.md
  PLAN.md
  LAST_VERSION
  devtool/
    __init__.py                 # __version__, re-exporta DevTool, Config, Context
    main.py                     # CLI entrypoint (script: devtool)
    logging.py
    settings.py
    abc/
      __init__.py
      source_host.py
      ci_runner.py
      deploy_target.py
    core/
      __init__.py
      devtool.py                # class DevTool
      config.py                 # class Config — injeta providers
      context.py                # Context, ReleaseRef, PRRef, RunRef, RunResult, DeployResult
      pipeline.py               # release() + deploy()
      versioning.py             # semver bump + LAST_VERSION
      changelog.py              # conventional commits -> CHANGELOG.md
      git.py                    # subprocess wrappers
      exception.py
      module.py                 # entry_points discovery
    providers/
      __init__.py
      source_github.py
      ci_jenkins.py
      deploy_dokploy.py
    cli/
      __init__.py
      setup.py                  # Typer app assembly
      commands/
        __init__.py
        init.py
        release.py
        deploy.py
    testing/
      __init__.py
    templates/
      code_quality/
        python/                 # copiado do stackin-sdk-template
      workflows/                # code-quality/test/integration/contract-conformance.yml
      specs/                    # RELEASE_SPEC/CODE_QUALITY_SPEC/API_CONTRACT.md
  tests/
    __init__.py
    test_versioning.py
    test_changelog.py
  examples/
    release_github_jenkins_dokploy.py
```

---

## 5. Comandos

### 5.1 `devtool init <lang>`

Bootstrap. Passos:

1. Copia `templates/code_quality/<lang>/` → `.code_quality/<lang>/`.
2. Copia `templates/workflows/*.yml` → `.github/workflows/`.
3. Copia `templates/specs/*.md` → `specs/`.
4. Gera `devtool.toml` base.
5. Cria `LAST_VERSION` = `0.1.0` se ausente.

Flags: `--force`, `--minimal`.

### 5.2 `devtool release [level]`

Level = `patch` | `minor` | `major` | `<X.Y.Z>`.

Pipeline (`core/pipeline.py::release`):

```
1. build Context (remote, branch, current_version)
2. guard: working tree clean
3. bump version
4. render CHANGELOG from conventional commits since latest tag
5. if dry_run: return
6. write LAST_VERSION + CHANGELOG.md
7. commit + tag + push + push_tag
8. source_host.create_release()
9. for ci in config.ci: trigger() + wait()
```

Flags: `--dry-run`.

### 5.3 `devtool deploy [--target NAME]`

Pipeline (`core/pipeline.py::deploy`):

```
1. build Context
2. resolve targets (all or filtered by --target)
3. for t: preflight() + deploy() (skip deploy if dry_run)
```

Flags: `--target NAME`, `--dry-run`.

---

## 6. Config do projeto — `devtool.toml`

```toml
[project]
name = "my-project"
language = "python"

[source_host]
kind = "github"
repo = "owner/my-project"

[release]
strategy = "semver"
changelog = "conventional"

[[ci]]
kind = "jenkins"
url  = "https://jenkins.internal"
job  = "my-project-build"

[[deploy]]
kind = "dokploy"
url  = "https://dokploy.internal"
app  = "my-project-prod"
```

Auth via env vars:

- `DEVTOOL_GITHUB_TOKEN` / `GH_TOKEN`
- `DEVTOOL_GITLAB_TOKEN` / `GITLAB_TOKEN`
- `DEVTOOL_JENKINS_USER` / `DEVTOOL_JENKINS_TOKEN`
- `DEVTOOL_DOKPLOY_TOKEN`

Hidratação completa do `Config` a partir do TOML (`ci`/`deploy`/`source_host`) fica p/ v0.2. v0.1 só lê `[project]`.

---

## 7. Stack técnica

- **Runtime**: Python 3.10+
- **CLI**: `typer`
- **Config**: `tomllib` (nativo)
- **HTTP**: `httpx`
- **Logging**: `rich` via `devtool/logging.py`
- **Testes**: `pytest`
- **Package**: `poetry`
- **Dist**: PyPI + `pipx install devtool`

---

## 8. Roadmap

**v0.1 — MVP (atual, esqueleto pronto)**
- Núcleo: `abc/`, `core/`, `providers/`, `cli/`
- Providers: `source_github`, `ci_jenkins`, `deploy_dokploy`
- Comandos: `init python`, `release`, `deploy`
- Templates: python + workflows + specs
- Testes: versioning + changelog

**v0.2 — Config completo**
- Hidratar `[[ci]]`, `[[deploy]]`, `[source_host]` do TOML.
- `providers/source_gitlab`, `providers/ci_github_actions`.
- Templates: go, node.

**v0.3 — Mais targets**
- `providers/deploy_pypi`, `providers/deploy_docker`.
- Rollback automático em fail.

**v0.4 — Extensibilidade**
- Docs de escrita de plugin externo.
- Repo exemplo `devtool-plugin-example`.
- `devtool plugins list`.

---

## 9. Convenções herdadas

- Branches: `feature/ISSUE-N`, `release/vX.Y.Z`, `hotfix/vX.Y.Z` (git-flow skill).
- Commits: `<icon> <type>: <msg> (#N)` — ex.: `:sparkles: feat: add release pipeline (#12)`.
- Sem comentários em código.
- Docstrings/logs/errors sempre em **inglês**.

---

## 10. API pública — estilo dotflow

`devtool/__init__.py`:

```python
"""Devtool __init__ module."""

__version__ = "0.1.0"
__description__ = "🛠️ Devtool padroniza init, release e deploy."

from .core.config import Config
from .core.context import Context
from .core.devtool import DevTool

__all__ = ["Config", "Context", "DevTool"]
```

Uso programático:

```python
from devtool import DevTool, Config
from devtool.providers import SourceGithub, CIJenkins, DeployDokploy

config = Config(
    source_host=SourceGithub(repo="owner/my-project"),
    ci=[CIJenkins(url="...", job="my-project-build")],
    deploy=[DeployDokploy(url="...", app="my-project-prod")],
)

tool = DevTool(config=config)
tool.release("patch")
tool.deploy(target="dokploy")
```

Uso via CLI:

```bash
devtool init python
devtool release patch
devtool deploy --target dokploy
```

Ambos consomem mesma `Config` — CLI hidrata a partir de `devtool.toml`, código passa direto.

---

## 11. Status atual

- [x] `pyproject.toml`, `LAST_VERSION`, `README.md`
- [x] `abc/` (SourceHost, CIRunner, DeployTarget)
- [x] `core/` (Context, Config, DevTool, pipeline, versioning, changelog, git, module, exception)
- [x] `providers/` (source_github, ci_jenkins, deploy_dokploy)
- [x] `cli/` + `main.py` (init, release, deploy) — Typer app funcional
- [x] `templates/code_quality/python/` copiado do stackin
- [x] `templates/workflows/*.yml` + `templates/specs/*.md`
- [x] `tests/test_versioning.py`, `tests/test_changelog.py` — 7 passing
- [x] `examples/release_github_jenkins_dokploy.py`
- [ ] `Config.from_toml` completo (hidrata providers)
- [ ] `.pre-commit-config.yaml` + `.code_quality/` próprio
- [ ] Templates go/node/rust/...
- [ ] Docs `mkdocs`
