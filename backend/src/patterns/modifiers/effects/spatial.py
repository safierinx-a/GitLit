import numpy as np
from ..base import BaseModifier, ModifierSpec
from typing import Dict, Any


class MirrorModifier(BaseModifier):
    """Mirror pattern around center point"""

    @classmethod
    @property
    def parameters(cls):
        return [
            ModifierSpec(
                name="enabled", type=bool, default=False, description="Enable mirroring"
            ),
            ModifierSpec(
                name="center",
                type=float,
                default=0.5,
                min_value=0.0,
                max_value=1.0,
                description="Mirror center point",
            ),
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        if not params["enabled"]:
            return frame

        center = int(len(frame) * params["center"])
        if center == 0 or center == len(frame):
            return frame

        result = frame.copy()  # Work on a copy to avoid modifying original

        if center < len(frame) // 2:
            # Mirror left side to right
            left_side = result[:center]
            mirror_size = min(len(left_side), len(frame) - center)
            if mirror_size > 0:
                result[center : center + mirror_size] = np.flip(
                    left_side[-mirror_size:], axis=0
                )
        else:
            # Mirror right side to left
            right_side = result[center:]
            mirror_size = min(len(right_side), center)
            if mirror_size > 0:
                result[center - mirror_size : center] = np.flip(
                    right_side[:mirror_size], axis=0
                )

        return result


class SegmentModifier(BaseModifier):
    """Show pattern only in specific segments"""

    @classmethod
    @property
    def parameters(cls):
        return [
            ModifierSpec(
                name="start",
                type=float,
                default=0.0,
                min_value=0.0,
                max_value=1.0,
                description="Segment start position",
            ),
            ModifierSpec(
                name="length",
                type=float,
                default=1.0,
                min_value=0.0,
                max_value=1.0,
                description="Segment length",
            ),
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        start = int(len(frame) * params["start"])
        length = int(len(frame) * params["length"])
        end = min(start + length, len(frame))

        # Create mask
        result = np.zeros_like(frame)
        if start < end:
            result[start:end] = frame[start:end]

        return result
