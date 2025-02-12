from typing import Any, Dict, List

import numpy as np

from ...base import BasePattern, ColorSpec, ModifiableAttribute, Parameter


class GradientPattern(BasePattern):
    """Two-color gradient pattern"""

    name = "gradient"
    description = "Smooth transition between two colors"

    parameters = [
        ColorSpec(name="color1_r", description="First color red component"),
        ColorSpec(name="color1_g", description="First color green component"),
        ColorSpec(name="color1_b", description="First color blue component"),
        ColorSpec(name="color2_r", description="Second color red component"),
        ColorSpec(name="color2_g", description="Second color green component"),
        ColorSpec(name="color2_b", description="Second color blue component"),
        Parameter(
            name="position",
            type=float,
            default=0.5,
            min_value=0.0,
            max_value=1.0,
            description="Center position of the gradient",
        ),
        Parameter(
            name="width",
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=2.0,
            description="Width of the gradient transition",
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
                    Parameter(
                        name="hue_shift",
                        type=float,
                        default=0.0,
                        min_value=0.0,
                        max_value=1.0,
                        description="Shift the color hue",
                    ),
                    Parameter(
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
                    Parameter(
                        name="offset",
                        type=float,
                        default=0.0,
                        min_value=-1.0,
                        max_value=1.0,
                        description="Position offset",
                    ),
                    Parameter(
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

    async def _generate(self, time_ms: float) -> np.ndarray:
        """Generate gradient pattern frame"""
        # Get color components from state
        color1 = np.array(
            [
                self.state.parameters.get("color1_r", 0),
                self.state.parameters.get("color1_g", 0),
                self.state.parameters.get("color1_b", 0),
            ],
            dtype=np.float32,
        )

        color2 = np.array(
            [
                self.state.parameters.get("color2_r", 0),
                self.state.parameters.get("color2_g", 0),
                self.state.parameters.get("color2_b", 0),
            ],
            dtype=np.float32,
        )

        # Get gradient parameters
        position = self.state.parameters.get("position", 0.5)
        width = self.state.parameters.get("width", 1.0)

        # Calculate gradient
        positions = np.linspace(0, 1, self.num_leds)
        distances = np.abs(positions - position)
        mix = np.clip(distances / width, 0, 1)

        # Mix colors based on position
        self.frame_buffer = (
            color1[None, :] * (1 - mix[:, None]) + color2[None, :] * mix[:, None]
        ).astype(np.uint8)

        return self.frame_buffer
