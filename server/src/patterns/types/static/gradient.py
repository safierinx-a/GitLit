from typing import Any, Dict, List

import numpy as np

from ...base import BasePattern, ColorSpec, ModifiableAttribute, ParameterSpec


class GradientPattern(BasePattern):
    """Linear gradient between two colors with enhanced control"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data.update(
            {
                "last_color1": [0, 0, 0],
                "last_color2": [0, 0, 0],
                "last_position": 0.5,
                "last_smoothness": 1.0,
            }
        )

    @classmethod
    @property
    def parameters(cls) -> List[ParameterSpec]:
        return [
            ColorSpec(
                name="color1_r", description="First color red component", default=255
            ),
            ColorSpec(
                name="color1_g", description="First color green component", default=0
            ),
            ColorSpec(
                name="color1_b", description="First color blue component", default=0
            ),
            ColorSpec(
                name="color2_r", description="Second color red component", default=0
            ),
            ColorSpec(
                name="color2_g", description="Second color green component", default=0
            ),
            ColorSpec(
                name="color2_b", description="Second color blue component", default=255
            ),
            ParameterSpec(
                name="position",
                type=float,
                default=0.5,
                min_value=0.0,
                max_value=1.0,
                description="Gradient center position",
            ),
            ParameterSpec(
                name="smoothness",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=5.0,
                description="Gradient transition smoothness",
            ),
        ]

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        return [
            ModifiableAttribute(
                name="color",
                description="Gradient color properties",
                parameter_specs=[
                    ParameterSpec(
                        name="hue_shift",
                        type=float,
                        default=0.0,
                        min_value=0.0,
                        max_value=1.0,
                        description="Shift the color hue",
                    ),
                    ParameterSpec(
                        name="saturation",
                        type=float,
                        default=1.0,
                        min_value=0.0,
                        max_value=1.0,
                        description="Color saturation",
                    ),
                ],
                supports_audio=True,
            ),
            ModifiableAttribute(
                name="position",
                description="Gradient position properties",
                parameter_specs=[
                    ParameterSpec(
                        name="offset",
                        type=float,
                        default=0.0,
                        min_value=-1.0,
                        max_value=1.0,
                        description="Position offset",
                    ),
                    ParameterSpec(
                        name="oscillation",
                        type=float,
                        default=0.0,
                        min_value=0.0,
                        max_value=1.0,
                        description="Position oscillation amount",
                    ),
                ],
                supports_audio=True,
            ),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate gradient pattern with enhanced control"""
        # Get colors with validation
        color1 = np.array(
            [
                params.get("color1_r", 255),
                params.get("color1_g", 0),
                params.get("color1_b", 0),
            ],
            dtype=np.float32,
        )

        color2 = np.array(
            [
                params.get("color2_r", 0),
                params.get("color2_g", 0),
                params.get("color2_b", 255),
            ],
            dtype=np.float32,
        )

        # Get position and smoothness
        position = np.clip(params.get("position", 0.5), 0.0, 1.0)
        smoothness = np.clip(params.get("smoothness", 1.0), 0.1, 5.0)

        # Cache current values for transitions
        self.state.cache_value("last_color1", color1)
        self.state.cache_value("last_color2", color2)
        self.state.cache_value("last_position", position)
        self.state.cache_value("last_smoothness", smoothness)

        # Generate gradient
        positions = np.linspace(0, 1, self.led_count)
        t = 1.0 / (1.0 + np.exp(-(positions - position) * smoothness * 10))

        # Interpolate colors
        gradient = color1[None, :] * (1 - t[:, None]) + color2[None, :] * t[:, None]

        # Ensure output is uint8
        return np.clip(gradient, 0, 255).astype(np.uint8)
