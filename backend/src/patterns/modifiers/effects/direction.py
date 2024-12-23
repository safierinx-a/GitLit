from ..base import BaseModifier, ModifierSpec
import numpy as np
from typing import Dict, Any, List


class DirectionModifier(BaseModifier):
    """Reverse pattern direction"""

    @classmethod
    @property
    def parameters(cls) -> List[ModifierSpec]:
        return [
            ModifierSpec(
                name="reverse",
                type=bool,
                default=False,
                description="Reverse pattern direction",
            )
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        if params["reverse"]:
            return np.flip(frame, axis=0)
        return frame
