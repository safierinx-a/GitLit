from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AudioConfig:
    """Audio processing configuration"""

    enabled: bool = False
    sample_rate: int = 44100
    channels: int = 2
    chunk_size: int = 1024
    format: str = "float32"


@dataclass
class LEDConfig:
    """LED hardware configuration"""

    count: int = 300
    brightness: float = 1.0
    refresh_rate: int = 60


@dataclass
class PerformanceConfig:
    """Performance settings"""

    target_fps: int = 60
    max_frame_time: float = 16.67  # ms (1000/60)
    buffer_size: int = 2


@dataclass
class FeatureFlags:
    """System feature flags"""

    audio_enabled: bool = False
    performance_monitoring: bool = True
    error_reporting: bool = True


@dataclass
class SystemConfig:
    """Main system configuration"""

    features: FeatureFlags = field(default_factory=FeatureFlags)
    led: LEDConfig = field(default_factory=LEDConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)

    @classmethod
    def create_default(cls) -> "SystemConfig":
        """Create default configuration"""
        return cls()

    def update(self, updates: Dict[str, Any]) -> None:
        """Update configuration with new values"""
        if "features" in updates:
            self.features = FeatureFlags(**updates["features"])
        if "led" in updates:
            self.led = LEDConfig(**updates["led"])
        if "audio" in updates:
            self.audio = AudioConfig(**updates["audio"])
        if "performance" in updates:
            self.performance = PerformanceConfig(**updates["performance"])


@dataclass
class PatternConfig:
    """Configuration for a pattern including modifiers"""

    name: str
    parameters: Dict[str, Any]
    modifiers: Optional[List[Dict[str, Any]]] = None
