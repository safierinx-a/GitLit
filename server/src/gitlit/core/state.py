"""Centralized state management for LED control system."""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, Optional, List, Set, Callable

from .config import SystemConfig
from .exceptions import ValidationError
from .timing import TimeState, TimingConstraints
from .transactions import TransactionManager, Transaction, StateChange

logger = logging.getLogger(__name__)


class SystemState(Enum):
    """System operational states"""

    INITIALIZING = auto()
    READY = auto()
    RUNNING = auto()
    PAUSED = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()


@dataclass
class StateObserver:
    """Observer for state changes"""

    callback: Callable[[Dict[str, Any], Dict[str, Any]], None]
    paths: Set[str] = field(default_factory=set)  # Empty means observe all

    def should_notify(self, change: StateChange) -> bool:
        """Check if observer should be notified of change"""
        if not self.paths:
            return True
        return any(change.path.startswith(path) for path in self.paths)


@dataclass
class PerformanceState:
    """Performance monitoring state"""

    frame_count: int = 0
    dropped_frames: int = 0
    buffer_usage: float = 0.0
    generation_times: List[float] = field(default_factory=list)
    transfer_times: List[float] = field(default_factory=list)
    error_count: int = 0
    last_error_time: float = 0
    last_error_message: str = ""

    def update(self, frame_time: float, transfer_time: float) -> None:
        """Update performance metrics"""
        self.frame_count += 1

        # Track generation times (keep last 60 frames)
        self.generation_times.append(frame_time)
        if len(self.generation_times) > 60:
            self.generation_times.pop(0)

        # Track transfer times
        self.transfer_times.append(transfer_time)
        if len(self.transfer_times) > 60:
            self.transfer_times.pop(0)

    def record_error(self, message: str) -> None:
        """Record an error occurrence"""
        self.error_count += 1
        self.last_error_time = time.time()
        self.last_error_message = message

    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        avg_generation = (
            sum(self.generation_times) / len(self.generation_times)
            if self.generation_times
            else 0
        )
        avg_transfer = (
            sum(self.transfer_times) / len(self.transfer_times)
            if self.transfer_times
            else 0
        )

        return {
            "frame_count": self.frame_count,
            "dropped_frames": self.dropped_frames,
            "buffer_usage": self.buffer_usage,
            "avg_generation_time_ms": avg_generation,
            "avg_transfer_time_ms": avg_transfer,
            "error_count": self.error_count,
            "last_error_time": self.last_error_time,
            "last_error_message": self.last_error_message,
        }


@dataclass
class SystemStateManager:
    """Manages system state and transitions"""

    config: SystemConfig
    current_state: SystemState = SystemState.INITIALIZING
    time_state: TimeState = field(default_factory=TimeState)
    performance: PerformanceState = field(default_factory=PerformanceState)
    timing_constraints: Optional[TimingConstraints] = None

    # State change tracking
    state_change_time: float = field(default_factory=time.time)
    last_state: Optional[SystemState] = None

    # Transaction management
    transaction_manager: TransactionManager = field(default_factory=TransactionManager)

    # Observer pattern
    observers: List[StateObserver] = field(default_factory=list)

    def __post_init__(self):
        """Initialize state manager"""
        self.timing_constraints = TimingConstraints.from_config(self.config.led.count)

    def add_observer(
        self,
        callback: Callable[[Dict[str, Any], Dict[str, Any]], None],
        paths: Optional[Set[str]] = None,
    ) -> None:
        """Add state observer"""
        self.observers.append(StateObserver(callback, paths or set()))

    def remove_observer(self, callback: Callable) -> None:
        """Remove state observer"""
        self.observers = [obs for obs in self.observers if obs.callback != callback]

    async def _notify_observers(self, transaction: Transaction) -> None:
        """Notify observers of state changes"""
        old_state = self.get_state()
        # Apply changes to get new state
        new_state = old_state.copy()
        for change in transaction.changes:
            path_parts = change.path.split(".")
            current = new_state
            for part in path_parts[:-1]:
                current = current.setdefault(part, {})
            current[path_parts[-1]] = change.new_value

        # Notify observers
        for observer in self.observers:
            relevant_changes = [
                c for c in transaction.changes if observer.should_notify(c)
            ]
            if relevant_changes:
                try:
                    observer.callback(old_state, new_state)
                except Exception as e:
                    logger.error(f"Observer notification failed: {e}")

    async def start(self) -> None:
        """Start the system"""
        async with TransactionContext(self.transaction_manager) as transaction:
            if self.current_state != SystemState.READY:
                raise ValidationError(f"Cannot start from state {self.current_state}")

            transaction.add_change(
                "system_state", self.current_state, SystemState.RUNNING
            )
            transaction.on_commit = lambda: self._transition_to(SystemState.RUNNING)
            self.time_state.reset()

        logger.info("System started")

    async def pause(self) -> None:
        """Pause the system"""
        async with TransactionContext(self.transaction_manager) as transaction:
            if self.current_state != SystemState.RUNNING:
                raise ValidationError(f"Cannot pause from state {self.current_state}")

            transaction.add_change(
                "system_state", self.current_state, SystemState.PAUSED
            )
            transaction.on_commit = lambda: self._transition_to(SystemState.PAUSED)

        logger.info("System paused")

    async def resume(self) -> None:
        """Resume the system"""
        async with TransactionContext(self.transaction_manager) as transaction:
            if self.current_state != SystemState.PAUSED:
                raise ValidationError(f"Cannot resume from state {self.current_state}")

            transaction.add_change(
                "system_state", self.current_state, SystemState.RUNNING
            )
            transaction.on_commit = lambda: self._transition_to(SystemState.RUNNING)

        logger.info("System resumed")

    async def stop(self) -> None:
        """Stop the system"""
        if self.current_state in {SystemState.ERROR, SystemState.SHUTTING_DOWN}:
            return

        async with TransactionContext(self.transaction_manager) as transaction:
            transaction.add_change(
                "system_state", self.current_state, SystemState.SHUTTING_DOWN
            )
            transaction.on_commit = lambda: self._transition_to(
                SystemState.SHUTTING_DOWN
            )

        logger.info("System stopping")

    def _transition_to(self, new_state: SystemState) -> None:
        """Handle state transition"""
        self.last_state = self.current_state
        self.current_state = new_state
        self.state_change_time = time.time()

        logger.info(f"State transition: {self.last_state} -> {self.current_state}")

    async def update(self) -> None:
        """Update system state"""
        if self.current_state not in {SystemState.RUNNING, SystemState.PAUSED}:
            return

        try:
            async with TransactionContext(self.transaction_manager) as transaction:
                old_time_metrics = self.time_state.get_metrics()
                self.time_state.update()
                new_time_metrics = self.time_state.get_metrics()

                # Record time state changes
                for key, value in new_time_metrics.items():
                    if old_time_metrics.get(key) != value:
                        transaction.add_change(
                            f"timing.{key}", old_time_metrics.get(key), value
                        )

        except Exception as e:
            logger.error(f"State update failed: {e}")
            self.performance.record_error(str(e))
            await self._transition_to(SystemState.ERROR)

    def get_state(self) -> Dict[str, Any]:
        """Get complete system state"""
        return {
            "system_state": self.current_state.name,
            "last_state": self.last_state.name if self.last_state else None,
            "uptime": time.time() - self.state_change_time,
            "timing": self.time_state.get_metrics(),
            "performance": self.performance.get_metrics(),
            "config": {
                "led_count": self.config.led.count,
                "target_fps": self.config.performance.target_fps,
                "brightness": self.config.led.brightness,
            },
        }
