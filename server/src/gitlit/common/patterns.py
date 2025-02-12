"""Common pattern utilities and definitions."""

from enum import Enum
from typing import Set


class PatternCategory(str, Enum):
    """Categories of patterns"""

    STATIC = "static"
    MOVING = "moving"
    PARTICLE = "particle"
    OTHER = "other"


# Pattern category definitions
STATIC_PATTERNS: Set[str] = {"solid", "gradient"}
MOVING_PATTERNS: Set[str] = {"wave", "rainbow", "chase", "scan"}
PARTICLE_PATTERNS: Set[str] = {"twinkle", "meteor", "breathe"}


def determine_pattern_category(pattern_name: str) -> PatternCategory:
    """Determine pattern category based on name"""
    if pattern_name in STATIC_PATTERNS:
        return PatternCategory.STATIC
    elif pattern_name in MOVING_PATTERNS:
        return PatternCategory.MOVING
    elif pattern_name in PARTICLE_PATTERNS:
        return PatternCategory.PARTICLE
    return PatternCategory.OTHER
