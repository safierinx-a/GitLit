from .engine import BaseModifier
import numpy as np
from typing import Dict, Any


class BrightnessModifier(BaseModifier):
    """Modify brightness of frame"""

    def apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        brightness = params.get("level", 1.0)  # 0.0 to 1.0
        return (frame * brightness).astype(np.uint8)


class MirrorModifier(BaseModifier):
    """Mirror the frame"""

    def apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        if params.get("enabled", True):
            mid = len(frame) // 2
            frame[mid:] = np.flip(frame[:mid], axis=0)
        return frame
