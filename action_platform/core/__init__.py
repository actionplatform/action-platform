"""Action Platform core.

- `manifest`: `Manifest` — platform.toml as an object
- `scaffold`: sources, catalog (`Matrix`), language, renderer, scaffolder (`Scaffolder`), publisher, installer (`Installer`)
- `flow`: `Repository` (one git clone), `GitFlow` (audit, branches, pull requests, hooks), `gitflow` (the rules)
- `release`: `Version`, `VersionFiles`, `Releaser` (plan → apply), `Deployer`, changelog
- `config`, `context`, `exception`, `action_platform` (the `ActionPlatform` facade)
"""
