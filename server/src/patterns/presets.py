import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Type

from .base import BasePattern
from .config import PatternConfig


@dataclass
class PatternPreset:
    """Reusable pattern configuration"""

    name: str
    pattern_type: str
    parameters: Dict[str, Any]
    modifiers: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class PresetManager:
    """Manages pattern presets"""

    def __init__(self, preset_dir: str = "presets"):
        self.preset_dir = preset_dir
        self.presets: Dict[str, PatternPreset] = {}
        self._load_presets()

    def _load_presets(self):
        """Load presets from files"""
        if not os.path.exists(self.preset_dir):
            os.makedirs(self.preset_dir)
            return

        for filename in os.listdir(self.preset_dir):
            if filename.endswith(".json"):
                with open(os.path.join(self.preset_dir, filename), "r") as f:
                    data = json.load(f)
                    preset = PatternPreset(
                        name=data["name"],
                        pattern_type=data["pattern_type"],
                        parameters=data["parameters"],
                        modifiers=data.get("modifiers"),
                        metadata=data.get("metadata", {}),
                    )
                    self.presets[preset.name] = preset

    def save_preset(
        self,
        name: str,
        pattern: BasePattern,
        config: PatternConfig,
        metadata: Dict[str, Any] = None,
    ):
        """Save current pattern configuration as preset"""
        preset = PatternPreset(
            name=name,
            pattern_type=pattern.__class__.__name__,
            parameters=config.parameters.copy(),
            modifiers=config.modifiers.copy() if config.modifiers else None,
            metadata=metadata or {},
        )

        # Save to file
        filename = f"{name.lower().replace(' ', '_')}.json"
        with open(os.path.join(self.preset_dir, filename), "w") as f:
            json.dump(asdict(preset), f, indent=2)

        self.presets[name] = preset

    def load_preset(self, name: str) -> PatternConfig:
        """Load preset configuration"""
        if name not in self.presets:
            raise KeyError(f"Preset {name} not found")

        preset = self.presets[name]
        return PatternConfig(
            name=preset.pattern_type,
            parameters=preset.parameters.copy(),
            modifiers=preset.modifiers.copy() if preset.modifiers else None,
        )

    def list_presets(self) -> List[str]:
        """List available presets"""
        return list(self.presets.keys())
