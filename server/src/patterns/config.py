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
    delta_time: float = 0.0
    parameters: Dict[str, Any] = field(default_factory=dict)
    cached_data: Dict[str, Any] = field(default_factory=dict)
    is_transitioning: bool = False
    frame_times: List[float] = field(default_factory=list)
    avg_frame_time: float = 0.0

    def get_normalized_time(self, time_ms: float) -> float:
        """Get normalized time (0-1) considering offset"""
        return ((time_ms + self.time_offset) / 1000.0) % 1.0

    def update(self, time_ms: float):
        """Update state for new frame"""
        current_time = time_ms / 1000.0  # Convert to seconds
        if self.last_frame_time > 0:
            self.delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        self.frame_count += 1

        # Update performance metrics
        self.frame_times.append(self.delta_time)
        if len(self.frame_times) > 60:  # Keep last 60 frames
            self.frame_times.pop(0)
        if self.frame_times:
            self.avg_frame_time = sum(self.frame_times) / len(self.frame_times)

    def reset(self):
        """Reset state to initial values"""
        self.time_offset = 0.0
        self.frame_count = 0
        self.last_frame_time = 0.0
        self.delta_time = 0.0
        self.parameters.clear()
        self.cached_data.clear()
        self.is_transitioning = False
        self.frame_times.clear()
        self.avg_frame_time = 0.0

    def cache_value(self, key: str, value: Any) -> None:
        """Cache a value for later use"""
        self.cached_data[key] = value
