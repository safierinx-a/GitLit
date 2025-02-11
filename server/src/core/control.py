import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import signal
import sys
from contextlib import asynccontextmanager
import time

import numpy as np

from ..patterns.base import BasePattern
from ..patterns.engine import PatternEngine
from ..patterns.config import PatternConfig, PatternState
from ..patterns.types import (
    SolidPattern,
    GradientPattern,
    WavePattern,
    RainbowPattern,
    ChasePattern,
    ScanPattern,
    TwinklePattern,
    MeteorPattern,
    BreathePattern,
)
from .config import SystemConfig
from .exceptions import ValidationError
from .frame_manager import FrameManager
from .state import SystemStateManager, SystemState
from .websocket_manager import manager as ws_manager
from .commands import (
    CommandQueue,
    CommandPriority,
    SetPatternCommand,
    EmergencyStopCommand,
)

logger = logging.getLogger(__name__)


@dataclass
class AudioBinding:
    """Audio parameter to modifier binding"""

    modifier_name: str
    parameter: str
    audio_metric: str  # volume, beat, frequency
    scale: float = 1.0
    offset: float = 0.0


class CommandType(Enum):
    """Types of control commands"""

    SET_PATTERN = "set_pattern"
    UPDATE_PARAMS = "update_params"
    TOGGLE_MODIFIER = "toggle_modifier"
    SET_BRIGHTNESS = "set_brightness"
    ADD_AUDIO_BINDING = "add_audio_binding"
    REMOVE_AUDIO_BINDING = "remove_audio_binding"
    RESET_MODIFIERS = "reset_modifiers"
    STOP = "stop"


@dataclass
class Command:
    """Control command with type and parameters"""

    type: CommandType
    params: Dict[str, Any]


