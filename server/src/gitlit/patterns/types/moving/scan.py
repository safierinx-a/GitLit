from typing import Any, Dict, List

import numpy as np

from ...base import BasePattern, ColorSpec, ModifiableAttribute, Parameter


class ScanPattern(BasePattern):
    """Moving light bar that scans back and forth"""

    name = "scan"
    description = "Moving light bar that scans back and forth"

    parameters = [
        Parameter(
            name="speed",
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=5.0,
            description="Scan movement speed",
            units="Hz",
        ),
        Parameter(
            name="width",
            type=int,
            default=3,
            min_value=1,
            max_value=20,
            description="Width of scanning bar",
        ),
        ColorSpec(name="red", description="Red component of scan color"),
        ColorSpec(name="green", description="Green component of scan color"),
        ColorSpec(name="blue", description="Blue component of scan color"),
        Parameter(
            name="fade",
            type=float,
            default=0.3,
            min_value=0.0,
            max_value=1.0,
            description="Trail fade amount",
        ),
        Parameter(
            name="bounce",
            type=bool,
            default=True,
            description="Whether to bounce at ends or wrap around",
        ),
        Parameter(
            name="wrap",
            type=bool,
            default=False,
            description="Whether to wrap around at ends",
        ),
    ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        width = params.get("width", 3)
        fade = params.get("fade", 0.3)
        bounce = params.get("bounce", True)
        color = np.array(
            [params.get("red", 255), params.get("green", 255), params.get("blue", 255)],
            dtype=np.uint8,
        )

        # Use timing system for smooth movement
        if bounce:
            t = self.timing.get_bounce()  # 0-1-0 motion
        else:
            t = self.timing.get_phase()  # 0-1 motion

        # Calculate center position
        center = int(t * (self.led_count - 1))

        # Clear buffer
        self.frame_buffer.fill(0)

        # Draw scan bar with fade
        for i in range(max(0, center - width), min(self.led_count, center + width + 1)):
            distance = abs(i - center)
            intensity = 1.0 - (distance / width) ** (1.0 / fade) if fade > 0 else 1.0
            self.frame_buffer[i] = (color * intensity).astype(np.uint8)

        return self.frame_buffer
