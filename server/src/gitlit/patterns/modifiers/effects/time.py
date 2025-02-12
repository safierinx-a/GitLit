import math
import time
from typing import Any, Dict

import numpy as np

from ..base import BaseModifier, ModifierSpec


class StrobeModifier(BaseModifier):
    """Add strobe effect"""

    @classmethod
    @property
    def parameters(cls):
        return [
            ModifierSpec(
                name="rate",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=10.0,
                description="Strobe rate in Hz",
            ),
            ModifierSpec(
                name="duty_cycle",
                type=float,
                default=0.5,
                min_value=0.1,
                max_value=0.9,
                description="On-time ratio",
            ),
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        rate = params["rate"]
        duty_cycle = params["duty_cycle"]

        # Calculate strobe state based on time
        t = (time.time() * rate) % 1.0
        if t > duty_cycle:
            return np.zeros_like(frame)
        return frame


class FadeModifier(BaseModifier):
    """Add fade in/out effect"""

    @classmethod
    @property
    def parameters(cls):
        return [
            ModifierSpec(
                name="period",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=10.0,
                description="Fade period in seconds",
            ),
            ModifierSpec(
                name="min_brightness",
                type=float,
                default=0.0,
                min_value=0.0,
                max_value=1.0,
                description="Minimum brightness",
            ),
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        period = params["period"]
        min_bright = params["min_brightness"]

        # Calculate fade multiplier
        t = (time.time() / period) % 1.0
        fade = (math.sin(t * 2 * math.pi) + 1) / 2
        fade = min_bright + (1.0 - min_bright) * fade

        return (frame * fade).astype(np.uint8)
