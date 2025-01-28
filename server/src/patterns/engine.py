from typing import Dict, Any, Optional, List, Type
from dataclasses import asdict
import logging
import numpy as np

from ..core.config import PatternConfig
from ..core.state import PatternState
from ..core.exceptions import ValidationError
from ..led.controller import LEDController
from .base import BasePattern, ParameterSpec, ModifiableAttribute, BaseModifier
from .types import (
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
from ..audio.processor import AudioProcessor

logger = logging.getLogger(__name__)


class PatternEngine:
    """Manages pattern execution and validation"""

    def __init__(self, led_controller: LEDController):
        self.led_controller = led_controller
        self.patterns: Dict[str, BasePattern] = {}
        self.current_pattern: Optional[BasePattern] = None
        self.current_config: Optional[PatternConfig] = None
        self.state = PatternState()
        self.audio_processor = AudioProcessor()
        self._register_patterns()

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
            self.patterns[name] = pattern_class(self.led_controller.config.led_count)
            logger.info(f"Registered pattern: {name}")

    def update(self, time_ms: float) -> Optional[np.ndarray]:
        """Update pattern and apply modifiers"""
        if not self.ui_state.active_pattern:
            return None

        # Generate base pattern
        frame = self.ui_state.active_pattern.generate(
            time_ms, self.ui_state.pattern_params
        )

        # Apply modifiers with audio if enabled
        if self.ui_state.audio_enabled:
            audio_metrics = self.audio_processor.process_audio(
                self.audio_processor.buffer
            )

            # Apply audio-bound modifiers
            for binding in self.ui_state.audio_bindings:
                if binding.modifier.enabled:
                    value = audio_metrics[binding.audio_metric]
                    value = value * binding.scale + binding.offset
                    params = {binding.parameter: value}
                    frame = binding.modifier.apply(frame, params)

        return frame

    def _update_leds(self, frame: np.ndarray) -> None:
        """Update LED strip with safety checks"""
        try:
            for i in range(len(frame)):
                self.led_controller.set_pixel(i, *frame[i])
            self.led_controller.show()
        except Exception as e:
            logger.error(f"LED update failed: {e}")
            self.led_controller.emergency_stop()

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
        if config.name not in self.patterns:
            raise ValidationError(f"Pattern {config.name} not found")

        pattern_class = self.patterns[config.name].__class__

        # Validate pattern parameters
        validated_params = self.validate_parameters(pattern_class, config.parameters)

        # Validate modifiers
        if config.modifiers:
            for modifier in config.modifiers:
                self.validate_modifier_config(pattern_class, modifier)

        # Apply validated configuration
        self.current_pattern = self.patterns[config.name]
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
