import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Type
import time
import asyncio

import numpy as np
from fastapi import WebSocket

from ..core.websocket_manager import manager as ws_manager
from ..core.exceptions import ValidationError
from .config import PatternConfig, PatternState
from .base import BasePattern, ModifiableAttribute, ParameterSpec
from .modifiers.base import BaseModifier
from .types import (
    BreathePattern,
    ChasePattern,
    GradientPattern,
    MeteorPattern,
    RainbowPattern,
    ScanPattern,
    SolidPattern,
    TwinklePattern,
    WavePattern,
)

logger = logging.getLogger(__name__)


class PatternEngine:
    """Manages pattern generation and validation"""

    def __init__(self, num_pixels: int):
        logger.info(f"Initializing pattern engine with {num_pixels} LEDs")
        self._num_pixels = num_pixels
        self._patterns: Dict[str, Type[BasePattern]] = {}
        self._pattern_instances: Dict[str, BasePattern] = {}
        self._modifiers: Dict[str, Type[BaseModifier]] = {}
        self.current_pattern: Optional[BasePattern] = None
        self.current_config: Optional[PatternConfig] = None
        self.state = PatternState()

        # Initialize active modifiers
        self.active_modifiers: Dict[str, BaseModifier] = {}

        self._register_patterns()
        self._register_modifiers()

        # Start heartbeat
        asyncio.create_task(self._send_heartbeat())

    def _register_patterns(self) -> None:
        """Register available patterns with automatic name generation"""
        # Define pattern categories and their patterns
        pattern_categories = {
            "static": [
                SolidPattern,
                GradientPattern,
            ],
            "moving": [
                WavePattern,
                RainbowPattern,
                ChasePattern,
                ScanPattern,
            ],
            "particle": [
                TwinklePattern,
                MeteorPattern,
                BreathePattern,
            ],
        }

        # Register patterns in order by category
        for category, patterns in sorted(pattern_categories.items()):
            logger.info(f"Registering {category} patterns...")
            for pattern_class in sorted(patterns, key=lambda x: x.__name__):
                name = pattern_class.__name__.lower().replace("pattern", "")
                pattern = pattern_class(self._num_pixels)
                self._patterns[name] = pattern_class
                self._pattern_instances[name] = pattern
                logger.info(f"Registered {category} pattern: {name}")

    def _register_modifiers(self) -> None:
        """Register available modifiers"""
        # Import modifiers here to avoid circular imports
        from .modifiers import AVAILABLE_MODIFIERS

        self._modifiers = {
            mod.__name__.lower().replace("modifier", ""): mod
            for mod in AVAILABLE_MODIFIERS
        }
        logger.info(f"Registered {len(self._modifiers)} modifiers")

    async def _send_heartbeat(self):
        """Send periodic heartbeat to clients"""
        backoff = 1
        max_backoff = 30
        while True:
            try:
                await ws_manager.broadcast({"type": "heartbeat"})
                await asyncio.sleep(5)  # Every 5 seconds
                backoff = 1  # Reset backoff on success
            except asyncio.CancelledError:
                logger.info("Heartbeat task cancelled")
                break
            except Exception as e:
                logger.error(f"Error sending heartbeat: {e}")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)  # Exponential backoff

    async def handle_client_connect(self, websocket: WebSocket) -> None:
        """Send current pattern state when client connects"""
        try:
            if self.current_pattern and self.current_config:
                # Generate current frame
                current_time = time.time() * 1000
                frame = self.current_pattern.generate(
                    current_time, self.current_config.parameters
                )

                # Apply any active modifiers
                if self.current_config.modifiers:
                    for modifier_config in self.current_config.modifiers:
                        if modifier_config.get("enabled", True):
                            modifier = self._modifiers.get(modifier_config["name"])
                            if modifier:
                                frame = modifier.apply(
                                    frame, modifier_config.get("parameters", {})
                                )

                # Send current state
                await websocket.send_json(
                    {
                        "type": "pattern",
                        "data": {
                            "frame": frame.tolist(),
                            "config": asdict(self.current_config),
                            "timestamp": current_time,
                        },
                    }
                )
                logger.info("Sent current pattern state to new client")
        except Exception as e:
            logger.error(f"Error sending initial state to client: {e}")

    async def update(self, time_ms: float) -> Optional[np.ndarray]:
        """Generate pattern frame and send via WebSocket"""
        if not self.current_pattern or not self.current_config:
            logger.warning("No active pattern, skipping frame generation")
            return None

        try:
            logger.debug(
                f"Generating pattern: {self.current_config.pattern_type} "
                f"with params: {self.current_config.parameters}"
            )

            # Ensure pattern has current parameters
            if self.current_pattern.state.parameters != self.current_config.parameters:
                logger.warning(
                    "Pattern state parameters don't match config, updating..."
                )
                self.current_pattern.state.parameters = (
                    self.current_config.parameters.copy()
                )

            # Generate base pattern
            frame = self.current_pattern.generate(
                time_ms, self.current_config.parameters
            )

            if frame is None:
                logger.error("Pattern generated None frame")
                return None

            # Apply modifiers if configured
            if self.current_config.modifiers:
                for modifier_config in self.current_config.modifiers:
                    if modifier_config.get("enabled", True):
                        modifier = self._modifiers.get(modifier_config["name"])
                        if modifier:
                            frame = modifier.apply(
                                frame, modifier_config.get("parameters", {})
                            )

            # Ensure frame is valid
            if not isinstance(frame, np.ndarray):
                logger.error(f"Invalid frame type: {type(frame)}")
                return None

            if frame.shape != (self._num_pixels, 3):
                logger.error(
                    f"Invalid frame shape: {frame.shape}, expected ({self._num_pixels}, 3)"
                )
                return None

            # Ensure frame values are in valid range
            frame = np.clip(frame, 0, 255).astype(np.uint8)

            # Log frame statistics
            nonzero_pixels = np.count_nonzero(np.any(frame > 0, axis=1))
            if nonzero_pixels == 0:
                logger.warning("Generated frame contains all black pixels!")
                logger.debug(
                    f"Current pattern state: {self.current_pattern.state.parameters}"
                )
                logger.debug(
                    f"Current config parameters: {self.current_config.parameters}"
                )
            else:
                logger.debug(
                    f"Frame stats - Shape: {frame.shape}, Range: [{frame.min()}, {frame.max()}], "
                    f"Active pixels: {nonzero_pixels}/{self._num_pixels}, "
                    f"First non-zero pixel: {frame[frame.any(axis=1)][0] if nonzero_pixels > 0 else 'None'}"
                )

            # Send frame via WebSocket
            try:
                message = {
                    "type": "pattern",
                    "data": {
                        "frame": frame.tolist(),
                        "timestamp": time_ms,
                        "pattern_type": self.current_config.pattern_type,
                        "stats": {
                            "active_pixels": int(nonzero_pixels),
                            "max_value": int(frame.max()),
                            "min_value": int(frame.min()),
                        },
                    },
                }
                await ws_manager.broadcast(message)
                logger.debug(
                    f"Frame broadcast complete for {self.current_config.pattern_type}"
                )
            except Exception as e:
                logger.error(f"Failed to send frame: {e}")
                return None

            return frame

        except Exception as e:
            logger.error(f"Pattern update error: {e}")
            # Notify clients of error
            try:
                await ws_manager.broadcast(
                    {
                        "type": "error",
                        "data": {"message": f"Pattern update failed: {str(e)}"},
                    }
                )
            except Exception as broadcast_error:
                logger.error(f"Failed to broadcast error: {broadcast_error}")
            return None

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            # Clear current pattern
            if self.current_pattern:
                self.current_pattern.reset()
            self.current_pattern = None
            self.current_config = None

            # Clear pattern instances
            self._pattern_instances.clear()
            self._patterns.clear()
            self._modifiers.clear()

            # Send clear command via WebSocket
            await ws_manager.broadcast({"type": "clear"})

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def cleanup_sync(self) -> None:
        """Synchronous cleanup for use in __del__"""
        try:
            # Clear current pattern
            if self.current_pattern:
                self.current_pattern.reset()
            self.current_pattern = None
            self.current_config = None

            # Clear pattern instances
            self._pattern_instances.clear()
            self._patterns.clear()
            self._modifiers.clear()

            # Note: We can't do WebSocket broadcast in sync cleanup
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def __del__(self) -> None:
        """Ensure cleanup on deletion"""
        self.cleanup_sync()  # Use sync version for __del__

    async def validate_parameters(
        self, pattern_class: Type[BasePattern], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and normalize pattern parameters"""
        validated = {}
        param_specs = {p.name: p for p in pattern_class.parameters}

        # Check for required parameters
        for name, spec in param_specs.items():
            if name not in params:
                if spec.default is not None:
                    validated[name] = spec.default
                else:
                    raise ValidationError(f"Missing required parameter: {name}")

        # Validate provided parameters
        for name, value in params.items():
            if name not in param_specs:
                logger.warning(f"Unknown parameter: {name}")
                continue

            spec = param_specs[name]

            # Type checking
            if not isinstance(value, spec.type):
                try:
                    value = spec.type(value)
                except (ValueError, TypeError):
                    raise ValidationError(
                        f"Invalid type for parameter {name}: expected {spec.type.__name__}, got {type(value).__name__}"
                    )

            # Range validation
            if spec.min_value is not None and value < spec.min_value:
                raise ValidationError(
                    f"Parameter {name} value {value} is below minimum {spec.min_value}"
                )
            if spec.max_value is not None and value > spec.max_value:
                raise ValidationError(
                    f"Parameter {name} value {value} is above maximum {spec.max_value}"
                )

            validated[name] = value

        return validated

    def validate_modifier_config(
        self, pattern_class: Type[BasePattern], modifier_config: Dict[str, Any]
    ) -> None:
        """Validate modifier configuration"""
        if "name" not in modifier_config:
            raise ValidationError("Modifier must have a name")
        if "hook" not in modifier_config:
            raise ValidationError("Modifier must specify a hook")

        # Check if hook exists
        valid_hooks = {h.name: h for h in pattern_class.modifiable_attributes}
        if modifier_config["hook"] not in valid_hooks:
            raise ValidationError(f"Invalid modifier hook: {modifier_config['hook']}")

        hook = valid_hooks[modifier_config["hook"]]

        # Check if modifier is supported for this hook
        if modifier_config["name"] not in hook.supported_modifiers:
            raise ValidationError(
                f"Modifier {modifier_config['name']} not supported "
                f"for hook {modifier_config['hook']}"
            )

        # Validate modifier parameters
        if "parameters" in modifier_config:
            self.validate_parameters(
                hook.parameter_specs, modifier_config["parameters"]
            )

    async def set_pattern(self, config: PatternConfig) -> None:
        """Set the current pattern with configuration"""
        try:
            # Get pattern instance from registered instances
            pattern = self._pattern_instances.get(config.pattern_type)
            if not pattern:
                logger.error(
                    f"Pattern type {config.pattern_type} not found in registered instances"
                )
                raise ValidationError(f"Unknown pattern type: {config.pattern_type}")

            logger.info(
                f"Setting pattern {config.pattern_type} with raw params: {config.parameters}"
            )

            # Validate parameters
            validated_params = await self.validate_parameters(
                pattern.__class__, config.parameters
            )
            logger.info(f"Validated parameters: {validated_params}")

            # Update state and config first
            self.current_pattern = pattern
            self.current_config = PatternConfig(
                pattern_type=config.pattern_type,
                parameters=validated_params.copy(),  # Make a copy to prevent reference issues
                modifiers=config.modifiers,
            )

            # Reset and reinitialize the pattern
            pattern.reset()
            pattern.state.parameters = (
                validated_params.copy()
            )  # Set parameters after reset

            # Initialize pattern with a test frame
            try:
                current_time = asyncio.get_event_loop().time() * 1000
                pattern.before_generate(
                    current_time, validated_params
                )  # This will update state
                test_frame = pattern._generate(
                    current_time, validated_params
                )  # Call _generate directly to bypass state updates

                if test_frame is None or test_frame.shape != (self._num_pixels, 3):
                    raise ValidationError(
                        f"Pattern generated invalid frame shape: {test_frame.shape if test_frame is not None else None}"
                    )

                # Log detailed frame information
                nonzero_pixels = np.count_nonzero(np.any(test_frame > 0, axis=1))
                first_nonzero = None
                if nonzero_pixels > 0:
                    first_nonzero = test_frame[np.any(test_frame > 0, axis=1)][0]

                logger.info(
                    f"Test frame generated:"
                    f"\n  - Shape: {test_frame.shape}"
                    f"\n  - Range: [{test_frame.min()}, {test_frame.max()}]"
                    f"\n  - Non-zero pixels: {nonzero_pixels}/{self._num_pixels}"
                    f"\n  - First non-zero pixel: {first_nonzero}"
                    f"\n  - Parameters: {validated_params}"
                    f"\n  - Pattern state: {pattern.state.parameters}"
                )

                if nonzero_pixels == 0:
                    logger.warning(
                        f"Test frame contains all black pixels with parameters: {validated_params}"
                    )

            except Exception as e:
                logger.error(f"Failed to generate test frame: {e}")
                raise

            logger.info(
                f"Successfully set pattern to {config.pattern_type} with params: {validated_params}"
            )

        except Exception as e:
            logger.error(f"Error setting pattern: {e}")
            raise

    def validate_pattern_state(self, pattern: BasePattern) -> None:
        """Complete pattern state validation"""
        if not pattern.state:
            raise ValidationError("Pattern missing state")

        # Validate required state attributes
        required_attrs = [
            "frame_count",
            "last_frame_time",
            "delta_time",
            "parameters",
            "cached_data",
            "is_transitioning",
            "frame_times",
            "avg_frame_time",
        ]

        for attr in required_attrs:
            if not hasattr(pattern.state, attr):
                raise ValidationError(f"Pattern state missing {attr}")

        # Validate timing values
        if pattern.state.delta_time < 0:
            raise ValidationError("Invalid negative delta_time")
        if pattern.state.frame_count < 0:
            raise ValidationError("Invalid negative frame_count")

        # Validate cached data structure
        if not isinstance(pattern.state.cached_data, dict):
            raise ValidationError("Pattern cached_data must be a dictionary")

        # Validate performance metrics
        if not isinstance(pattern.state.frame_times, list):
            raise ValidationError("Pattern frame_times must be a list")

        # Validate parameters
        if not isinstance(pattern.state.parameters, dict):
            raise ValidationError("Pattern parameters must be a dictionary")

    def _load_patterns(self) -> Dict[str, Type[BasePattern]]:
        """Load available patterns"""
        # TODO: Implement dynamic pattern loading
        return {}

    def _load_modifiers(self) -> Dict[str, Type[BaseModifier]]:
        """Load available modifiers"""
        # TODO: Implement dynamic modifier loading
        return {}

    def get_patterns_by_category(self) -> Dict[str, List[str]]:
        """Get available patterns organized by category"""
        categories = {"static": [], "moving": [], "particle": []}

        # Categorize patterns
        for name, pattern_cls in self._patterns.items():
            if issubclass(pattern_cls, (SolidPattern, GradientPattern)):
                categories["static"].append(name)
            elif issubclass(
                pattern_cls, (WavePattern, RainbowPattern, ChasePattern, ScanPattern)
            ):
                categories["moving"].append(name)
            elif issubclass(
                pattern_cls, (TwinklePattern, MeteorPattern, BreathePattern)
            ):
                categories["particle"].append(name)

        # Sort patterns within each category
        for category in categories:
            categories[category].sort()

        return categories

    def get_available_patterns(self) -> List[Dict[str, Any]]:
        """Get list of available patterns with metadata"""
        patterns_by_category = self.get_patterns_by_category()
        patterns = []

        # Add patterns in category order
        for category in sorted(patterns_by_category.keys()):
            for name in sorted(patterns_by_category[category]):
                pattern_cls = self._patterns[name]
                patterns.append(
                    {
                        "name": name,
                        "category": category,
                        "description": pattern_cls.__doc__ or "",
                        "parameters": self._get_parameters_metadata(pattern_cls),
                        "supported_modifiers": self._get_supported_modifiers(
                            pattern_cls
                        ),
                    }
                )

        return patterns

    def get_pattern_metadata(self, pattern_name: str) -> Dict[str, Any]:
        """Get metadata for a specific pattern"""
        if pattern_name not in self._patterns:
            raise KeyError(f"Pattern '{pattern_name}' not found")

        pattern_cls = self._patterns[pattern_name]
        return {
            "name": pattern_name,
            "description": pattern_cls.__doc__ or "",
            "parameters": self._get_parameters_metadata(pattern_cls),
            "supported_modifiers": self._get_supported_modifiers(pattern_cls),
        }

    def get_available_modifiers(self) -> List[Dict[str, Any]]:
        """Get list of available modifiers with metadata"""
        return [
            {
                "name": name,
                "description": modifier_cls.__doc__ or "",
                "parameters": self._get_parameters_metadata(modifier_cls),
                "supported_audio_metrics": self._get_supported_audio_metrics(
                    modifier_cls
                ),
            }
            for name, modifier_cls in self._modifiers.items()
        ]

    def get_modifier_metadata(self, modifier_name: str) -> Dict[str, Any]:
        """Get metadata for a specific modifier"""
        if modifier_name not in self._modifiers:
            raise KeyError(f"Modifier '{modifier_name}' not found")

        modifier_cls = self._modifiers[modifier_name]
        return {
            "name": modifier_name,
            "description": modifier_cls.__doc__ or "",
            "parameters": self._get_parameters_metadata(modifier_cls),
            "supported_audio_metrics": self._get_supported_audio_metrics(modifier_cls),
        }

    def _get_parameters_metadata(self, cls: Type) -> Dict[str, Dict[str, Any]]:
        """Get metadata for a class's parameters"""
        if not hasattr(cls, "PARAMETERS"):
            return {}

        metadata = {}
        for name, param in cls.PARAMETERS.items():
            meta = {
                "type": param.get("type", "float"),
                "description": param.get("description", ""),
                "default": param.get("default"),
            }

            if "min" in param:
                meta["min"] = param["min"]
            if "max" in param:
                meta["max"] = param["max"]

            metadata[name] = meta

        return metadata

    def _get_supported_modifiers(self, pattern_cls: Type[BasePattern]) -> List[str]:
        """Get list of modifiers supported by a pattern"""
        if not hasattr(pattern_cls, "SUPPORTED_MODIFIERS"):
            return []
        return pattern_cls.SUPPORTED_MODIFIERS

    def _get_supported_audio_metrics(
        self, modifier_cls: Type[BaseModifier]
    ) -> Optional[List[str]]:
        """Get list of audio metrics supported by a modifier"""
        if not hasattr(modifier_cls, "SUPPORTED_AUDIO_METRICS"):
            return None
        return modifier_cls.SUPPORTED_AUDIO_METRICS

    async def reset_modifiers(self) -> None:
        """Reset all active modifiers to their default state"""
        try:
            if not self.current_pattern:
                return

            # Clear modifiers from current config
            if self.current_config:
                self.current_config.modifiers = None

            # Clear active modifiers
            self._modifiers.clear()

            # Regenerate current frame
            await self.update(time.time() * 1000)

            logger.info("All modifiers reset successfully")
        except Exception as e:
            logger.error(f"Error resetting modifiers: {e}")
            raise

    def update_modifier_parameter(
        self, modifier_name: str, parameter: str, value: Any
    ) -> None:
        """Update a specific parameter of an active modifier"""
        try:
            if not self.current_config or not self.current_config.modifiers:
                return

            for modifier in self.current_config.modifiers:
                if modifier["name"] == modifier_name:
                    if "parameters" not in modifier:
                        modifier["parameters"] = {}
                    modifier["parameters"][parameter] = value
                    break

            logger.debug(
                f"Updated modifier {modifier_name} parameter {parameter} = {value}"
            )
        except Exception as e:
            logger.error(f"Error updating modifier parameter: {e}")
            raise

    async def add_modifier(self, name: str, params: Dict[str, Any]) -> None:
        """Add a modifier to the current pattern"""
        if not self.current_pattern:
            raise ValidationError("No active pattern")

        if name not in self._modifiers:
            raise ValidationError(f"Unknown modifier: {name}")

        # Create modifier instance
        modifier_class = self._modifiers[name]
        modifier = modifier_class()

        # Validate parameters
        validated_params = self.validate_parameters(modifier_class, params)

        # Add to current config
        if not self.current_config.modifiers:
            self.current_config.modifiers = []

        self.current_config.modifiers.append(
            {"name": name, "parameters": validated_params, "enabled": True}
        )

        # Add to active modifiers
        self.active_modifiers[name] = modifier
        logger.info(f"Added modifier {name} with params: {validated_params}")

    async def remove_modifier(self, name: str) -> None:
        """Remove a modifier from the current pattern"""
        if not self.current_pattern:
            raise ValidationError("No active pattern")

        if name not in self.active_modifiers:
            raise ValidationError(f"Modifier not active: {name}")

        # Remove from current config
        if self.current_config.modifiers:
            self.current_config.modifiers = [
                m for m in self.current_config.modifiers if m["name"] != name
            ]

        # Remove from active modifiers
        del self.active_modifiers[name]
        logger.info(f"Removed modifier {name}")

    async def update_modifier(self, name: str, params: Dict[str, Any]) -> None:
        """Update modifier parameters"""
        if not self.current_pattern:
            raise ValidationError("No active pattern")

        if name not in self.active_modifiers:
            raise ValidationError(f"Modifier not active: {name}")

        # Validate parameters
        modifier_class = self._modifiers[name]
        validated_params = self.validate_parameters(modifier_class, params)

        # Update in current config
        if self.current_config.modifiers:
            for modifier in self.current_config.modifiers:
                if modifier["name"] == name:
                    modifier["parameters"].update(validated_params)
                    break

        logger.info(f"Updated modifier {name} with params: {validated_params}")

    def validate_modifier_parameters(
        self, modifier_class: Type[BaseModifier], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate and normalize modifier parameters"""
        validated = {}
        param_specs = {p.name: p for p in modifier_class.parameters}

        # Check for required parameters
        for name, spec in param_specs.items():
            if name not in params:
                if spec.default is not None:
                    validated[name] = spec.default
                else:
                    raise ValidationError(f"Missing required parameter: {name}")

        # Validate provided parameters
        for name, value in params.items():
            if name not in param_specs:
                logger.warning(f"Unknown modifier parameter: {name}")
                continue

            spec = param_specs[name]

            # Type checking
            if not isinstance(value, spec.type):
                try:
                    value = spec.type(value)
                except (ValueError, TypeError):
                    raise ValidationError(
                        f"Parameter {name} must be of type {spec.type.__name__}"
                    )

            # Range checking
            if spec.min_value is not None and value < spec.min_value:
                raise ValidationError(
                    f"Parameter {name} below minimum value {spec.min_value}"
                )
            if spec.max_value is not None and value > spec.max_value:
                raise ValidationError(
                    f"Parameter {name} above maximum value {spec.max_value}"
                )

            validated[name] = value

        return validated
