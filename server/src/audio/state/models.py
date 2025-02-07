from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StructureInfo:
    """Musical structure information"""

    boundaries: List[float] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class HarmonyInfo:
    """Harmonic analysis information"""

    key: Optional[str] = None
    mode: Optional[str] = None
    chords: List[str] = field(default_factory=list)
    chord_timestamps: List[float] = field(default_factory=list)


@dataclass
class SeparationInfo:
    """Harmonic/percussive separation information"""

    harmonic_energy: List[float] = field(default_factory=list)
    percussive_energy: List[float] = field(default_factory=list)
    balance: float = 0.5  # 0 = percussive, 1 = harmonic


@dataclass
class BeatInfo:
    """Beat detection information"""

    confidence: float
    tempo: float
    last_beat_time: float
    beat_positions: List[float] = field(default_factory=list)


@dataclass
class SpectralInfo:
    """Spectral analysis information"""

    centroid: float
    bandwidth: float
    rolloff: float
    flatness: float
    contrast: List[float] = field(default_factory=list)
    complexity: float = 0.0
    hfc: float = 0.0
    melbands: List[float] = field(default_factory=list)
    melbands_diff: List[float] = field(default_factory=list)
    frequency_bands: Dict[str, float] = field(
        default_factory=lambda: {
            "sub": 0.0,  # 20-60 Hz
            "bass": 0.0,  # 60-250 Hz
            "low_mid": 0.0,  # 250-500 Hz
            "mid": 0.0,  # 500-2000 Hz
            "high_mid": 0.0,  # 2000-4000 Hz
            "high": 0.0,  # 4000-8000 Hz
            "presence": 0.0,  # 8000-20000 Hz
        }
    )
    peak_frequencies: List[float] = field(
        default_factory=list
    )  # Top dominant frequencies


@dataclass
class EnergyInfo:
    """Energy and loudness information"""

    rms: float
    peak: float
    loudness: float
    dynamic_complexity: float = 0.0
    dynamic_mean: float = 0.0
    onset_strength: float = 0.0
    beats_magnitude: List[float] = field(default_factory=list)


@dataclass
class RhythmInfo:
    """Rhythm analysis information"""

    bpm: float = 0.0
    beat_intervals: List[float] = field(default_factory=list)
    onset_positions: List[float] = field(default_factory=list)
    onset_strengths: List[float] = field(default_factory=list)


@dataclass
class AudioState:
    """Complete audio analysis state"""

    timestamp: datetime = field(default_factory=datetime.now)
    beat: Optional[BeatInfo] = None
    spectral: Optional[SpectralInfo] = None
    energy: Optional[EnergyInfo] = None
    rhythm: Optional[RhythmInfo] = None
    structure: Optional[StructureInfo] = None
    harmony: Optional[HarmonyInfo] = None
    separation: Optional[SeparationInfo] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "beat": vars(self.beat) if self.beat else None,
            "spectral": vars(self.spectral) if self.spectral else None,
            "energy": vars(self.energy) if self.energy else None,
            "rhythm": vars(self.rhythm) if self.rhythm else None,
            "structure": vars(self.structure) if self.structure else None,
            "harmony": vars(self.harmony) if self.harmony else None,
            "separation": vars(self.separation) if self.separation else None,
        }
