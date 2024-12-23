from dataclasses import dataclass
from typing import Dict, Optional, List
from ..patterns.base import BasePattern
from ..patterns.modifiers import BaseModifier


@dataclass
class AudioBinding:
    """Audio parameter to modifier binding"""

    modifier: BaseModifier
    parameter: str
    audio_metric: str  # volume, beat, frequency
    scale: float = 1.0
    offset: float = 0.0


@dataclass
class UIState:
    """State of the control UI"""

    active_pattern: Optional[BasePattern] = None
    pattern_params: Dict[str, any] = None
    active_modifiers: List[BaseModifier] = None
    audio_bindings: List[AudioBinding] = None
    audio_enabled: bool = False
