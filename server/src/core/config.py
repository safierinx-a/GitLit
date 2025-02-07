from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PatternConfig:
    """Configuration for a pattern including modifiers"""

    name: str
    parameters: Dict[str, Any]
    modifiers: Optional[List[Dict[str, Any]]] = None


@dataclass
class FeatureFlags:
    """System feature flags"""

    audio_enabled: bool = False  # Disable audio processing by default
    performance_monitoring: bool = True
    error_reporting: bool = True


@dataclass
class SystemConfig:
    """Main system configuration"""

    features: FeatureFlags = field(default_factory=FeatureFlags)
    led: Dict[str, Any] = field(
        default_factory=lambda: {
            "led_count": 300,
            "brightness": 1.0,
        }
    )
    performance: Dict[str, Any] = field(
        default_factory=lambda: {
            "target_fps": 60,
            "max_frame_time": 16.67,  # ms (1000/60)
            "buffer_size": 2,
        }
    )

    @classmethod
    def create_default(cls) -> "SystemConfig":
        """Create default configuration"""
        return cls()

    def update(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        if "features" in updates:
            self.features = FeatureFlags(**updates["features"])
        if "led" in updates:
            self.led.update(updates["led"])
        if "performance" in updates:
            self.performance.update(updates["performance"])
