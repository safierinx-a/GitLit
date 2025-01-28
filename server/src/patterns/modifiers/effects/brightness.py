from ..base import BaseModifier, ModifierSpec
import numpy as np
from typing import Dict, Any, List


class BrightnessModifier(BaseModifier):
    """Modify pattern brightness"""

    @classmethod
    @property
    def parameters(cls) -> List[ModifierSpec]:
        return [
            ModifierSpec(
                name="brightness",
                type=float,
                default=1.0,
                min_value=0.0,
                max_value=1.0,
                description="Brightness multiplier",
                units="%",
            )
        ]

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        brightness = params["brightness"]
        return (frame * brightness).astype(np.uint8)
