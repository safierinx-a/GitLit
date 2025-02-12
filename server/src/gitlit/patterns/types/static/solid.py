from typing import Any, Dict, List

import numpy as np
import logging

from ...base import BasePattern, ColorSpec, ModifiableAttribute, ParameterSpec

logger = logging.getLogger(__name__)


class SolidPattern(BasePattern):
    """Single solid color across all LEDs"""

    @classmethod
    @property
    def parameters(cls) -> List[ParameterSpec]:
        return [
            ColorSpec(
                name="red", description="Red component of solid color", default=255
            ),
            ColorSpec(
                name="green", description="Green component of solid color", default=255
            ),
            ColorSpec(
                name="blue", description="Blue component of solid color", default=255
            ),
        ]

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        return [
            ModifiableAttribute(
                name="color",
                description="Solid color properties",
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
                    ParameterSpec(
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

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate a solid color frame"""
        # Get color parameters from state with defaults
        r = self.state.parameters.get("red", 255)
        g = self.state.parameters.get("green", 255)
        b = self.state.parameters.get("blue", 255)

        logger.debug(f"Generating solid pattern with color: R={r}, G={g}, B={b}")

        # Create frame buffer with solid color
        frame = np.tile([r, g, b], (self.led_count, 1)).astype(np.uint8)

        # Cache the current color for modifiers
        self.state.cache_value("last_color", [r, g, b])

        return frame
