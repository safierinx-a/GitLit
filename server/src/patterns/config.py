from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .modifiers.base import BaseModifier


@dataclass
class PatternConfig:
    """Configuration for a pattern and its modifiers"""

    pattern_type: str
    parameters: Dict[str, Any]
    modifiers: List[tuple[BaseModifier, Dict[str, Any]]] = field(default_factory=list)

    def __init__(
        self,
        pattern_type: str,
        parameters: Dict[str, Any],
        modifiers: Optional[List[tuple[BaseModifier, Dict[str, Any]]]] = None,
    ):
        self.pattern_type = pattern_type
        self.parameters = parameters
        self.modifiers = modifiers or []


@dataclass
class PatternState:
    """Maintains pattern state between frames"""

    time_offset: float = 0.0
    frame_count: int = 0
    last_frame_time: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    cached_data: Dict[str, Any] = field(default_factory=dict)

    def get_normalized_time(self, time_ms: float) -> float:
        """Get normalized time (0-1) considering offset"""
        return ((time_ms + self.time_offset) / 1000.0) % 1.0

    def update(self, time_ms: float):
        """Update state for new frame"""
        self.frame_count += 1
        self.last_frame_time = time_ms
