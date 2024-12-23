import numpy as np
from scipy import signal, stats
from dataclasses import dataclass
from typing import Dict, List, Optional
import time


@dataclass
class EnhancedAudioFeatures:
    """Complete real-time audio feature set"""

    # Rhythm
    bpm: float = 0.0
    beat_positions: List[float] = None
    beat_strength: float = 0.0
    groove_type: str = "unknown"
    rhythm_stability: float = 0.0
    sub_beats: List[float] = None

    # Spectral
    bands: Dict[str, float] = None
    harmonic_content: float = 0.0
    spectral_flux: float = 0.0
    brightness: float = 0.0
    warmth: float = 0.0

    # Musical
    energy_level: float = 0.0
    is_build_up: bool = False
    is_drop: bool = False
    section_change: bool = False
    intensity: float = 0.0
    mood: str = "neutral"

    def __post_init__(self):
        if self.beat_positions is None:
            self.beat_positions = []
        if self.sub_beats is None:
            self.sub_beats = []
        if self.bands is None:
            self.bands = {
                "sub_bass": 0.0,
                "bass": 0.0,
                "low_mid": 0.0,
                "mid": 0.0,
                "high_mid": 0.0,
                "high": 0.0,
                "presence": 0.0,
            }


class EnhancedAudioProcessor:
    """Advanced audio analysis using numpy/scipy (no essentia dependency)"""

    def __init__(self, sample_rate: int, buffer_size: int):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        # Initialize FFT components
        self.window = signal.hann(buffer_size)
        self.freq_bins = np.fft.rfftfreq(buffer_size, 1 / sample_rate)

        # Prepare frequency band indices
        self.band_ranges = {
            "sub_bass": (20, 60),
            "bass": (60, 250),
            "low_mid": (250, 500),
            "mid": (500, 2000),
            "high_mid": (2000, 4000),
            "high": (4000, 8000),
            "presence": (8000, 20000),
        }
        self.band_indices = self._calculate_band_indices()

        # Analysis state
        self.features = EnhancedAudioFeatures()
        self.history_length = int(2 * sample_rate)  # 2 seconds
        self.audio_history = np.zeros(self.history_length)
        self.spectrum_history = []
        self.energy_history = []

        print(f"Initialized FFT-based analyzer at {sample_rate}Hz")

    def _calculate_band_indices(self) -> Dict[str, tuple]:
        """Calculate FFT bin indices for each frequency band"""
        indices = {}
        for band, (low, high) in self.band_ranges.items():
            low_idx = np.searchsorted(self.freq_bins, low)
            high_idx = np.searchsorted(self.freq_bins, high)
            indices[band] = (low_idx, high_idx)
            print(f"Band {band}: {low}-{high}Hz (bins {low_idx}-{high_idx})")
        return indices

    def process_buffer(self, buffer: np.ndarray) -> EnhancedAudioFeatures:
        """Process a buffer of audio data"""
        # Update audio history
        self.audio_history = np.roll(self.audio_history, -len(buffer))
        self.audio_history[-len(buffer) :] = buffer

        # Compute spectrum
        windowed = self.window(buffer)
        spectrum = np.fft.rfft(windowed)

        # Update frequency bands
        band_names = list(self.features.bands.keys())
        for i, band in enumerate(band_names):
            self.features.bands[band] = float(
                spectrum[self.band_indices[band][0] : self.band_indices[band][1]].mean()
            )

        # Rhythm analysis on larger buffer
        if len(self.audio_history) >= self.history_length:
            bpm, beats, confidence, _ = self.rhythm_extractor(self.audio_history)
            self.features.bpm = float(bpm)
            self.features.beat_strength = float(confidence)

            # Update beat positions
            current_time = time.time()
            self.features.beat_positions = [current_time + b for b in beats if b >= 0]

        # Harmonic-Percussive Separation
        harmonic, percussive = self.hpss(spectrum)
        self.features.harmonic_content = np.mean(harmonic) / (
            np.mean(percussive) + 1e-10
        )

        # Spectral features
        self.features.brightness = np.sum(spectrum * np.arange(len(spectrum))) / (
            np.sum(spectrum) + 1e-10
        )
        self.features.warmth = np.mean(
            spectrum[self.band_indices["bass"][0] : self.band_indices["bass"][1]].mean()
        ) / (
            np.mean(
                spectrum[
                    self.band_indices["high"][0] : self.band_indices["high"][1]
                ].mean()
            )
            + 1e-10
        )

        # Update spectral history
        self.spectrum_history.append(spectrum)
        if len(self.spectrum_history) > 10:
            self.spectrum_history.pop(0)
            self.features.spectral_flux = np.mean(
                np.diff(self.spectrum_history, axis=0)
            )

        # Energy and musical features
        self._analyze_musical_features(buffer, spectrum)

        return self.features

    def _analyze_musical_features(self, buffer: np.ndarray, spectrum: np.ndarray):
        """Analyze higher-level musical features"""
        # Calculate energy level
        current_energy = np.mean(buffer**2)
        self.energy_history.append(current_energy)
        if len(self.energy_history) > 100:  # About 2 seconds
            self.energy_history.pop(0)

        # Smooth energy
        self.features.energy_level = np.mean(self.energy_history)

        # Detect build-up
        if len(self.energy_history) > 50:
            energy_trend = np.polyfit(
                np.arange(len(self.energy_history)), self.energy_history, 1
            )[0]
            self.features.is_build_up = energy_trend > 0.1

        # Detect drops
        if len(self.energy_history) > 10:
            recent_energy = np.mean(self.energy_history[-10:])
            past_energy = np.mean(self.energy_history[:-10])
            self.features.is_drop = (
                recent_energy > past_energy * 1.5
                and self.features.bands["bass"]
                > np.mean(list(self.features.bands.values())[1:])
            )

        # Calculate intensity
        self.features.intensity = (
            0.4 * self.features.energy_level
            + 0.3 * self.features.bands["bass"]
            + 0.2 * self.features.spectral_flux
            + 0.1 * self.features.beat_strength
        )

        # Estimate mood
        if self.features.intensity > 0.7:
            self.features.mood = "energetic"
        elif self.features.intensity > 0.4:
            self.features.mood = "balanced"
        else:
            self.features.mood = "calm"
