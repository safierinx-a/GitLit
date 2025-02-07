from enum import Enum
from typing import Any, Dict, List, Tuple

import numpy as np

from ..core.exceptions import ValidationError
from .base import BasePattern


class BlendMode(Enum):
    """Blend modes for pattern composition"""

    NORMAL = "normal"
    ADD = "add"
    MULTIPLY = "multiply"
    OVERLAY = "overlay"

    def apply(self, base: np.ndarray, layer: np.ndarray, opacity: float) -> np.ndarray:
        """Apply blend mode between base and layer"""
        if self == BlendMode.NORMAL:
            return layer * opacity + base * (1 - opacity)
        elif self == BlendMode.ADD:
            return np.minimum(base + layer * opacity, 255)
        elif self == BlendMode.MULTIPLY:
            return base * (layer * opacity / 255)
        elif self == BlendMode.OVERLAY:
            mask = base > 127
            result = np.zeros_like(base)
            result[mask] = 255 - (
                (255 - 2 * (base[mask] - 127)) * (255 - layer[mask]) / 255
            )
            result[~mask] = (2 * base[~mask] * layer[~mask]) / 255
            return result * opacity + base * (1 - opacity)


class CompositePattern(BasePattern):
    """Pattern that combines multiple patterns with blend modes"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.layers: List[Tuple[BasePattern, float, BlendMode]] = []

    def add_layer(
        self, pattern: BasePattern, opacity: float = 1.0, blend: str = "normal"
    ):
        """Add a pattern layer with blend mode"""
        try:
            blend_mode = BlendMode[blend.upper()]
        except KeyError:
            raise ValidationError(f"Invalid blend mode: {blend}")

        self.layers.append((pattern, opacity, blend_mode))

    def remove_layer(self, index: int):
        """Remove a pattern layer"""
        if 0 <= index < len(self.layers):
            self.layers.pop(index)

    def generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate composite frame from all layers"""
        if not self.layers:
            return self.frame_buffer

        # Generate base layer
        base_pattern, base_opacity, _ = self.layers[0]
        self.frame_buffer = base_pattern.generate(time_ms, params) * base_opacity

        # Apply additional layers
        for pattern, opacity, blend_mode in self.layers[1:]:
            layer = pattern.generate(time_ms, params)
            self.frame_buffer = blend_mode.apply(self.frame_buffer, layer, opacity)

        return self.frame_buffer.astype(np.uint8)
