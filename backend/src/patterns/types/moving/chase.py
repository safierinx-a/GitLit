from ...base import BasePattern, ParameterSpec, ModifiableAttribute, ColorSpec
import numpy as np
from typing import Dict, Any, List


class ChasePattern(BasePattern):
    """Moving dots that chase each other along the strip"""

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
                description="Chase speed",
                units="Hz",
            ),
            ParameterSpec(
                name="count",
                type=int,
                default=3,
                min_value=1,
                max_value=10,
                description="Number of chase dots",
            ),
            ParameterSpec(
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
            ParameterSpec(
                name="fade",
                type=float,
                default=0.5,
                min_value=0.0,
                max_value=1.0,
                description="Trail fade length",
            ),
            ParameterSpec(
                name="spacing",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=2.0,
                description="Spacing between dots",
            ),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        count = params.get("count", 3)
        size = params.get("size", 2)
        spacing = params.get("spacing", 1.0)
        fade = params.get("fade", 0.5)
        color = np.array(
            [params.get("red", 255), params.get("green", 0), params.get("blue", 0)],
            dtype=np.uint8,
        )

        self.frame_buffer.fill(0)

        # Use timing system for movement
        t = self.timing.get_phase()

        # Draw each chase dot
        for i in range(count):
            phase = (t + (i / count)) % 1.0
            pos = int(phase * self.led_count)

            # Draw dot and trail
            for j in range(size + int(size * fade)):
                pixel_pos = (pos - j) % self.led_count
                intensity = 1.0 if j < size else 1.0 - ((j - size) / (size * fade))
                self.frame_buffer[pixel_pos] = (color * intensity).astype(np.uint8)

        return self.frame_buffer
