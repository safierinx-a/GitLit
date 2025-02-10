import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np

from ..patterns.base import BasePattern
from ..patterns.engine import PatternEngine
from ..patterns.config import PatternConfig
from .config import SystemConfig

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
    """Main system controller handling patterns and LED updates"""

    def __init__(self, config: SystemConfig):
        # Store configuration
        self.config = config

        # Initialize components
        self.pattern_engine = PatternEngine(self.config.led.count)

        # Set default pattern (solid color)
        default_pattern = PatternConfig(
            pattern_type="solid",
            parameters={"color": [0, 0, 255]},  # Blue color
            modifiers=[],
        )
        self.pattern_engine.set_pattern(default_pattern)

        # Control state
        self.is_running = False
        self.command_queue: asyncio.Queue[Command] = asyncio.Queue()
        self.update_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        # Performance monitoring
        self.last_frame_time = 0
        self.frame_times: List[float] = []
        self.target_frame_time = 1.0 / self.config.performance.target_fps

        # Audio state
        self.audio_processor = None
        self.audio_bindings: List[AudioBinding] = []

    def init_audio(self, audio_processor: Any) -> None:
        """Initialize audio processing"""
        self.audio_processor = audio_processor
        self.config.features.audio_enabled = True

    async def start(self) -> None:
        """Start the control system"""
        async with self._lock:
            if self.is_running:
                return

            self.is_running = True
            self.update_task = asyncio.create_task(self._update_loop())
            logger.info("System controller started")

    async def stop(self) -> None:
        """Stop the control system"""
        async with self._lock:
            if not self.is_running:
                return

            logger.info("Stopping system controller...")
            self.is_running = False
            await self.command_queue.put(Command(CommandType.STOP, {}))

            if self.update_task:
                try:
                    await asyncio.wait_for(self.update_task, timeout=1.0)
                except asyncio.TimeoutError:
                    self.update_task.cancel()
                    try:
                        await self.update_task
                    except asyncio.CancelledError:
                        pass

            # Cleanup
            await self.pattern_engine.cleanup()
            if self.audio_processor:
                self.audio_processor.cleanup()

            logger.info("System controller stopped")

    async def _update_loop(self) -> None:
        """Main update loop"""
        last_update = asyncio.get_event_loop().time()

        while self.is_running:
            try:
                current_time = asyncio.get_event_loop().time()
                frame_delta = current_time - last_update

                # Process any pending commands
                while not self.command_queue.empty():
                    cmd = await self.command_queue.get()
                    await self._handle_command(cmd)
                    self.command_queue.task_done()

                # Update pattern
                frame = await self.pattern_engine.update(
                    current_time * 1000
                )  # Convert to milliseconds

                # Process audio if enabled
                if self.config.features.audio_enabled and self.audio_processor:
                    await self._process_audio_bindings()

                # Update performance metrics
                self.frame_times.append(frame_delta)
                if len(self.frame_times) > 60:
                    self.frame_times.pop(0)
                self.last_frame_time = frame_delta

                # Calculate sleep time to maintain target FPS
                sleep_time = max(0, self.target_frame_time - frame_delta)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)

                last_update = current_time

            except asyncio.CancelledError:
                logger.info("Update loop cancelled")
                break
            except Exception as e:
                logger.error(f"Update loop error: {e}")
                await asyncio.sleep(0.1)  # Prevent tight error loop

    async def _process_audio_bindings(self) -> None:
        """Process audio bindings and update modifiers"""
        try:
            features = self.audio_processor.get_features()
            if not features:
                return

            for binding in self.audio_bindings:
                if binding.audio_metric in features:
                    value = (
                        features[binding.audio_metric] * binding.scale + binding.offset
                    )
                    await self.pattern_engine.update_modifier_parameter(
                        binding.modifier_name, binding.parameter, value
                    )
        except Exception as e:
            logger.error(f"Audio binding error: {e}")

    async def _handle_command(self, command: Command) -> None:
        """Handle a command from the queue"""
        try:
            if command.type == CommandType.STOP:
                self.is_running = False
            elif command.type == CommandType.SET_PATTERN:
                pattern_name = command.params["pattern"]
                params = command.params.get("params", {})
                pattern_config = PatternConfig(
                    pattern_type=pattern_name,
                    parameters=params,
                    modifiers=[],
                )
                self.pattern_engine.set_pattern(pattern_config)
            elif command.type == CommandType.UPDATE_PARAMS:
                await self.pattern_engine.update_parameters(command.params)
            elif command.type == CommandType.TOGGLE_MODIFIER:
                name = command.params["name"]
                if name in self.pattern_engine.active_modifiers:
                    await self.pattern_engine.remove_modifier(name)
                else:
                    await self.pattern_engine.add_modifier(
                        name, command.params.get("params", {})
                    )
            elif command.type == CommandType.SET_BRIGHTNESS:
                self.config.led.brightness = command.params["brightness"]
            elif command.type == CommandType.ADD_AUDIO_BINDING:
                if self.config.features.audio_enabled:
                    self.audio_bindings.append(AudioBinding(**command.params))
            elif command.type == CommandType.REMOVE_AUDIO_BINDING:
                if self.config.features.audio_enabled:
                    self.audio_bindings = [
                        b
                        for b in self.audio_bindings
                        if b.modifier_name != command.params["modifier_name"]
                    ]
            elif command.type == CommandType.RESET_MODIFIERS:
                await self.pattern_engine.reset_modifiers()
        except Exception as e:
            logger.error(f"Command handling error: {e}")

    async def set_pattern(
        self, pattern_name: str, params: Optional[Dict] = None
    ) -> None:
        """Set the active pattern"""
        await self.command_queue.put(
            Command(
                CommandType.SET_PATTERN,
                {"pattern": pattern_name, "params": params or {}},
            )
        )

    async def update_parameters(self, params: Dict[str, Any]) -> None:
        """Update pattern parameters"""
        await self.command_queue.put(Command(CommandType.UPDATE_PARAMS, params))

    async def toggle_modifier(self, name: str, params: Optional[Dict] = None) -> None:
        """Toggle a pattern modifier"""
        await self.command_queue.put(
            Command(CommandType.TOGGLE_MODIFIER, {"name": name, "params": params or {}})
        )

    async def set_brightness(self, brightness: float) -> None:
        """Set LED brightness"""
        await self.command_queue.put(
            Command(CommandType.SET_BRIGHTNESS, {"brightness": brightness})
        )

    async def add_audio_binding(
        self,
        modifier_name: str,
        parameter: str,
        audio_metric: str,
        scale: float = 1.0,
        offset: float = 0.0,
    ) -> None:
        """Add an audio parameter binding"""
        await self.command_queue.put(
            Command(
                CommandType.ADD_AUDIO_BINDING,
                {
                    "modifier_name": modifier_name,
                    "parameter": parameter,
                    "audio_metric": audio_metric,
                    "scale": scale,
                    "offset": offset,
                },
            )
        )

    async def remove_audio_binding(self, modifier_name: str) -> None:
        """Remove an audio binding"""
        await self.command_queue.put(
            Command(CommandType.REMOVE_AUDIO_BINDING, {"modifier_name": modifier_name})
        )

    def get_state(self) -> Dict[str, Any]:
        """Get current system state"""
        with self._lock:
            return {
                "pattern": self.pattern_engine.current_pattern.name
                if self.pattern_engine.current_pattern
                else "",
                "modifiers": list(self.pattern_engine.active_modifiers.keys()),
                "performance": {
                    "fps": 1.0 / self.last_frame_time
                    if self.last_frame_time > 0
                    else 0.0,
                    "frame_time": self.last_frame_time,
                },
                "audio": {
                    "enabled": self.config.features.audio_enabled,
                }
                if self.audio_processor
                else None,
            }
