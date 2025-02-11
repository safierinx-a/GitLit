"""Frame generation and management with optimized buffering and timing."""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, List
import numpy as np
from dataclasses import dataclass, field

from .config import SystemDefaults
from .exceptions import ValidationError
from .timing import TimeState

logger = logging.getLogger(__name__)


@dataclass
class FrameMetrics:
    """Metrics for frame generation and timing"""

    generation_time_ms: float = 0.0
    transfer_time_ms: float = 0.0
    total_time_ms: float = 0.0
    frame_number: int = 0
    timestamp: float = 0.0
    dropped_frames: int = 0
    buffer_usage: float = 0.0  # 0-1 representing buffer fullness


@dataclass
class FrameBuffer:
    """Double/Triple buffering implementation for smooth frame delivery"""

    size: int = SystemDefaults.DEFAULT_BUFFER_SIZE
    frames: List[np.ndarray] = field(default_factory=list)
    metrics: List[FrameMetrics] = field(default_factory=list)
    read_index: int = 0
    write_index: int = 0

    def __post_init__(self):
        """Initialize buffer with empty frames"""
        if self.size < 1:
            raise ValidationError("Buffer size must be at least 1")
        self.frames = [None] * self.size
        self.metrics = [FrameMetrics() for _ in range(self.size)]

    def write_frame(self, frame: np.ndarray, metrics: FrameMetrics) -> bool:
        """Write frame to buffer, returns False if buffer is full"""
        if self.is_full():
            return False
        self.frames[self.write_index] = frame.copy()
        self.metrics[self.write_index] = metrics
        self.write_index = (self.write_index + 1) % self.size
        return True

    def read_frame(self) -> tuple[Optional[np.ndarray], Optional[FrameMetrics]]:
        """Read frame from buffer, returns (None, None) if buffer is empty"""
        if self.is_empty():
            return None, None
        frame = self.frames[self.read_index]
        metrics = self.metrics[self.read_index]
        self.frames[self.read_index] = None
        self.read_index = (self.read_index + 1) % self.size
        return frame, metrics

    def is_empty(self) -> bool:
        """Check if buffer is empty"""
        return self.read_index == self.write_index

    def is_full(self) -> bool:
        """Check if buffer is full"""
        return ((self.write_index + 1) % self.size) == self.read_index

    def get_usage(self) -> float:
        """Get buffer usage as percentage"""
        if self.read_index <= self.write_index:
            used = self.write_index - self.read_index
        else:
            used = self.size - (self.read_index - self.write_index)
        return used / self.size


class FrameManager:
    """Manages frame generation, buffering, and timing"""

    def __init__(self, num_leds: int, target_fps: int):
        """Initialize frame manager"""
        self.num_leds = num_leds
        self.target_fps = target_fps
        self.frame_time_ms = 1000 / target_fps
        self.frame_budget_ms = (
            self.frame_time_ms * 0.9
        )  # 90% of frame time for processing

        # Buffers for smooth frame delivery
        self.primary_buffer = FrameBuffer()
        self.emergency_frame = np.zeros((num_leds, 3), dtype=np.uint8)

        # State
        self.running = False
        self.frame_count = 0
        self.dropped_frames = 0
        self.last_frame_time = 0
        self.time_state = TimeState()

        # Performance monitoring
        self.generation_times: List[float] = []
        self.transfer_times: List[float] = []
        self.frame_intervals: List[float] = []

    async def start(self) -> None:
        """Start frame manager"""
        if self.running:
            return
        self.running = True
        self.time_state.reset()
        logger.info(
            f"Frame manager started with {self.num_leds} LEDs at {self.target_fps} FPS"
        )

    async def stop(self) -> None:
        """Stop frame manager"""
        self.running = False
        # Clear buffers
        self.primary_buffer = FrameBuffer()
        logger.info("Frame manager stopped")

    async def generate_frame(
        self, pattern_func, **kwargs
    ) -> tuple[Optional[np.ndarray], FrameMetrics]:
        """Generate a new frame using the provided pattern function"""
        if not self.running:
            return None, FrameMetrics()

        try:
            # Update timing
            current_time = time.perf_counter()
            if self.last_frame_time:
                frame_interval = (current_time - self.last_frame_time) * 1000
                self.frame_intervals.append(frame_interval)
            self.last_frame_time = current_time

            # Generate frame
            start_time = time.perf_counter()
            frame = await pattern_func(self.time_state.time_ms, **kwargs)
            generation_time = (time.perf_counter() - start_time) * 1000

            # Update metrics
            self.frame_count += 1
            self.generation_times.append(generation_time)
            if len(self.generation_times) > 60:
                self.generation_times.pop(0)

            # Create frame metrics
            metrics = FrameMetrics(
                generation_time_ms=generation_time,
                frame_number=self.frame_count,
                timestamp=self.time_state.time_ms,
                buffer_usage=self.primary_buffer.get_usage(),
            )

            # Check timing budget
            if generation_time > self.frame_budget_ms:
                logger.warning(
                    f"Frame generation took {generation_time:.1f}ms, "
                    f"exceeding budget of {self.frame_budget_ms:.1f}ms"
                )

            return frame, metrics

        except Exception as e:
            logger.error(f"Frame generation failed: {e}")
            self.dropped_frames += 1
            return self.emergency_frame.copy(), FrameMetrics(
                dropped_frames=self.dropped_frames, frame_number=self.frame_count
            )

    async def write_frame(self, frame: np.ndarray, metrics: FrameMetrics) -> bool:
        """Write frame to buffer"""
        if not self.running:
            return False

        # Try to write to primary buffer
        if not self.primary_buffer.write_frame(frame, metrics):
            self.dropped_frames += 1
            logger.warning("Frame dropped: Buffer full")
            return False

        return True

    async def read_frame(self) -> tuple[Optional[np.ndarray], FrameMetrics]:
        """Read next frame from buffer"""
        if not self.running:
            return None, FrameMetrics()

        # Try to read from primary buffer
        frame, metrics = self.primary_buffer.read_frame()
        if frame is None:
            logger.warning("Buffer underrun, using emergency frame")
            return self.emergency_frame.copy(), FrameMetrics(
                dropped_frames=self.dropped_frames, frame_number=self.frame_count
            )

        return frame, metrics

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        avg_generation = (
            sum(self.generation_times) / len(self.generation_times)
            if self.generation_times
            else 0
        )
        avg_interval = (
            sum(self.frame_intervals) / len(self.frame_intervals)
            if self.frame_intervals
            else 0
        )

        return {
            "frame_count": self.frame_count,
            "dropped_frames": self.dropped_frames,
            "avg_generation_time_ms": avg_generation,
            "avg_frame_interval_ms": avg_interval,
            "buffer_usage": self.primary_buffer.get_usage(),
            "target_fps": self.target_fps,
            "actual_fps": 1000 / avg_interval if avg_interval else 0,
        }
