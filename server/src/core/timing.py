"""Timing management and calculations for LED control system."""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .config import SystemDefaults


@dataclass
class TimingConstraints:
    """Hardware timing constraints"""

    min_frame_time_ns: int
    max_frame_time_ns: int
    reset_time_ns: int
    bit_time_ns: float
    led_time_ns: float

    @classmethod
    def from_config(cls, num_leds: int) -> "TimingConstraints":
        """Create timing constraints from system defaults"""
        # Calculate bit and LED timing
        bit_time_ns = 1_000_000_000 / SystemDefaults.DEFAULT_LED_FREQ_HZ
        led_time_ns = bit_time_ns * SystemDefaults.LED_BITS_PER_PIXEL

        # Calculate frame timing
        total_data_time_ns = led_time_ns * num_leds
        min_frame_time_ns = SystemDefaults.MIN_REFRESH_TIME_NS
        max_frame_time_ns = 1_000_000_000 / SystemDefaults.MAX_REFRESH_RATE

        return cls(
            min_frame_time_ns=min_frame_time_ns,
            max_frame_time_ns=max_frame_time_ns,
            reset_time_ns=SystemDefaults.RESET_TIME_NS,
            bit_time_ns=bit_time_ns,
            led_time_ns=led_time_ns,
        )


@dataclass
class TimeState:
    """Manages time state and frame timing"""

    start_time: float = field(default_factory=time.perf_counter)
    last_update: float = 0.0
    frame_count: int = 0
    delta_time: float = 0.0
    time_ms: float = 0.0

    # Performance tracking
    frame_times: List[float] = field(default_factory=list)
    max_frame_times: int = 60  # Track last 60 frames

    def reset(self) -> None:
        """Reset time state"""
        self.start_time = time.perf_counter()
        self.last_update = 0.0
        self.frame_count = 0
        self.delta_time = 0.0
        self.time_ms = 0.0
        self.frame_times.clear()

    def update(self) -> None:
        """Update time state"""
        current_time = time.perf_counter()

        # Calculate delta time
        if self.last_update > 0:
            self.delta_time = current_time - self.last_update

            # Track frame times
            frame_time_ms = self.delta_time * 1000
            self.frame_times.append(frame_time_ms)
            if len(self.frame_times) > self.max_frame_times:
                self.frame_times.pop(0)

        self.last_update = current_time
        self.time_ms = (current_time - self.start_time) * 1000
        self.frame_count += 1

    def get_metrics(self) -> Dict[str, float]:
        """Get timing metrics"""
        if not self.frame_times:
            return {
                "avg_frame_time_ms": 0,
                "min_frame_time_ms": 0,
                "max_frame_time_ms": 0,
                "current_fps": 0,
                "frame_count": self.frame_count,
            }

        avg_frame_time = sum(self.frame_times) / len(self.frame_times)
        return {
            "avg_frame_time_ms": avg_frame_time,
            "min_frame_time_ms": min(self.frame_times),
            "max_frame_time_ms": max(self.frame_times),
            "current_fps": 1000 / avg_frame_time if avg_frame_time > 0 else 0,
            "frame_count": self.frame_count,
        }


def calculate_max_fps(
    num_leds: int, constraints: Optional[TimingConstraints] = None
) -> float:
    """Calculate maximum theoretical FPS for given number of LEDs"""
    if constraints is None:
        constraints = TimingConstraints.from_config(num_leds)

    # Calculate total frame time
    total_data_time_ns = constraints.led_time_ns * num_leds
    total_frame_time_ns = total_data_time_ns + constraints.reset_time_ns

    # Calculate maximum FPS
    max_fps = 1_000_000_000 / total_frame_time_ns

    # Cap at system maximum
    return min(max_fps, SystemDefaults.MAX_REFRESH_RATE)


def validate_timing(num_leds: int) -> Dict[str, float]:
    """Validate and return timing information for LED strip"""
    constraints = TimingConstraints.from_config(num_leds)
    max_fps = calculate_max_fps(num_leds, constraints)

    return {
        "max_fps": max_fps,
        "min_frame_time_ms": constraints.min_frame_time_ns / 1_000_000,
        "max_frame_time_ms": constraints.max_frame_time_ns / 1_000_000,
        "bit_time_ns": constraints.bit_time_ns,
        "led_time_ns": constraints.led_time_ns,
        "total_data_time_us": (constraints.led_time_ns * num_leds) / 1000,
        "reset_time_us": constraints.reset_time_ns / 1000,
    }
