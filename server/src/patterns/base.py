from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union, ClassVar, Tuple
import time
import logging
import numpy as np

from ..common.exceptions import PatternError, ValidationError
from ..common.timing import TimeState
from .config import PatternState

logger = logging.getLogger(__name__)


@dataclass
class PatternMetrics:
    """Pattern performance metrics"""

    generation_time_ms: float = 0.0
    state_update_time_ms: float = 0.0
    frame_count: int = 0
    error_count: int = 0
    last_error: str = ""
    parameter_updates: int = 0


@dataclass
class Parameter:
    """Pattern parameter definition with validation"""

    name: str
    type: type
    default: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    description: str = ""
    units: str = ""

    def validate(self, value: Any) -> Any:
        """Validate and normalize parameter value"""
        try:
            # Type conversion
            value = self.type(value)

            # Range validation
            if self.min_value is not None and value < self.min_value:
                logger.warning(
                    f"Clamping {self.name} to minimum value {self.min_value}"
                )
                value = self.min_value
            if self.max_value is not None and value > self.max_value:
                logger.warning(
                    f"Clamping {self.name} to maximum value {self.max_value}"
                )
                value = self.max_value

            return value

        except (ValueError, TypeError) as e:
            raise ValidationError(
                f"Invalid value for parameter {self.name}: {value}. {str(e)}"
            )


@dataclass
class ColorSpec(Parameter):
    """Specification for a color parameter"""

    def __init__(
        self,
        name: str,
        description: str = "",
        default: int = 0,
        min_value: int = 0,
        max_value: int = 255,
    ):
        super().__init__(
            name=name,
            type=int,
            description=description,
            default=default,
            min_value=min_value,
            max_value=max_value,
        )


@dataclass
class ModifiableAttribute:
    """Defines an aspect of the pattern that can be modified"""

    name: str  # e.g., 'color', 'timing', 'position'
    description: str
    parameter_specs: List[Parameter]  # Parameters this attribute exposes
    supports_audio: bool = False  # Can this be audio reactive?


@dataclass
class PatternState:
    """Pattern state with improved validation"""

    # Basic state
    parameters: Dict[str, Any] = field(default_factory=dict)
    frame_count: int = 0
    is_transitioning: bool = False

    # Timing
    start_time: float = field(default_factory=time.perf_counter)
    last_update: float = 0.0
    delta_time: float = 0.0

    # Performance tracking
    metrics: PatternMetrics = field(default_factory=PatternMetrics)

    # Cached computations
    cache: Dict[str, Any] = field(default_factory=dict)

    def update(self, current_time: float) -> None:
        """Update pattern state"""
        # Update timing
        if self.last_update > 0:
            self.delta_time = current_time - self.last_update
        self.last_update = current_time

        # Update counters
        self.frame_count += 1
        self.metrics.frame_count = self.frame_count

    def reset(self) -> None:
        """Reset pattern state"""
        self.frame_count = 0
        self.last_update = 0
        self.delta_time = 0
        self.start_time = time.perf_counter()
        self.cache.clear()
        self.metrics = PatternMetrics()


class BasePattern(ABC):
    """Base class for all patterns with improved state management"""

    # Class-level pattern metadata
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    parameters: ClassVar[List[Parameter]] = []

    def __init__(self, num_leds: int):
        """Initialize pattern"""
        self.num_leds = num_leds
        self.state = PatternState()
        self.frame_buffer = np.zeros((num_leds, 3), dtype=np.uint8)
        self._last_valid_frame = None

        # Initialize with default parameters
        self._init_parameters()

    def _init_parameters(self) -> None:
        """Initialize pattern parameters with defaults"""
        self.state.parameters = {param.name: param.default for param in self.parameters}

    async def update_parameters(self, params: Dict[str, Any]) -> None:
        """Update pattern parameters with validation"""
        start_time = time.perf_counter()
        try:
            # Validate parameters
            validated = {}
            for name, value in params.items():
                param_def = self._get_parameter_def(name)
                if param_def:
                    validated[name] = param_def.validate(value)
                else:
                    logger.warning(f"Unknown parameter: {name}")

            # Update state
            self.state.parameters.update(validated)
            self.state.metrics.parameter_updates += 1

            # Test generate one frame
            test_frame = await self.generate(time.perf_counter() * 1000)
            if test_frame is None:
                raise ValidationError(
                    "Failed to generate test frame with new parameters"
                )

        except Exception as e:
            self.state.metrics.error_count += 1
            self.state.metrics.last_error = str(e)
            raise

        finally:
            self.state.metrics.state_update_time_ms = (
                time.perf_counter() - start_time
            ) * 1000

    def _get_parameter_def(self, name: str) -> Optional[Parameter]:
        """Get parameter definition by name"""
        return next((p for p in self.parameters if p.name == name), None)

    async def generate(self, time_ms: float) -> Optional[np.ndarray]:
        """Generate pattern frame with error handling"""
        start_time = time.perf_counter()

        try:
            # Import TimeState here to avoid circular import
            from ..core.timing import TimeState

            # Update state
            self.state.update(time_ms / 1000.0)

            # Generate frame
            frame = await self._generate(time_ms)

            # Validate frame
            if frame is None:
                raise PatternError("Pattern generated None frame")
            if not isinstance(frame, np.ndarray):
                raise PatternError(f"Invalid frame type: {type(frame)}")
            if frame.shape != (self.num_leds, 3):
                raise PatternError(
                    f"Invalid frame shape: {frame.shape}, expected ({self.num_leds}, 3)"
                )

            # Store last valid frame
            self._last_valid_frame = frame.copy()

            # Ensure frame values are in valid range
            return np.clip(frame, 0, 255).astype(np.uint8)

        except Exception as e:
            self.state.metrics.error_count += 1
            self.state.metrics.last_error = str(e)
            logger.error(f"Frame generation failed: {e}")
            return (
                self._last_valid_frame
                if self._last_valid_frame is not None
                else np.zeros((self.num_leds, 3), dtype=np.uint8)
            )

        finally:
            self.state.metrics.generation_time_ms = (
                time.perf_counter() - start_time
            ) * 1000

    @abstractmethod
    async def _generate(self, time_ms: float) -> np.ndarray:
        """Generate pattern frame"""
        pass

    def get_state(self) -> Dict[str, Any]:
        """Get pattern state"""
        return {
            "name": self.name,
            "parameters": self.state.parameters.copy(),
            "frame_count": self.state.frame_count,
            "is_transitioning": self.state.is_transitioning,
            "metrics": {
                "generation_time_ms": self.state.metrics.generation_time_ms,
                "state_update_time_ms": self.state.metrics.state_update_time_ms,
                "frame_count": self.state.metrics.frame_count,
                "error_count": self.state.metrics.error_count,
                "last_error": self.state.metrics.last_error,
                "parameter_updates": self.state.metrics.parameter_updates,
            },
        }
