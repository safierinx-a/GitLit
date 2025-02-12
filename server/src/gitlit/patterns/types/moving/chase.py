from typing import Any, Dict, List

import numpy as np

from ...base import BasePattern, ColorSpec, Parameter


class ChasePattern(BasePattern):
    """Moving dots that chase each other along the strip"""

    name = "chase"
    description = "Moving dots that chase each other along the strip"

    parameters = [
        Parameter(
            name="speed",
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=5.0,
            description="Chase speed",
            units="Hz",
        ),
        Parameter(
            name="count",
            type=int,
            default=3,
            min_value=1,
            max_value=10,
            description="Number of chase dots",
        ),
        Parameter(
            name="size",
            type=int,
            default=2,
            min_value=1,
            max_value=10,
            description="Size of each dot",
        ),
        ColorSpec(name="red", description="Red component of dot color"),
        ColorSpec(name="green", description="Green component of dot color"),
        ColorSpec(name="blue", description="Blue component of dot color"),
        Parameter(
            name="fade",
            type=float,
            default=0.5,
            min_value=0.0,
            max_value=1.0,
            description="Trail fade length",
        ),
        Parameter(
            name="spacing",
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=2.0,
            description="Spacing between dots",
        ),
    ]

    async def _generate(self, time_ms: float) -> np.ndarray:
        """Generate chase pattern frame"""
        # Get parameters from state
        speed = self.state.parameters.get("speed", 1.0)
        count = self.state.parameters.get("count", 3)
        size = self.state.parameters.get("size", 2)
        fade = self.state.parameters.get("fade", 0.5)
        spacing = self.state.parameters.get("spacing", 1.0)

        # Get color components
        red = self.state.parameters.get("red", 255)
        green = self.state.parameters.get("green", 0)
        blue = self.state.parameters.get("blue", 0)
        color = np.array([red, green, blue], dtype=np.uint8)

        # Calculate positions
        t = (time_ms / 1000.0) * speed
        positions = [(i / count + t) % 1.0 for i in range(count)]

        # Initialize frame buffer
        self.frame_buffer.fill(0)

        # Draw chase dots
        for pos in positions:
            # Calculate LED indices affected by this dot
            center_idx = int(pos * self.num_leds)
            for i in range(-size, size + 1):
                idx = (center_idx + i) % self.num_leds
                # Calculate fade based on distance from center
                dist = abs(i) / size
                brightness = 1.0 - (dist * fade)
                if brightness > 0:
                    self.frame_buffer[idx] = (color * brightness).astype(np.uint8)

        return self.frame_buffer
