from dataclasses import dataclass
from typing import Dict, Any, Optional, List


@dataclass
class PatternConfig:
    """Configuration for a pattern including modifiers"""

    name: str
    parameters: Dict[str, Any]
    modifiers: Optional[List[Dict[str, Any]]] = None
