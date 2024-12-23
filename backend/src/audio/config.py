from dataclasses import dataclass
from typing import Optional


@dataclass
class AudioConfig:
    """Audio processing configuration"""

    sample_rate: int = 44100
    buffer_size: int = 1024
    channels: int = 1
    target: str = "pipewire:capture_1"  # Default input

    # Processing parameters
    volume_smoothing: float = 0.1  # Smoothing factor for volume
    beat_threshold: float = 1.5  # Beat detection threshold
    frequency_bands: int = 8  # Number of frequency bands to analyze
