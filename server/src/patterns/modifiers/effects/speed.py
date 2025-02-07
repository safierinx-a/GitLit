from typing import Any, Dict, List

import numpy as np

from ..base import BaseModifier, ModifierSpec


class SpeedModifier(BaseModifier):
    """Modify pattern speed"""

    @classmethod
    @property
    def parameters(cls) -> List[ModifierSpec]:
        return [
            ModifierSpec(
                name="speed",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=10.0,
                description="Speed multiplier",
                units="x",
            )
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        # Speed is handled by pattern timing system
        # This modifier just validates the speed parameter
        return frame
