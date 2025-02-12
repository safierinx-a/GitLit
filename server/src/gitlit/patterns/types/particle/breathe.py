"""Breathing light pattern implementation."""

import numpy as np
from typing import List

from ...base import BasePattern, ColorSpec, Parameter


class BreathePattern(BasePattern):
    """Smooth breathing light effect"""

    name = "breathe"
    description = "Smooth breathing light effect"

    parameters = [
        ColorSpec(name="red", description="Red component"),
        ColorSpec(name="green", description="Green component"),
        ColorSpec(name="blue", description="Blue component"),
        Parameter(
            name="speed",
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=5.0,
            description="Breathing speed",
            units="Hz",
        ),
        Parameter(
            name="min_brightness",
            type=float,
            default=0.0,
            min_value=0.0,
            max_value=1.0,
            description="Minimum brightness",
        ),
        Parameter(
            name="max_brightness",
            type=float,
            default=1.0,
            min_value=0.0,
            max_value=1.0,
            description="Maximum brightness",
        ),
    ]

    async def _generate(self, time_ms: float) -> np.ndarray:
        """Generate breathing pattern frame"""
        # Get parameters from state
        speed = self.state.parameters.get("speed", 1.0)
        min_bright = self.state.parameters.get("min_brightness", 0.0)
        max_bright = self.state.parameters.get("max_brightness", 1.0)

        # Get color components
        red = self.state.parameters.get("red", 255)
        green = self.state.parameters.get("green", 0)
        blue = self.state.parameters.get("blue", 0)
        color = np.array([red, green, blue], dtype=np.uint8)

        # Calculate brightness using sine wave
        t = (time_ms / 1000.0) * speed
        brightness = (np.sin(t * 2 * np.pi) + 1) / 2  # 0 to 1
        brightness = min_bright + (max_bright - min_bright) * brightness

        # Apply brightness to color
        self.frame_buffer.fill(0)
        self.frame_buffer[:] = (color * brightness).astype(np.uint8)

        return self.frame_buffer
