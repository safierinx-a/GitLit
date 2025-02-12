"""Common exceptions used across the system."""


class ValidationError(Exception):
    """Validation error for configuration and parameters"""

    pass


class PatternError(Exception):
    """Pattern execution error"""

    pass


class SystemError(Exception):
    """System-level error"""

    pass
