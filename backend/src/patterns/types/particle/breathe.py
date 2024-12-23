from ...base import BasePattern, ParameterSpec, ModifiableAttribute, ColorSpec
import numpy as np
from typing import Dict, Any, List
import math


class BreathePattern(BasePattern):
    """Smooth breathing effect that pulses the entire strip"""

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
                description="Breathing speed",
                units="Hz",
            ),
            ParameterSpec(
                name="min_brightness",
                type=float,
                default=0.0,
                min_value=0.0,
                max_value=1.0,
                description="Minimum brightness",
            ),
            ParameterSpec(
                name="max_brightness",
                type=float,
                default=1.0,
                min_value=0.0,
                max_value=1.0,
                description="Maximum brightness",
            ),
            ParameterSpec(
                name="curve",
                type=str,
                default="sine",
                description="Breathing curve type",
                options=["sine", "triangle", "exponential"],
            ),
            ParameterSpec(
                name="hold_time",
                type=float,
                default=0.0,
                min_value=0.0,
                max_value=1.0,
                description="Time to hold at peaks",
            ),
            ColorSpec(name="red", description="Red component of color"),
            ColorSpec(name="green", description="Green component of color"),
            ColorSpec(name="blue", description="Blue component of color"),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        min_bright = params.get("min_brightness", 0.0)
        max_bright = params.get("max_brightness", 1.0)
        curve = params.get("curve", "sine")
        hold_time = params.get("hold_time", 0.0)
        color = np.array(
            [params.get("red", 255), params.get("green", 255), params.get("blue", 255)],
            dtype=np.uint8,
        )

        t = self.timing.get_phase()

        if curve == "sine":
            brightness = (math.sin(t * 2 * math.pi) + 1) / 2
        elif curve == "triangle":
            brightness = 1.0 - abs(2.0 * t - 1.0)
        else:  # exponential
            if t < 0.5:
                brightness = math.pow(t * 2, 2)
            else:
                brightness = math.pow((1.0 - t) * 2, 2)

        if hold_time > 0:
            if abs(brightness - 1.0) < 0.1 or abs(brightness) < 0.1:
                brightness = round(brightness)

        brightness = min_bright + (max_bright - min_bright) * brightness
        self.frame_buffer[:] = (color * brightness).astype(np.uint8)
        return self.frame_buffer
