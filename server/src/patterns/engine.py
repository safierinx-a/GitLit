import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Type

import numpy as np

from ..api.websocket import manager as ws_manager
from ..core.config import PatternConfig
from ..core.exceptions import ValidationError
from ..core.state import PatternState
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
        self._num_pixels = num_pixels
        self._patterns: Dict[str, Type[BasePattern]] = {}
        self._pattern_instances: Dict[str, BasePattern] = {}
        self._modifiers: Dict[str, Type[BaseModifier]] = {}
        self.current_pattern: Optional[BasePattern] = None
        self.current_config: Optional[PatternConfig] = None
        self.state = PatternState()

        self._register_patterns()
        self._register_modifiers()

    def _register_patterns(self) -> None:
        """Register available patterns with automatic name generation"""
        pattern_classes = [
            # Static Patterns
            SolidPattern,
            GradientPattern,
            # Moving Patterns
            WavePattern,
            RainbowPattern,
            ChasePattern,
            ScanPattern,
            # Particle Patterns
            TwinklePattern,
            MeteorPattern,
            BreathePattern,
        ]

        for pattern_class in pattern_classes:
            name = pattern_class.__name__.lower().replace("pattern", "")
            pattern = pattern_class(self._num_pixels)
            self._patterns[name] = pattern_class
            self._pattern_instances[name] = pattern
            logger.info(f"Registered pattern: {name}")

    def _register_modifiers(self) -> None:
        """Register available modifiers"""
        # Import modifiers here to avoid circular imports
        from .modifiers import AVAILABLE_MODIFIERS

        self._modifiers = {
            mod.__name__.lower().replace("modifier", ""): mod
            for mod in AVAILABLE_MODIFIERS
        }
        logger.info(f"Registered {len(self._modifiers)} modifiers")

    def update(self, time_ms: float) -> Optional[np.ndarray]:
        """Generate pattern frame and send via WebSocket"""
        if not self.current_pattern:
            return None

        try:
            # Generate base pattern
            frame = self.current_pattern.generate(
                time_ms, self.current_config.parameters
            )

            # Apply modifiers if configured
            if self.current_config and self.current_config.modifiers:
                for modifier_config in self.current_config.modifiers:
                    modifier = self._modifiers.get(modifier_config["name"])
                    if modifier and modifier_config.get("enabled", True):
                        params = modifier_config.get("parameters", {})
                        frame = modifier.apply(frame, params)

            # Send frame via WebSocket
            ws_manager.broadcast(
                {
                    "type": "pattern",
                    "data": {"frame": frame.tolist(), "timestamp": time_ms},
                }
            )

            return frame

        except Exception as e:
            logger.error(f"Pattern update error: {e}")
            return None

    def cleanup(self) -> None:
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
            ws_manager.broadcast({"type": "clear"})

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    def __del__(self) -> None:
        """Ensure cleanup on deletion"""
        self.cleanup()

    def validate_parameters(
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

            # Options checking
            if hasattr(spec, "options") and value not in spec.options:
                raise ValidationError(
                    f"Invalid value for {name}. Must be one of: {spec.options}"
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

    def set_pattern(self, config: PatternConfig) -> None:
        """Set and validate pattern configuration"""
        if config.name not in self._patterns:
            raise ValidationError(f"Pattern {config.name} not found")

        pattern_class = self._patterns[config.name]

        # Validate pattern parameters
        validated_params = self.validate_parameters(pattern_class, config.parameters)

        # Validate modifiers
        if config.modifiers:
            for modifier in config.modifiers:
                self.validate_modifier_config(pattern_class, modifier)

        # Apply validated configuration
        self.current_pattern = pattern_class(self._num_pixels)
        self.current_config = PatternConfig(
            name=config.name, parameters=validated_params, modifiers=config.modifiers
        )
        self.current_pattern.reset()

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

    def get_available_patterns(self) -> List[Dict[str, Any]]:
        """Get list of available patterns with metadata"""
        return [
            {
                "name": name,
                "description": pattern_cls.__doc__ or "",
                "parameters": self._get_parameters_metadata(pattern_cls),
                "supported_modifiers": self._get_supported_modifiers(pattern_cls),
            }
            for name, pattern_cls in self._patterns.items()
        ]

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
