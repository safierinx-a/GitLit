"""Pattern system for LED control"""

from .base import BasePattern, Parameter, ModifiableAttribute
from .engine import PatternEngine
from .config import PatternConfig
from .transitions import CrossFadeTransition, InstantTransition

__all__ = [
    "BasePattern",
    "Parameter",
    "ModifiableAttribute",
    "PatternEngine",
    "PatternConfig",
    "CrossFadeTransition",
    "InstantTransition",
]
