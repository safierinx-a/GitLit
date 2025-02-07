from typing import Any, Dict, List

import numpy as np

from ...base import BasePattern, ModifiableAttribute, ParameterSpec


class RainbowPattern(BasePattern):
    """Moving rainbow pattern across the strip"""

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
                description="Rainbow movement speed",
                units="Hz",
            ),
            ParameterSpec(
                name="scale",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=5.0,
                description="Number of rainbow repetitions",
                units="cycles",
            ),
            ParameterSpec(
                name="saturation",
                type=float,
                default=1.0,
                min_value=0.0,
                max_value=1.0,
                description="Color saturation",
            ),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        speed = params.get("speed", 1.0)
        scale = params.get("scale", 1.0)
        saturation = params.get("saturation", 1.0)

        t = (time_ms / 1000.0 * speed) % 1.0

        for i in range(self.led_count):
            hue = ((i / self.led_count) * scale + t) % 1.0
            self._hsv_to_rgb(hue, saturation, 1.0, i)

        return self.frame_buffer

    def _hsv_to_rgb(self, h: float, s: float, v: float, index: int) -> None:
        if s == 0.0:
            self.frame_buffer[index] = [int(v * 255)] * 3
            return

        h *= 6.0
        i = int(h)
        f = h - i
        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        if i == 0:
            rgb = [v, t, p]
        elif i == 1:
            rgb = [q, v, p]
        elif i == 2:
            rgb = [p, v, t]
        elif i == 3:
            rgb = [p, q, v]
        elif i == 4:
            rgb = [t, p, v]
        else:
            rgb = [v, p, q]

        self.frame_buffer[index] = [int(c * 255) for c in rgb]
