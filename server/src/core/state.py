import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class PatternState:
    """Maintains pattern state between frames"""

    # Timing
    time_offset: float = 0.0
    frame_count: int = 0
    last_frame_time: float = 0.0
    delta_time: float = 0.0
    start_time: float = field(default_factory=time.time)

    # Pattern State
    parameters: Dict[str, Any] = field(default_factory=dict)
    cached_data: Dict[str, Any] = field(default_factory=dict)
    is_transitioning: bool = False

    # Performance Metrics
    frame_times: list = field(default_factory=list)  # Last N frame times
    avg_frame_time: float = 0.0

    def update(self, time_ms: float) -> None:
        """Update state for new frame"""
        current_time = time.time()

        # Update timing
        if self.last_frame_time:
            self.delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        self.frame_count += 1

        # Update performance metrics
        self.frame_times.append(self.delta_time)
        if len(self.frame_times) > 60:  # Keep last 60 frames
            self.frame_times.pop(0)
        self.avg_frame_time = sum(self.frame_times) / len(self.frame_times)

    def get_normalized_time(self, time_ms: float) -> float:
        """Get normalized time (0-1) considering offset"""
        return ((time_ms + self.time_offset) / 1000.0) % 1.0

    def cache_value(self, key: str, value: Any) -> None:
        """Cache a value for use between frames"""
        self.cached_data[key] = value

    def get_cached(self, key: str, default: Any = None) -> Any:
        """Get a cached value"""
        return self.cached_data.get(key, default)

    def clear_cache(self) -> None:
        """Clear cached data"""
        self.cached_data.clear()

    def reset(self) -> None:
        """Reset state"""
        self.frame_count = 0
        self.last_frame_time = 0.0
        self.delta_time = 0.0
        self.time_offset = 0.0
        self.start_time = time.time()
        self.clear_cache()
