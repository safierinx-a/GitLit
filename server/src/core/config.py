from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .exceptions import ValidationError


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
        config = cls()

        # Validate LED configuration
        if config.led.count <= 0:
            raise ValidationError("LED count must be greater than 0")
        if not 0 <= config.led.brightness <= 1:
            raise ValidationError("LED brightness must be between 0 and 1")
        if config.led.refresh_rate <= 0:
            raise ValidationError("LED refresh rate must be greater than 0")

        # Validate performance configuration
        if config.performance.target_fps <= 0:
            raise ValidationError("Target FPS must be greater than 0")
        if config.performance.max_frame_time <= 0:
            raise ValidationError("Max frame time must be greater than 0")
        if config.performance.buffer_size <= 0:
            raise ValidationError("Buffer size must be greater than 0")

        # Validate audio configuration if enabled
        if config.features.audio_enabled:
            if config.audio.sample_rate <= 0:
                raise ValidationError("Audio sample rate must be greater than 0")
            if config.audio.channels <= 0:
                raise ValidationError("Audio channels must be greater than 0")
            if config.audio.chunk_size <= 0:
                raise ValidationError("Audio chunk size must be greater than 0")
            if config.audio.format not in ["float32", "int16"]:
                raise ValidationError("Audio format must be either float32 or int16")

        return config

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

        # Validate the updated configuration
        # Validate LED configuration
        if self.led.count <= 0:
            raise ValidationError("LED count must be greater than 0")
        if not 0 <= self.led.brightness <= 1:
            raise ValidationError("LED brightness must be between 0 and 1")
        if self.led.refresh_rate <= 0:
            raise ValidationError("LED refresh rate must be greater than 0")

        # Validate performance configuration
        if self.performance.target_fps <= 0:
            raise ValidationError("Target FPS must be greater than 0")
        if self.performance.max_frame_time <= 0:
            raise ValidationError("Max frame time must be greater than 0")
        if self.performance.buffer_size <= 0:
            raise ValidationError("Buffer size must be greater than 0")

        # Validate audio configuration if enabled
        if self.features.audio_enabled:
            if self.audio.sample_rate <= 0:
                raise ValidationError("Audio sample rate must be greater than 0")
            if self.audio.channels <= 0:
                raise ValidationError("Audio channels must be greater than 0")
            if self.audio.chunk_size <= 0:
                raise ValidationError("Audio chunk size must be greater than 0")
            if self.audio.format not in ["float32", "int16"]:
                raise ValidationError("Audio format must be either float32 or int16")
