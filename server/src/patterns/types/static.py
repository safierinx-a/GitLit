from typing import Dict, Any, List
import numpy as np
from ...core.exceptions import ValidationError
from ..base import BasePattern, ParameterSpec, ModifiableAttribute, ColorSpec


class SolidPattern(BasePattern):
    """Single solid color across all LEDs"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data["last_color"] = [0, 0, 0]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate solid color pattern"""
        color = [params.get("red", 0), params.get("green", 0), params.get("blue", 0)]

        # Cache current color for transitions
        self.state.cache_value("last_color", color)

        # Fill buffer with color
        self.frame_buffer.fill(color)
        return self.frame_buffer


class GradientPattern(BasePattern):
    """Linear gradient between two colors"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data["last_color1"] = [0, 0, 0]
        self.state.cached_data["last_color2"] = [0, 0, 0]
        self.state.cached_data["last_position"] = 0.5

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate gradient pattern"""
        color1 = [
            params.get("color1_r", 0),
            params.get("color1_g", 0),
            params.get("color1_b", 0),
        ]
        color2 = [
            params.get("color2_r", 0),
            params.get("color2_g", 0),
            params.get("color2_b", 0),
        ]
        position = params.get("position", 0.5)

        # Cache values for transitions
        self.state.cache_value("last_color1", color1)
        self.state.cache_value("last_color2", color2)
        self.state.cache_value("last_position", position)

        # Generate gradient
        for i in range(self.led_count):
            t = i / (self.led_count - 1)
            t = max(0, min(1, (t - position + 0.5)))
            self.frame_buffer[i] = [
                int(color1[j] * (1 - t) + color2[j] * t) for j in range(3)
            ]

        return self.frame_buffer
