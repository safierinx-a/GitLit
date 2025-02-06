import threading
import queue
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from ..patterns.engine import PatternEngine
from ..led.controller import LEDController, create_controller
from ..patterns.base import BasePattern
from .config import Command, CommandType, AudioBinding

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
    STOP = "stop"


@dataclass
class Command:
    """Control command with type and parameters"""

    type: CommandType
    params: Dict[str, Any]


class SystemController:
    """Main system controller handling patterns and LED updates"""

    def __init__(self, config: Dict[str, Any]):
        # Initialize components
        self.config = config
        self.led_config = config["led"]
        self.pattern_engine = PatternEngine(self.led_config["led_count"])

        # Control state
        self.is_running = False
        self.command_queue = queue.Queue()
        self.update_thread = None
        self._lock = threading.Lock()

        # Performance monitoring
        self.last_frame_time = 0
        self.frame_times = []
        self.target_fps = config.get("performance", {}).get("target_fps", 60)

        # Audio state
        self.audio_bindings: List[AudioBinding] = []
        self.audio_enabled = (
            config.get("features", {}).get("audio", {}).get("enabled", False)
        )

    def start(self) -> None:
        """Start the control system"""
        with self._lock:
            if self.is_running:
                return

            self.is_running = True
            self.update_thread = threading.Thread(target=self._update_loop)
            self.update_thread.daemon = True
            self.update_thread.start()

    def stop(self) -> None:
        """Stop the control system"""
        with self._lock:
            if not self.is_running:
                return

            self.is_running = False
            self.command_queue.put(Command(CommandType.STOP, {}))

            if self.update_thread:
                self.update_thread.join(timeout=1.0)

            self.pattern_engine.cleanup()

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
                self.pattern_engine.update(current_time)

                # Update performance metrics
                frame_time = time.time() * 1000 - current_time
                self.frame_times.append(frame_time)
                if len(self.frame_times) > 60:
                    self.frame_times.pop(0)
                self.last_frame_time = frame_time

                # Sleep to maintain target FPS
                sleep_time = max(0, 1.0 / self.target_fps - frame_time / 1000)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Update loop error: {e}")
                time.sleep(0.1)  # Prevent tight error loop

    def _handle_command(self, command: Command) -> None:
        """Handle a command from the queue"""
        if command.type == CommandType.STOP:
            self.is_running = False
        elif command.type == CommandType.SET_PATTERN:
            self.pattern_engine.set_pattern(command.params["pattern"])
        elif command.type == CommandType.UPDATE_PARAMS:
            self.pattern_engine.update_parameters(command.params)
        elif command.type == CommandType.TOGGLE_MODIFIER:
            name = command.params["name"]
            if name in self.pattern_engine.active_modifiers:
                self.pattern_engine.remove_modifier(name)
            else:
                self.pattern_engine.add_modifier(name, command.params.get("params", {}))
        elif command.type == CommandType.SET_BRIGHTNESS:
            self.led_config["brightness"] = command.params["brightness"]
        elif command.type == CommandType.ADD_AUDIO_BINDING:
            if self.audio_enabled:
                self.audio_bindings.append(AudioBinding(**command.params))
        elif command.type == CommandType.REMOVE_AUDIO_BINDING:
            if self.audio_enabled:
                self.audio_bindings = [
                    b
                    for b in self.audio_bindings
                    if b.modifier_name != command.params["modifier_name"]
                ]

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

    def get_state(self) -> Dict[str, Any]:
        """Get current system state"""
        state = {
            "pattern": self.pattern_engine.current_pattern,
            "modifiers": list(self.pattern_engine.active_modifiers.keys()),
            "performance": {
                "fps": 1000 / (sum(self.frame_times) / len(self.frame_times))
                if self.frame_times
                else 0,
                "frame_time": sum(self.frame_times) / len(self.frame_times)
                if self.frame_times
                else 0,
            },
        }

        if self.audio_enabled:
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
