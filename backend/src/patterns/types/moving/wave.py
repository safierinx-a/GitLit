from ...base import BasePattern, ParameterSpec, ModifiableAttribute, ColorSpec
import numpy as np
from typing import Dict, Any, List
import math


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
            ParameterSpec(
                name="amplitude",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=5.0,
                description="Amplitude of the wave",
                units="",
            ),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        wavelength = params.get("wavelength", 1.0)
        amplitude = params.get("amplitude", 1.0)
        color = np.array(
            [params.get("red", 255), params.get("green", 0), params.get("blue", 0)],
            dtype=np.uint8,
        )

        # Use timing system directly for consistent period
        t = self.timing.get_phase()  # Already handles speed scaling

        for i in range(self.led_count):
            phase = (i / self.led_count) * wavelength * 2 * math.pi
            brightness = ((math.sin(phase + t * 2 * math.pi) + 1) / 2) * amplitude
            self.frame_buffer[i] = (color * brightness).astype(np.uint8)

        return self.frame_buffer