class SystemController:
    """Main system controller with command queue"""

    def __init__(self, config: SystemConfig):
        """Initialize system controller"""
        self.config = config
        self.state_manager = SystemStateManager(config)
        self.frame_manager = FrameManager(
            num_leds=config.led.count, target_fps=config.performance.target_fps
        )

        # Initialize pattern engine
        self.pattern_engine = PatternEngine(num_leds=config.led.count)

        # Command queue
        self.command_queue = CommandQueue(self.state_manager.transaction_manager)

        # Control flags
        self.shutdown_event = asyncio.Event()
        self.update_task: Optional[asyncio.Task] = None
        self._cleanup_tasks: list[asyncio.Task] = []

        # Register signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._signal_handler)

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown")
        if not self.shutdown_event.is_set():
            # Create and enqueue emergency stop command
            stop_cmd = EmergencyStopCommand()
            asyncio.create_task(self.command_queue.enqueue(stop_cmd))

    @property
    def is_running(self) -> bool:
        """Check if system is running"""
        return self.state_manager.current_state == SystemState.RUNNING

    async def _register_patterns(self) -> None:
        """Register built-in patterns"""
        patterns = [
            SolidPattern,
            GradientPattern,
            WavePattern,
            RainbowPattern,
            ChasePattern,
            ScanPattern,
            TwinklePattern,
            MeteorPattern,
            BreathePattern,
        ]
        for pattern_class in patterns:
            await self.pattern_engine.register_pattern(pattern_class)

    async def start(self) -> None:
        """Start the system"""
        try:
            logger.info("Starting system controller")

            # Initialize components
            await self.frame_manager.start()
            await ws_manager.start()
            await self.command_queue.start()

            # Register patterns
            await self._register_patterns()

            # Start update loop
            self.update_task = asyncio.create_task(
                self._update_loop(), name="system_update_loop"
            )
            self._cleanup_tasks.append(self.update_task)

            # Transition to ready state
            await self.state_manager.start()
            logger.info("System controller started")

        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            await self.stop()
            raise

    async def stop(self) -> None:
        """Stop the system"""
        if self.shutdown_event.is_set():
            return

        logger.info("Stopping system controller")
        self.shutdown_event.set()

        try:
            # Stop components in order
            await self.command_queue.stop()
            await self.state_manager.stop()
            await self.frame_manager.stop()
            await ws_manager.stop()

            # Cancel all tasks
            for task in self._cleanup_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

            logger.info("System controller stopped")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise

    async def _update_loop(self) -> None:
        """Main update loop"""
        consecutive_errors = 0
        last_error_time = 0.0
        ERROR_THRESHOLD = 10
        ERROR_RESET_TIME = 5.0  # seconds

        try:
            while not self.shutdown_event.is_set():
                if not self.is_running:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    current_time = time.time()

                    # Reset error count if enough time has passed
                    if current_time - last_error_time > ERROR_RESET_TIME:
                        consecutive_errors = 0

                    # Update state
                    await self.state_manager.update()

                    # Generate frame
                    frame, metrics = await self.frame_manager.generate_frame(
                        self._generate_pattern_frame
                    )

                    # Update performance metrics
                    self.state_manager.performance.update(
                        metrics.generation_time_ms, metrics.transfer_time_ms
                    )

                    # Broadcast frame
                    if frame is not None:
                        await ws_manager.broadcast_frame(
                            frame,
                            {
                                "frame_number": metrics.frame_number,
                                "timestamp": metrics.timestamp,
                            },
                        )

                    # Reset error count on successful iteration
                    consecutive_errors = 0

                    # Maintain target frame rate
                    await asyncio.sleep(1 / self.config.performance.target_fps)

                except Exception as e:
                    consecutive_errors += 1
                    last_error_time = current_time
                    logger.error(f"Update loop error: {e}")
                    self.state_manager.performance.record_error(str(e))

                    # Handle consecutive errors
                    if consecutive_errors >= ERROR_THRESHOLD:
                        logger.critical(
                            f"Too many consecutive errors ({consecutive_errors}), attempting recovery"
                        )
                        try:
                            # Try to recover pattern engine
                            await self.pattern_engine.reset()
                            # Reset frame manager
                            await self.frame_manager.reset()
                            # Clear command queue
                            await self.command_queue.clear()
                            logger.info("Recovery attempt completed")
                            consecutive_errors = 0
                        except Exception as recovery_error:
                            logger.error(f"Recovery failed: {recovery_error}")
                            await self.stop()
                            raise

                    # Delay based on error count
                    delay = min(consecutive_errors * 0.5, 5.0)  # Max 5 second delay
                    await asyncio.sleep(delay)

        except asyncio.CancelledError:
            logger.info("Update loop cancelled")
            raise

        except Exception as e:
            logger.error(f"Fatal error in update loop: {e}")
            await self.stop()
            raise

    async def _generate_pattern_frame(
        self, time_ms: float, **kwargs
    ) -> Optional[np.ndarray]:
        """Generate pattern frame using pattern engine with validation"""
        try:
            # Check if we have an active pattern
            if not self.pattern_engine.current_pattern:
                # Return black frame if no pattern is active
                return np.zeros((self.config.led.count, 3), dtype=np.uint8)

            # Generate frame with timing
            start_time = time.perf_counter()
            frame = await self.pattern_engine.generate_frame(time_ms)
            generation_time = (time.perf_counter() - start_time) * 1000

            # Validate frame
            if frame is None:
                raise ValidationError("Pattern generated None frame")
            if not isinstance(frame, np.ndarray):
                raise ValidationError(f"Invalid frame type: {type(frame)}")
            if frame.shape != (self.config.led.count, 3):
                raise ValidationError(
                    f"Invalid frame shape: {frame.shape}, expected ({self.config.led.count}, 3)"
                )
            if frame.dtype != np.uint8:
                frame = np.clip(frame, 0, 255).astype(np.uint8)

            # Update performance metrics
            self.state_manager.performance.update(generation_time, 0)
            return frame

        except Exception as e:
            error_msg = f"Frame generation failed: {str(e)}"
            logger.error(error_msg)
            self.state_manager.performance.record_error(error_msg)

            # Return last valid frame or black frame
            return getattr(
                self.pattern_engine,
                "_last_valid_frame",
                np.zeros((self.config.led.count, 3), dtype=np.uint8),
            )

    @asynccontextmanager
    async def pause(self):
        """Temporarily pause the system"""
        was_running = self.is_running
        if was_running:
            await self.state_manager.pause()
        try:
            yield
        finally:
            if was_running:
                await self.state_manager.resume()

    def get_state(self) -> Dict[str, Any]:
        """Get current system state"""
        return {
            **self.state_manager.get_state(),
            "frame_manager": self.frame_manager.get_performance_metrics(),
            "pattern_engine": {
                "current_pattern": self.pattern_engine.current_pattern.name
                if self.pattern_engine.current_pattern
                else None,
                "available_patterns": list(self.pattern_engine.patterns.keys()),
                "transition_state": {
                    "active": self.pattern_engine.transition_state.is_active,
                    "progress": self.pattern_engine.transition_state.progress,
                },
            },
            "command_queue": {
                "current_command": self.command_queue.get_current_command(),
                "history": self.command_queue.get_history(5),
            },
        }

    # Command interface methods
    async def set_pattern(
        self, pattern_name: str, parameters: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set active pattern through command queue"""
        command = SetPatternCommand(pattern_name, parameters)
        await self.command_queue.enqueue(command)

    async def emergency_stop(self) -> None:
        """Trigger emergency stop"""
        command = EmergencyStopCommand()
        await self.command_queue.enqueue(command)
