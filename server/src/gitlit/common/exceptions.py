"""Common exceptions for the GitLit system."""


class GitLitError(Exception):
    """Base exception for all GitLit errors."""

    pass


class PatternError(GitLitError):
    """Pattern execution or validation error."""

    pass


class ValidationError(GitLitError):
    """Input validation error."""

    pass


class SystemError(GitLitError):
    """System-level error."""

    pass


class ConfigurationError(GitLitError):
    """Configuration error."""

    pass


class CommunicationError(GitLitError):
    """Communication or network error."""

    pass
