from typing import Any, Dict

import numpy as np

from ..base import BaseModifier


class BeatModifier(BaseModifier):
    """Modify pattern based on audio beats"""

    def apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        beat_active = params.get("beat_active", False)
        intensity = params.get("beat_intensity", 1.0)

        if beat_active:
            return (frame * intensity).astype(np.uint8)
        return frame
