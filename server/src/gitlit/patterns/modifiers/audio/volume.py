from typing import Any, Dict

import numpy as np

from ..base import BaseModifier


class VolumeModifier(BaseModifier):
    """Modify pattern based on audio volume"""

    def apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        volume = params.get("volume", 1.0)
        return (frame * volume).astype(np.uint8)
