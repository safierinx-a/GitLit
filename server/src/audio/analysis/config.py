from dataclasses import dataclass
from typing import Dict, List, Optional

import numpy as np


@dataclass
class AudioFeatures:
    """Rich audio features from ML models"""

    # Rhythm Features (from TCN model)
    rhythm: Dict[str, float] = None  # Detailed rhythm information
    beats: List[float] = None  # Beat positions
    tempo: float = 0.0  # BPM
    groove: str = "unknown"  # Groove type

    # Spectral Features (from wav2vec)
    spectrum: Dict[str, float] = None  # Frequency bands
    timbre: Dict[str, float] = None  # Timbral characteristics

    # Musical Features (from classifier)
    genre: str = "unknown"  # Detected genre
    mood: str = "neutral"  # Detected mood
    energy: float = 0.0  # Energy level
    section: str = "unknown"  # Musical section

    # Events
    events: Dict[str, bool] = None  # Musical events (drop, build, etc)

    def __post_init__(self):
        if self.rhythm is None:
            self.rhythm = {
                "strength": 0.0,  # Beat strength
                "confidence": 0.0,  # Detection confidence
                "stability": 0.0,  # Rhythm stability
                "complexity": 0.0,  # Rhythmic complexity
            }

        if self.spectrum is None:
            self.spectrum = {
                "sub_bass": 0.0,
                "bass": 0.0,
                "low_mid": 0.0,
                "mid": 0.0,
                "high_mid": 0.0,
                "high": 0.0,
                "presence": 0.0,
            }

        if self.timbre is None:
            self.timbre = {
                "brightness": 0.0,
                "warmth": 0.0,
                "roughness": 0.0,
                "attack": 0.0,
            }

        if self.events is None:
            self.events = {
                "beat": False,
                "drop": False,
                "build_up": False,
                "breakdown": False,
                "section_change": False,
            }

        if self.beats is None:
            self.beats = []


@dataclass
class AnalysisConfig:
    """Configuration for audio analysis"""

    # Audio parameters
    sample_rate: int = 44100
    buffer_size: int = 2048
    hop_length: int = 512

    # Model parameters
    beat_model: str = "tcn"  # Temporal Conv Net
    feature_model: str = "w2v2"  # wav2vec 2.0
    music_model: str = "music_understanding"

    # Analysis parameters
    tempo_range: tuple = (50, 200)  # BPM range
    frequency_range: tuple = (20, 20000)  # Hz range

    # Processing parameters
    use_gpu: bool = False
    batch_size: int = 1
    feature_size: int = 768  # wav2vec feature dimension

    # Buffer management
    history_size: int = 4  # Seconds of history to keep

    def get_buffer_samples(self) -> int:
        """Get number of samples for history buffer"""
        return int(self.history_size * self.sample_rate)
