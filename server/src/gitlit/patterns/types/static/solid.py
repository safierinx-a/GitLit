from typing import Any, Dict, List

import numpy as np
import logging

from ...base import BasePattern, ColorSpec, ModifiableAttribute, Parameter

logger = logging.getLogger(__name__)


class SolidPattern(BasePattern):
    """Single solid color pattern"""

    name = "solid"
    description = "Single solid color pattern"

    parameters = [
        ColorSpec(name="red", description="Red component"),
        ColorSpec(name="green", description="Green component"),
        ColorSpec(name="blue", description="Blue component"),
    ]

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        return [
            ModifiableAttribute(
                name="color",
                description="Solid color properties",
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
                    Parameter(
                        name="brightness",
                        type=float,
                        default=1.0,
                        min_value=0.0,
                        max_value=1.0,
                        description="Color brightness",
                    ),
                ],
                supports_audio=True,
            )
        ]

    def before_generate(self, time_ms: float, params: Dict[str, Any]) -> None:
        """Store parameters in state before generation"""
        super().before_generate(time_ms, params)

        # Get current parameters with defaults
        current_params = self.state.parameters

        # Update color parameters with validation
        self.state.parameters.update(
            {
                "red": np.clip(
                    int(params.get("red", current_params.get("red", 255))), 0, 255
                ),
                "green": np.clip(
                    int(params.get("green", current_params.get("green", 255))), 0, 255
                ),
                "blue": np.clip(
                    int(params.get("blue", current_params.get("blue", 255))), 0, 255
                ),
            }
        )

        logger.debug(f"Updated state parameters: {self.state.parameters}")

    async def _generate(self, time_ms: float) -> np.ndarray:
        """Generate solid color frame"""
        # Get color components from state
        red = self.state.parameters.get("red", 0)
        green = self.state.parameters.get("green", 0)
        blue = self.state.parameters.get("blue", 0)

        # Fill frame buffer with solid color
        self.frame_buffer.fill(0)
        self.frame_buffer[:] = [red, green, blue]

        return self.frame_buffer
