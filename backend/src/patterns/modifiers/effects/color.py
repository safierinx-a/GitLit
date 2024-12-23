import numpy as np
import colorsys
from ..base import BaseModifier, ModifierSpec
from typing import Dict, Any


class ColorTempModifier(BaseModifier):
    """Adjust color temperature (warm/cool)"""

    @classmethod
    @property
    def parameters(cls):
        return [
            ModifierSpec(
                name="temperature",
                type=float,
                default=0.0,  # 0 = neutral, -1 = warm, +1 = cool
                min_value=-1.0,
                max_value=1.0,
                description="Color temperature adjustment",
            )
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        temp = params["temperature"]
        if temp == 0:
            return frame

        # Convert RGB to HSV
        hsv_frame = np.zeros_like(frame, dtype=float)
        for i in range(len(frame)):
            r, g, b = frame[i] / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)

            # Adjust hue based on temperature
            if temp > 0:  # Cooler
                h = h * 0.8 + 0.6  # Shift toward blue
            else:  # Warmer
                h = h * 0.8 + 0.05  # Shift toward orange

            # Convert back to RGB
            r, g, b = colorsys.hsv_to_rgb(h % 1.0, s, v)
            frame[i] = np.array([r, g, b]) * 255

        return frame.astype(np.uint8)


class SaturationModifier(BaseModifier):
    """Adjust color saturation"""

    @classmethod
    @property
    def parameters(cls):
        return [
            ModifierSpec(
                name="saturation",
                type=float,
                default=1.0,
                min_value=0.0,
                max_value=2.0,
                description="Color saturation multiplier",
            )
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        sat_mult = params["saturation"]
        if sat_mult == 1.0:
            return frame

        # Convert RGB to HSV
        hsv_frame = np.zeros_like(frame, dtype=float)
        for i in range(len(frame)):
            r, g, b = frame[i] / 255.0
            h, s, v = colorsys.rgb_to_hsv(r, g, b)

            # Adjust saturation
            s = min(1.0, s * sat_mult)

            # Convert back to RGB
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            frame[i] = np.array([r, g, b]) * 255

        return frame.astype(np.uint8)


class ColorCycleModifier(BaseModifier):
    """Alternate between two colors for patterns like chase"""

    @classmethod
    @property
    def parameters(cls):
        return [
            ModifierSpec(
                name="enabled",
                type=bool,
                default=False,
                description="Enable color alternating",
            ),
            ModifierSpec(
                name="color1",
                type=tuple,
                default=(255, 0, 0),  # Red
                description="First color (RGB)",
            ),
            ModifierSpec(
                name="color2",
                type=tuple,
                default=(0, 0, 255),  # Blue
                description="Second color (RGB)",
            ),
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        if not params["enabled"]:
            return frame

        color1 = np.array(params["color1"])
        color2 = np.array(params["color2"])

        result = np.zeros_like(frame)
        sequence_found = False
        current_color = color1

        # Find first lit pixel to determine sequence start
        for i in range(len(frame)):
            if np.any(frame[i] > 0):
                sequence_found = True
                break

        # Apply alternating colors to sequences
        in_sequence = False
        for i in range(len(frame)):
            if np.any(frame[i] > 0):
                if not in_sequence:  # Start of new sequence
                    in_sequence = True
                    if sequence_found:
                        current_color = (
                            color2 if np.array_equal(current_color, color1) else color1
                        )

                # Apply current color while preserving brightness
                brightness = frame[i].max() / 255.0
                result[i] = current_color * brightness
            else:
                in_sequence = False

        return result.astype(np.uint8)
