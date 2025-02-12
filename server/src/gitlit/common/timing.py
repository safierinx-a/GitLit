"""Common timing utilities"""

from dataclasses import dataclass, field
import time
from typing import Optional


@dataclass
class TimeState:
    """Timing state for pattern generation"""

    current_time: float = 0.0
    delta_time: float = 0.0
    start_time: float = field(default_factory=time.perf_counter)
    last_update: Optional[float] = None

    def update(self, current_time: Optional[float] = None) -> None:
        """Update timing state"""
        if current_time is None:
            current_time = time.perf_counter()

        self.current_time = current_time
        if self.last_update is not None:
            self.delta_time = current_time - self.last_update
        self.last_update = current_time

    def reset(self) -> None:
        """Reset timing state"""
        self.current_time = 0.0
        self.delta_time = 0.0
        self.start_time = time.perf_counter()
        self.last_update = None
