"""Deploy targets the core knows without a plugin: registries a version is published to by someone else's pipeline. They verify and point; they never deploy."""

from action_platform.providers.deploy.docker import DeployDocker
from action_platform.providers.deploy.go import DeployGo
from action_platform.providers.deploy.npm import DeployNpm
from action_platform.providers.deploy.packagist import DeployPackagist
from action_platform.providers.deploy.pypi import DeployPypi

BUILTIN_DEPLOY_TARGETS: dict[str, type] = {
    "pypi": DeployPypi,
    "docker": DeployDocker,
    "npm": DeployNpm,
    "packagist": DeployPackagist,
    "go": DeployGo,
}

__all__ = [
    "BUILTIN_DEPLOY_TARGETS",
    "DeployDocker",
    "DeployGo",
    "DeployNpm",
    "DeployPackagist",
    "DeployPypi",
]
