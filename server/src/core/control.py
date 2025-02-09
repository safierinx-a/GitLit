import logging
import queue
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

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

        # Control state
        self.is_running = False
        self.command_queue: queue.Queue[Command] = queue.Queue()
        self.update_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Performance monitoring
        self.last_frame_time = 0
        self.frame_times: List[float] = []

        # Audio state
        self.audio_processor = None
        self.audio_bindings: List[AudioBinding] = []

    def init_audio(self, audio_processor: Any) -> None:
        """Initialize audio processing"""
        self.audio_processor = audio_processor
        self.config.features.audio_enabled = True

    def start(self) -> None:
        """Start the control system"""
        with self._lock:
            if self.is_running:
                return

            self.is_running = True
            self.update_thread = threading.Thread(target=self._update_loop)
            self.update_thread.daemon = True
            self.update_thread.start()

            logger.info("System controller started")

    def stop(self) -> None:
        """Stop the control system"""
        with self._lock:
            if not self.is_running:
                return

            logger.info("Stopping system controller...")
            self.is_running = False
            self.command_queue.put(Command(CommandType.STOP, {}))

            if self.update_thread:
                self.update_thread.join(timeout=1.0)

            # Cleanup
            self.pattern_engine.cleanup()
            if self.audio_processor:
                self.audio_processor.cleanup()

            logger.info("System controller stopped")

    def _update_loop(self) -> None:
        """Main update loop"""
        while self.is_running:
            try:
                # Process any pending commands
                while not self.command_queue.empty():
                    cmd = self.command_queue.get_nowait()
                    self._handle_command(cmd)

                # Update pattern
                current_time = time.time() * 1000  # Convert to milliseconds
                frame = self.pattern_engine.update(current_time)

                # Process audio if enabled
                if self.config.features.audio_enabled and self.audio_processor:
                    self._process_audio_bindings()

                # Update performance metrics
                frame_time = time.time() * 1000 - current_time
                self.frame_times.append(frame_time)
                if len(self.frame_times) > 60:
                    self.frame_times.pop(0)
                self.last_frame_time = frame_time

                # Sleep to maintain target FPS
                sleep_time = max(
                    0, 1.0 / self.config.performance.target_fps - frame_time / 1000
                )
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Update loop error: {e}")
                time.sleep(0.1)  # Prevent tight error loop

    def _process_audio_bindings(self) -> None:
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
                    self.pattern_engine.update_modifier_parameter(
                        binding.modifier_name, binding.parameter, value
                    )
        except Exception as e:
            logger.error(f"Audio binding error: {e}")

    def _handle_command(self, command: Command) -> None:
        """Handle a command from the queue"""
        try:
            if command.type == CommandType.STOP:
                self.is_running = False
            elif command.type == CommandType.SET_PATTERN:
                pattern_name = command.params["pattern"]
                params = command.params.get("params", {})
                pattern_config = PatternConfig(
                    pattern_type=pattern_name, parameters=params, modifiers=[]
                )
                self.pattern_engine.set_pattern(pattern_config)
            elif command.type == CommandType.UPDATE_PARAMS:
                self.pattern_engine.update_parameters(command.params)
            elif command.type == CommandType.TOGGLE_MODIFIER:
                name = command.params["name"]
                if name in self.pattern_engine.active_modifiers:
                    self.pattern_engine.remove_modifier(name)
                else:
                    self.pattern_engine.add_modifier(
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
                self.pattern_engine.reset_modifiers()
        except Exception as e:
            logger.error(f"Command handling error: {e}")

    def set_pattern(self, pattern_name: str, params: Optional[Dict] = None) -> None:
        """Set the active pattern"""
        self.command_queue.put(
            Command(
                CommandType.SET_PATTERN,
                {"pattern": pattern_name, "params": params or {}},
            )
        )

    def update_parameters(self, params: Dict[str, Any]) -> None:
        """Update pattern parameters"""
        self.command_queue.put(Command(CommandType.UPDATE_PARAMS, params))

    def toggle_modifier(self, name: str, params: Optional[Dict] = None) -> None:
        """Toggle a pattern modifier"""
        self.command_queue.put(
            Command(CommandType.TOGGLE_MODIFIER, {"name": name, "params": params or {}})
        )

    def set_brightness(self, brightness: float) -> None:
        """Set LED brightness"""
        self.command_queue.put(
            Command(CommandType.SET_BRIGHTNESS, {"brightness": brightness})
        )

    def add_audio_binding(
        self,
        modifier_name: str,
        parameter: str,
        audio_metric: str,
        scale: float = 1.0,
        offset: float = 0.0,
    ) -> None:
        """Add an audio parameter binding"""
        self.command_queue.put(
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

    def remove_audio_binding(self, modifier_name: str) -> None:
        """Remove an audio binding"""
        self.command_queue.put(
            Command(CommandType.REMOVE_AUDIO_BINDING, {"modifier_name": modifier_name})
        )

    def reset_modifiers(self) -> None:
        """Reset all modifiers to default state"""
        self.command_queue.put(Command(CommandType.RESET_MODIFIERS, {}))

    def get_state(self) -> Dict[str, Any]:
        """Get current system state"""
        state = {
            "pattern": self.pattern_engine.current_pattern,
            "modifiers": list(self.pattern_engine.active_modifiers.keys()),
            "performance": {
                "fps": (
                    1000 / (sum(self.frame_times) / len(self.frame_times))
                    if self.frame_times
                    else 0
                ),
                "frame_time": (
                    sum(self.frame_times) / len(self.frame_times)
                    if self.frame_times
                    else 0
                ),
            },
        }

        if self.config.features.audio_enabled:
            state["audio"] = {
                "enabled": True,
                "bindings": [
                    {
                        "modifier": b.modifier_name,
                        "parameter": b.parameter,
                        "metric": b.audio_metric,
                        "scale": b.scale,
                        "offset": b.offset,
                    }
                    for b in self.audio_bindings
                ],
            }

        return state
