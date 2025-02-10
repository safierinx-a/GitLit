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
        """Generate a moving rainbow pattern"""
        # Get parameters with validation
        speed = np.clip(params.get("speed", 1.0), 0.1, 5.0)
        scale = np.clip(params.get("scale", 1.0), 0.1, 5.0)
        saturation = np.clip(params.get("saturation", 1.0), 0.0, 1.0)

        # Calculate time offset
        t = (time_ms / 1000.0 * speed) % 1.0

        # Generate hues for all LEDs at once
        positions = np.linspace(0, 1, self.led_count)
        hues = (positions * scale + t) % 1.0

        # Create RGB array
        frame = np.zeros((self.led_count, 3), dtype=np.uint8)

        # Convert HSV to RGB for each LED
        for i in range(self.led_count):
            h = hues[i]
            s = saturation
            v = 1.0

            h_i = int(h * 6)
            f = h * 6 - h_i
            p = v * (1 - s)
            q = v * (1 - f * s)
            t = v * (1 - (1 - f) * s)

            if h_i == 0:
                r, g, b = v, t, p
            elif h_i == 1:
                r, g, b = q, v, p
            elif h_i == 2:
                r, g, b = p, v, t
            elif h_i == 3:
                r, g, b = p, q, v
            elif h_i == 4:
                r, g, b = t, p, v
            else:
                r, g, b = v, p, q

            frame[i] = [int(r * 255), int(g * 255), int(b * 255)]

        return frame

    def _hsv_to_rgb_vectorized(self, hsv: np.ndarray) -> np.ndarray:
        """Convert HSV colors to RGB efficiently"""
        h, s, v = hsv[:, 0], hsv[:, 1], hsv[:, 2]

        h = (h * 6.0) % 6.0
        i = h.astype(np.int32)
        f = h - i

        p = v * (1.0 - s)
        q = v * (1.0 - s * f)
        t = v * (1.0 - s * (1.0 - f))

        i = i.reshape(-1, 1) % 6
        v = v.reshape(-1, 1)
        p = p.reshape(-1, 1)
        q = q.reshape(-1, 1)
        t = t.reshape(-1, 1)

        mask = np.zeros((len(h), 3))
        mask[i == 0] = [1, 0, 0]
        mask[i == 1] = [0, 1, 0]
        mask[i == 2] = [0, 0, 1]
        mask[i == 3] = [0, 0, 1]
        mask[i == 4] = [0, 1, 0]
        mask[i == 5] = [1, 0, 0]

        rgb = np.where(mask == 1, v, np.where(mask == 0, p, np.where(i % 2 == 0, t, q)))

        return (rgb * 255).astype(np.uint8)

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
