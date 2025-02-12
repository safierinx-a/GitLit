from typing import Any, Dict, List

import numpy as np

from ..base import BaseModifier, ModifierSpec


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
