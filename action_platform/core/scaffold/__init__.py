"""Templates and the projects made from them, one module per role.

- `sources`: where templates come from (`TemplateSource`, `LocalTemplateStore` checkouts)
- `catalog`: what templates exist (`Matrix`, `Leaf`, `Cloud`, `Service`, `load_matrix`)
- `language`: which language a repository is written in (`LanguageDetector`)
- `renderer`: how a template turns into files (`TemplateRenderer`)
- `scaffolder`: generate a project, overlay clouds and services (`Scaffolder`)
- `publisher`: push a generated project to its source host (`Publisher`)
- `installer`: bring an existing repository onto the platform (`Installer`)
"""
