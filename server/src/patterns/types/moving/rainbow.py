from typing import Any, Dict, List
import numpy as np
import colorsys

from ...base import BasePattern, ModifiableAttribute, ParameterSpec


class RainbowPattern(BasePattern):
    """Moving rainbow pattern across the strip with enhanced color control"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data.update(
            {
                "last_speed": 1.0,
                "last_scale": 1.0,
                "last_saturation": 1.0,
                "last_value": 1.0,
                "last_offset": 0.0,
                "last_wave_amplitude": 0.0,
            }
        )

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
            ParameterSpec(
                name="value",
                type=float,
                default=1.0,
                min_value=0.0,
                max_value=1.0,
                description="Color brightness",
            ),
            ParameterSpec(
                name="offset",
                type=float,
                default=0.0,
                min_value=0.0,
                max_value=1.0,
                description="Color wheel offset",
            ),
            ParameterSpec(
                name="reverse",
                type=bool,
                default=False,
                description="Reverse rainbow direction",
            ),
            ParameterSpec(
                name="wave_amplitude",
                type=float,
                default=0.0,
                min_value=0.0,
                max_value=1.0,
                description="Wave motion amplitude",
            ),
        ]

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        return [
            ModifiableAttribute(
                name="color",
                description="Rainbow color properties",
                parameter_specs=[
                    ParameterSpec(
                        name="saturation_scale",
                        type=float,
                        default=1.0,
                        min_value=0.0,
                        max_value=2.0,
                        description="Saturation multiplier",
                    ),
                    ParameterSpec(
                        name="value_scale",
                        type=float,
                        default=1.0,
                        min_value=0.0,
                        max_value=2.0,
                        description="Brightness multiplier",
                    ),
                ],
                supports_audio=True,
            ),
            ModifiableAttribute(
                name="motion",
                description="Rainbow motion properties",
                parameter_specs=[
                    ParameterSpec(
                        name="speed_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Speed multiplier",
                    ),
                    ParameterSpec(
                        name="wave_amplitude",
                        type=float,
                        default=0.0,
                        min_value=0.0,
                        max_value=1.0,
                        description="Wave motion amplitude",
                    ),
                ],
                supports_audio=True,
            ),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate rainbow pattern with enhanced control"""
        # Get parameters with validation
        speed = np.clip(params.get("speed", 1.0), 0.1, 5.0)
        scale = np.clip(params.get("scale", 1.0), 0.1, 5.0)
        saturation = np.clip(params.get("saturation", 1.0), 0.0, 1.0)
        value = np.clip(params.get("value", 1.0), 0.0, 1.0)
        offset = np.clip(params.get("offset", 0.0), 0.0, 1.0)
        reverse = params.get("reverse", False)
        wave_amplitude = np.clip(params.get("wave_amplitude", 0.0), 0.0, 1.0)

        # Cache current values for transitions
        self.state.cache_value("last_speed", speed)
        self.state.cache_value("last_scale", scale)
        self.state.cache_value("last_saturation", saturation)
        self.state.cache_value("last_value", value)
        self.state.cache_value("last_offset", offset)
        self.state.cache_value("last_wave_amplitude", wave_amplitude)

        # Use timing system for smooth movement
        t = self.timing.get_phase() * (-1 if reverse else 1)

        # Generate rainbow colors
        for i in range(self.led_count):
            # Calculate hue position with wave motion
            base_pos = i / self.led_count
            wave_offset = np.sin(base_pos * 2 * np.pi) * wave_amplitude
            hue = ((base_pos + wave_offset) * scale + t + offset) % 1.0

            # Convert HSV to RGB
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)

            # Scale to 0-255 range
            self.frame_buffer[i] = (np.array(rgb) * 255).astype(np.uint8)

        return self.frame_buffer

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
