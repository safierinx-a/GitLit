from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

import numpy as np

from ..core.exceptions import PatternError
from ..core.state import PatternState
from ..core.timing import TimeState


@dataclass
class ParameterSpec:
    """Specification for a pattern parameter"""

    name: str
    type: type
    default: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    description: str = ""
    units: str = ""  # e.g., "Hz", "ms", "%"


@dataclass
class ColorSpec(ParameterSpec):
    """Specification for color parameters"""

    def __init__(self, name: str, description: str = ""):
        super().__init__(
            name=name,
            type=int,
            default=0,
            min_value=0,
            max_value=255,
            description=description,
        )


@dataclass
class ModifiableAttribute:
    """Defines an aspect of the pattern that can be modified"""

    name: str  # e.g., 'color', 'timing', 'position'
    description: str
    parameter_specs: List[ParameterSpec]  # Parameters this attribute exposes
    supports_audio: bool = False  # Can this be audio reactive?


class BasePattern(ABC):
    """Abstract base class for all patterns"""

    def __init__(self, led_count: int):
        self.led_count = led_count
        self.frame_buffer = np.zeros((led_count, 3), dtype=np.uint8)
        self.state = PatternState()
        self.timing = TimeState()

    @classmethod
    @property
    def name(cls) -> str:
        """Pattern name"""
        return cls.__name__.replace("Pattern", "")

    @classmethod
    @property
    def description(cls) -> str:
        """Pattern description"""
        return cls.__doc__ or ""

    @classmethod
    @property
    def parameters(cls) -> List[ParameterSpec]:
        """Define pattern parameters"""
        return []

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        """Define which aspects can be modified"""
        return []

    def before_generate(self, time_ms: float, params: Dict[str, Any]) -> None:
        """Pre-generation hook for state updates"""
        self.state.update(time_ms)
        self.state.parameters = params.copy()
        self.timing.update(time_ms)
        speed = params.get("speed", 1.0)
        self.timing.time_scale = speed

    def after_generate(self, time_ms: float, params: Dict[str, Any]) -> None:
        """Post-generation hook for cleanup and metrics"""
        # Update performance metrics
        if len(self.state.frame_times) > 60:
            self.state.frame_times.pop(0)
        self.state.frame_times.append(self.state.delta_time)
        self.state.avg_frame_time = sum(self.state.frame_times) / len(
            self.state.frame_times
        )

    def generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate pattern frame with complete state management"""
        try:
            # Pre-generation state update
            self.before_generate(time_ms, params)

            # Generate frame
            frame = self._generate(time_ms, params)

            # Post-generation cleanup
            self.after_generate(time_ms, params)

            return frame

        except Exception as e:
            raise PatternError(f"Pattern generation failed: {e}")

    def reset(self) -> None:
        """Reset pattern state"""
        self.frame_buffer.fill(0)
        self.state.reset()

    @abstractmethod
    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate pattern frame"""
        pass
