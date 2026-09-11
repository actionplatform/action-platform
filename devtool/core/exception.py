"""Devtool exceptions."""


class DevtoolError(Exception):
    """Base exception."""


class ConfigError(DevtoolError):
    """Invalid or missing configuration."""


class ProviderError(DevtoolError):
    """Provider operation failed."""


class ReleaseError(DevtoolError):
    """Release pipeline failed."""


class DeployError(DevtoolError):
    """Deploy pipeline failed."""
