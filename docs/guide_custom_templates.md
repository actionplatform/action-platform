# Add your own templates

Give your organization its own starting points: a reference service everyone copies, or a full catalog of templates next to the official one. The model behind this page is in [Templates](concept_templates.md).

## Choose the kind of repository

| You have | It becomes | What the platform does on creation |
|---|---|---|
| a plain repository (a starter, a reference service) | **one template** | copies the tree at the chosen branch or tag, detects the language (`pyproject.toml`, `go.mod`, `package.json`, …), keeps an existing `platform.toml` (renaming the project) or adds `platform.toml`, `.code_quality/`, CI files and hooks the way `action-platform install` does |
| a repository with `index.json` at its root | **a catalog** | reads it with the official layout: `projects/`, `cloud/`, `service/` |

A plain repository needs no change. A catalog needs the layout below.

## Build a catalog

```
index.json
projects/<type>/<stack>/<template>/
    cookiecutter.json
    {{cookiecutter.project_slug}}/
cloud/<name>/
service/<name>/
```

`index.json` lists every entry. Each list holds objects with an `id`:

```json
{
  "projects": [
    {
      "id": "web/python/orders-service",
      "type": "web",
      "stack": "python",
      "template": "orders-service",
      "language": "python",
      "framework": "FastAPI",
      "description": "Our FastAPI service with auth and tracing",
      "default": true
    }
  ],
  "clouds": [],
  "services": []
}
```

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | string | yes | — | `<type>/<stack>/<template>`; `type`, `stack` and `template` fall back to its parts |
| `type`, `stack`, `template` | string | no | parts of `id` | where the template sits in the Type › Stack › Template choice |
| `language` | string | no | `""` | the template's language, shown in the catalog |
| `framework` | string | no | `""` | label shown on the card |
| `description` | string | no | `""` | shown in the catalog and the wizard |
| `default` | boolean | no | `false` | the stack's default template |
| `icons` | object | no | — | `{"language": "<path>", "framework": "<path>"}` inside the repository |

A cloud entry takes `id`, `description`, `types` and `languages` (empty means all) and lives under `cloud/<id>/`. A service entry takes `id`, `description` and `providers`. Optional `types` and `stacks` lists label the choices (`id`, `label`, `description`).

`cookiecutter.json` declares the values the wizard and `init` fill: `project_name`, `project_slug`, `description`, `package_name`, `github_owner`, `author`, `license`, `source_host` and `ci`. Copy the one of a template in the [official repository](https://github.com/actionplatform/templates) as a starting point.

## Respect the sandbox

Templates from any repository other than the official one render text only:

- A template with a `hooks/` directory (`pre_prompt`, `pre_gen_project`, `post_gen_project`) is refused.
- `_extensions`, `_jinja2_env_vars`, `template` or `templates` in `cookiecutter.json` is refused.
- A symlink must point at a file inside the same template.
- `{% include %}` reads only files of the template itself.

Every template renders in a separate process with a sandboxed Jinja environment and no platform secret in its environment. [Templates › How a template is rendered](concept_templates.md#how-a-template-is-rendered).

## Register the repository

**Web app.** Go to **Templates → Template repositories → Add repository** and give a name, the git URL and a branch or tag. Owners and admins only. Private repositories are cloned with the organization's connected source host. Names are unique per organization, and `official` is reserved.

Every template, cloud and service then shows its source in the catalog, and the **New app** wizard offers them. A repository that cannot be cloned shows as *Unavailable* with the error, and the others stay available.

**CLI.** Pass the repository on each call:

```bash
action-platform init --list --source https://github.com/acme/templates.git@main
action-platform init web python orders-service --name billing --source https://github.com/acme/templates.git@main
```

`cloud set` and `service add` take the same `--source`.

**MCP.** On a local repository, `list_matrix(source="url[@ref]")`, then the same `source` on `init_project`, `cloud_set` and `service_add`. On a hosted platform, `list_matrix` already merges the organization's repositories; pass the source's `name` to `init_app`, `set_cloud` and `add_service`.

## Update a template

The platform fetches the repository with the organization's current credentials on every read, so a change merged on the registered branch shows on the next read. Apps created earlier keep the files they were created with.

## Related

[Templates](concept_templates.md) · [Project scaffolding](usecase_scaffolding.md) · [CLI › Scaffold](use_cli.md#scaffold)
