import math
from typing import Any, Dict, List

import numpy as np

from ...core.exceptions import ValidationError
from ..base import BasePattern, ColorSpec, ModifiableAttribute, ParameterSpec


class WavePattern(BasePattern):
    """Sinusoidal wave pattern"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data.update(
            {
                "last_wavelength": 1.0,
                "last_speed": 1.0,
                "last_color": [255, 0, 0],
                "last_phase": 0.0,
            }
        )

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate wave pattern using state"""
        speed = params.get("speed", 1.0)
        wavelength = params.get("wavelength", 1.0)
        color = [params.get("red", 255), params.get("green", 0), params.get("blue", 0)]

        # Use normalized time from state
        t = self.state.get_normalized_time(time_ms * speed)

        # Cache current parameters for transitions
        self.state.cache_value("last_wavelength", wavelength)
        self.state.cache_value("last_speed", speed)
        self.state.cache_value("last_color", color)

        # Generate wave using cached values
        for i in range(self.led_count):
            phase = (i / self.led_count) * wavelength * 2 * math.pi
            brightness = (math.sin(phase + t * 2 * math.pi) + 1) / 2
            self.frame_buffer[i] = [int(c * brightness) for c in color]

        return self.frame_buffer

    @classmethod
    @property
    def parameters(cls) -> List[ParameterSpec]:
        return [
            ParameterSpec(
                name="speed",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=5.0,
                description="Wave movement speed",
                units="Hz",
            ),
            ParameterSpec(
                name="wavelength",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=5.0,
                description="Length of one complete wave",
                units="strips",
            ),
            ColorSpec(name="red", description="Red component of wave color"),
            ColorSpec(name="green", description="Green component of wave color"),
            ColorSpec(name="blue", description="Blue component of wave color"),
        ]

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        return [
            ModifiableAttribute(
                name="timing",
                description="Wave timing properties",
                parameter_specs=[
                    ParameterSpec(
                        name="speed_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Speed multiplier",
                    ),
                    ParameterSpec(
                        name="phase",
                        type=float,
                        default=0.0,
                        min_value=0.0,
                        max_value=1.0,
                        description="Wave phase offset",
                    ),
                ],
                supports_audio=True,  # Can sync to beat/BPM
            ),
            ModifiableAttribute(
                name="amplitude",
                description="Wave amplitude properties",
                parameter_specs=[
                    ParameterSpec(
                        name="amplitude_scale",
                        type=float,
                        default=1.0,
                        min_value=0.0,
                        max_value=2.0,
                        description="Wave height multiplier",
                    )
                ],
                supports_audio=True,  # Can react to volume
            ),
        ]
