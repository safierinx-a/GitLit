from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import numpy as np


@dataclass
class ModifierSpec:
    """Specification for a modifier parameter"""

    name: str
    type: type
    default: Any
    min_value: Optional[Any] = None
    max_value: Optional[Any] = None
    description: str = ""
    units: str = ""


class BaseModifier:
    """Base class for all pattern modifiers"""

    def __init__(self):
        self.enabled = True

    @classmethod
    @property
    def parameters(cls) -> List[ModifierSpec]:
        """Get modifier parameters"""
        return []

    def validate_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and set defaults for parameters"""
        validated = {}
        for spec in self.parameters:
            value = params.get(spec.name, spec.default)

            # Type conversion
            try:
                value = spec.type(value)
            except (ValueError, TypeError):
                value = spec.default

            # Range validation
            if spec.min_value is not None:
                value = max(spec.min_value, value)
            if spec.max_value is not None:
                value = min(spec.max_value, value)

            validated[spec.name] = value

        return validated

    def apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Apply modifier to frame"""
        if not self.enabled:
            return frame

        params = self.validate_params(params)
        return self._apply(frame, params)

    def _apply(self, frame: np.ndarray, params: Dict[str, Any]) -> np.ndarray:
        """Implementation of modifier effect"""
        raise NotImplementedError
