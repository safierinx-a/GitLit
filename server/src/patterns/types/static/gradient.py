from typing import Any, Dict, List

import numpy as np

from ...base import BasePattern, ColorSpec, ModifiableAttribute, ParameterSpec


class GradientPattern(BasePattern):
    """Linear gradient between two colors"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data["last_color1"] = [0, 0, 0]
        self.state.cached_data["last_color2"] = [0, 0, 0]
        self.state.cached_data["last_position"] = 0.5

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate a gradient between two colors"""
        # Get color parameters with validation
        color1 = [
            np.clip(params.get("color1_r", 0), 0, 255),
            np.clip(params.get("color1_g", 0), 0, 255),
            np.clip(params.get("color1_b", 0), 0, 255),
        ]
        color2 = [
            np.clip(params.get("color2_r", 0), 0, 255),
            np.clip(params.get("color2_g", 0), 0, 255),
            np.clip(params.get("color2_b", 0), 0, 255),
        ]
        position = np.clip(params.get("position", 0.5), 0.0, 1.0)

        # Cache values for modifiers
        self.state.cache_value("last_color1", color1)
        self.state.cache_value("last_color2", color2)
        self.state.cache_value("last_position", position)

        # Create gradient
        t = np.linspace(0, 1, self.led_count)
        t = np.clip((t - position + 0.5), 0, 1)[:, np.newaxis]

        # Interpolate colors
        color1 = np.array(color1, dtype=np.uint8)
        color2 = np.array(color2, dtype=np.uint8)
        frame = ((1 - t) * color1 + t * color2).astype(np.uint8)

        return frame
