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
            raise ValidationError(f"Invalid value for {self.name}: {value} ({str(e)})")


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
    """Base class for all patterns"""

    name: str = "base"
    description: str = "Base pattern class"
    parameters: ClassVar[List[Parameter]] = []

    def __init__(self, led_count: int):
        """Initialize pattern"""
        self.led_count = led_count
        self.num_leds = led_count  # For backwards compatibility
        self.frame_buffer = np.zeros((led_count, 3), dtype=np.uint8)
        self.state = PatternState()
        self.state.cached_data = {}  # Initialize cached_data dict
        self.metrics = PatternMetrics()
        self.timing = TimeState()

    @abstractmethod
    async def _generate(self, time_ms: float) -> np.ndarray:
        """Generate pattern frame"""
        pass

    async def generate(
        self, time_ms: float, params: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """Public method to generate a frame"""
        if params:
            self.state.parameters.update(params)
        return await self._generate(time_ms)

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
