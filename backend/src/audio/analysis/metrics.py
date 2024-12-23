from dataclasses import dataclass
from typing import List, Dict
import numpy as np


@dataclass
class AudioMetrics:
    """Container for all audio analysis metrics"""

    # Immediate metrics (updated every buffer)
    volume: float = 0.0  # Current volume level (0-1)
    peak: float = 0.0  # Current peak level (0-1)

    # Spectral metrics
    frequency_bands: Dict[str, float] = None  # Energy in frequency bands
    spectral_centroid: float = 0.0  # Brightness measure

    # Beat metrics
    beat_detected: bool = False  # Beat occurred this frame
    beat_confidence: float = 0.0  # Confidence in beat detection
    bpm: float = 0.0  # Current BPM estimate

    # Energy metrics
    energy_level: float = 0.0  # Overall energy level
    is_build_up: bool = False  # Build-up detected
    is_drop: bool = False  # Drop detected

    def __post_init__(self):
        if self.frequency_bands is None:
            self.frequency_bands = {
                "sub": 0.0,  # 20-60 Hz
                "bass": 0.0,  # 60-250 Hz
                "low_mid": 0.0,  # 250-500 Hz
                "mid": 0.0,  # 500-2000 Hz
                "high_mid": 0.0,  # 2000-4000 Hz
                "high": 0.0,  # 4000-8000 Hz
                "presence": 0.0,  # 8000-20000 Hz
            }
