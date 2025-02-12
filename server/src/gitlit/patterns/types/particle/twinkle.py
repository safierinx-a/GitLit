import random
from typing import Any, Dict, List

import numpy as np

from ...base import BasePattern, ColorSpec, Parameter


class TwinklePattern(BasePattern):
    """Random twinkling lights that fade in and out"""

    name = "twinkle"
    description = "Random twinkling lights that fade in and out"

    parameters = [
        ColorSpec(name="red", description="Red component"),
        ColorSpec(name="green", description="Green component"),
        ColorSpec(name="blue", description="Blue component"),
        Parameter(
            name="density",
            type=float,
            default=0.1,
            min_value=0.0,
            max_value=1.0,
            description="Density of twinkles",
        ),
        Parameter(
            name="fade_speed",
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=5.0,
            description="Speed of fade in/out",
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

    def __init__(self, led_count: int):
        """Initialize twinkle pattern"""
        super().__init__(led_count)
        self.twinkles = np.zeros(led_count, dtype=np.float32)
        self.phases = np.random.random(led_count)
        self.state.cached_data["last_density"] = 0.1
        self.state.cached_data["last_fade_speed"] = 1.0

    async def _generate(self, time_ms: float) -> np.ndarray:
        """Generate twinkle pattern frame"""
        # Get parameters from state
        density = self.state.parameters.get("density", 0.1)
        fade_speed = self.state.parameters.get("fade_speed", 1.0)
        min_bright = self.state.parameters.get("min_brightness", 0.0)
        max_bright = self.state.parameters.get("max_brightness", 1.0)

        # Get color components
        red = self.state.parameters.get("red", 255)
        green = self.state.parameters.get("green", 255)
        blue = self.state.parameters.get("blue", 255)
        color = np.array([red, green, blue], dtype=np.uint8)

        # Update twinkles
        t = (time_ms / 1000.0) * fade_speed
        self.phases = (self.phases + 0.1) % 1.0

        # Randomly add new twinkles
        mask = np.random.random(self.led_count) < density
        self.twinkles[mask] = 1.0

        # Calculate brightness
        brightness = (np.sin(self.phases * 2 * np.pi) + 1) / 2
        brightness = min_bright + (max_bright - min_bright) * brightness
        brightness *= self.twinkles

        # Apply brightness to color
        self.frame_buffer = (color[None, :] * brightness[:, None]).astype(np.uint8)

        # Fade out twinkles
        self.twinkles *= 0.95

        return self.frame_buffer
