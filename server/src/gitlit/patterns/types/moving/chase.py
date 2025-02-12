from typing import Any, Dict, List

import numpy as np

from ...base import BasePattern, ColorSpec, ModifiableAttribute, ParameterSpec


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
        """Generate chase pattern using state"""
        speed = params.get("speed", 1.0)
        count = params.get("count", 3)
        width = params.get("width", 0.2)
        color = [params.get("red", 255), params.get("green", 0), params.get("blue", 0)]

        # Calculate spacing between segments
        spacing = 1.0 / count

        # Use normalized time from state
        t = self.state.get_normalized_time(time_ms * speed)

        # Generate chase segments
        for i in range(self.led_count):
            pos = (i / self.led_count + t) % 1.0
            for j in range(count):
                segment_pos = j / count
                dist = min(abs(pos - segment_pos), abs(pos - segment_pos - 1))
                if dist < width / 2:
                    brightness = 1.0 - (dist / (width / 2))
                    self.frame_buffer[i] = [int(c * brightness) for c in color]
                    break
            else:
                self.frame_buffer[i] = [0, 0, 0]

        return self.frame_buffer
