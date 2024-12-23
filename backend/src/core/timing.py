from dataclasses import dataclass
from typing import Optional


@dataclass
class TimeState:
    """Centralized time management for patterns"""

    current_time: float = 0.0  # Current time in seconds
    delta_time: float = 0.0  # Time since last frame in seconds
    start_time: float = 0.0  # Pattern start time
    time_scale: float = 1.0  # Global time scaling
    frame_rate: float = 30.0  # Add frame rate reference

    def update(self, time_ms: float) -> None:
        """Update time state"""
        new_time = time_ms / 1000.0
        self.delta_time = new_time - self.current_time
        self.current_time = new_time

    def get_phase(self, speed: float = 1.0, offset: float = 0.0) -> float:
        """Get normalized cyclic phase (0-1) with 1-second period"""
        t = self.current_time * speed * self.time_scale
        return (t + offset) % 1.0

    def get_bounce(self, speed: float = 1.0, offset: float = 0.0) -> float:
        """Get normalized bouncing phase (0-1-0) with 2-second period"""
        t = self.current_time * speed * self.time_scale / 2.0
        return abs((t + offset) % 2.0 - 1.0)

    def get_elapsed(self, speed: float = 1.0) -> float:
        """Get elapsed time with speed scaling"""
        return (self.current_time - self.start_time) * speed * self.time_scale

    def get_spawn_chance(self, base_rate: float) -> float:
        """Get spawn chance scaled to frame rate"""
        return base_rate * self.delta_time * self.frame_rate
