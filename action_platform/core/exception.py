"""Action Platform exceptions."""


class ActionPlatformError(Exception):
    """Base exception."""


class ConfigError(ActionPlatformError):
    """Invalid or missing configuration."""


class ProviderError(ActionPlatformError):
    """Provider operation failed."""


class ReleaseError(ActionPlatformError):
    """Release pipeline failed."""


class DeployError(ActionPlatformError):
    """Deploy pipeline failed."""


class TemplateError(ActionPlatformError):
    """Template lookup or generation failed."""
