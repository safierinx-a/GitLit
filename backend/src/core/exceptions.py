class ValidationError(Exception):
    """Pattern validation error"""

    pass


class PatternError(Exception):
    """Pattern execution error"""

    pass


class AudioError(Exception):
    """Audio processing error"""

    pass
