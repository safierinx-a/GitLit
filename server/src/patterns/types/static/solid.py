from ...base import BasePattern, ColorSpec, ModifiableAttribute, ParameterSpec
import numpy as np
from typing import Dict, Any, List


class SolidPattern(BasePattern):
    """Single solid color across all LEDs"""

    @classmethod
    @property
    def parameters(cls) -> List[ParameterSpec]:
        return [
            ColorSpec(name="red", description="Red component of solid color"),
            ColorSpec(name="green", description="Green component of solid color"),
            ColorSpec(name="blue", description="Blue component of solid color"),
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

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        r = self.state.parameters.get("red", 0)
        g = self.state.parameters.get("green", 0)
        b = self.state.parameters.get("blue", 0)
        self.state.cache_value("last_color", [r, g, b])
        self.frame_buffer[:] = np.array([r, g, b], dtype=np.uint8)
        return self.frame_buffer
