import numpy as np
import time
from typing import Dict, Optional
from .metrics import AudioMetrics
from .spectral import SpectralAnalyzer
from .beats import AdvancedBeatDetector, BeatInfo


class AudioAnalyzer:
    """Core audio analysis engine"""

    def __init__(self, sample_rate: int, buffer_size: int):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        # Initialize analyzers
        self.spectral = SpectralAnalyzer(sample_rate, buffer_size)
        self.beat_detector = AdvancedBeatDetector(sample_rate, buffer_size)

        # Analysis history
        self.volume_history = []
        self.peak_history = []
        self.beat_history = []
        self.metrics = AudioMetrics()

        # Analysis parameters
        self.volume_smooth_factor = 0.2
        self.peak_decay = 0.95
        self.current_peak = 0.0

        # Timing
        self.start_time = time.time()
        self.current_time = 0.0

    def process_buffer(self, buffer: np.ndarray) -> AudioMetrics:
        """Process a buffer of audio data and update metrics"""
        self.current_time = time.time() - self.start_time

        # Basic metrics
        volume = np.abs(buffer).mean()
        peak = np.abs(buffer).max()

        # Smooth volume
        if self.volume_history:
            volume = volume * self.volume_smooth_factor + self.volume_history[-1] * (
                1 - self.volume_smooth_factor
            )
        self.volume_history.append(volume)

        # Peak detection with decay
        self.current_peak *= self.peak_decay
        if peak > self.current_peak:
            self.current_peak = peak
        self.peak_history.append(self.current_peak)

        # Spectral analysis
        spectral_data = self.spectral.analyze(buffer)

        # Beat detection
        beats, tempo = self.beat_detector.process(buffer, self.current_time)

        # Update metrics
        self.metrics.volume = volume
        self.metrics.peak = self.current_peak
        self.metrics.frequency_bands = spectral_data["bands"]
        self.metrics.spectral_centroid = spectral_data["centroid"]

        # Update beat metrics
        if beats:
            latest_beat = beats[-1]
            self.metrics.beat_detected = True
            self.metrics.beat_confidence = latest_beat.confidence
            self.metrics.bpm = tempo
            self.beat_history.append(latest_beat)
        else:
            self.metrics.beat_detected = False

        # Calculate energy metrics
        self.metrics.energy_level = (
            0.4 * volume
            + 0.3 * spectral_data["bands"]["bass"]
            + 0.2 * spectral_data["bands"]["mid"]
            + 0.1 * peak
        )

        # Keep histories bounded
        if len(self.volume_history) > 100:
            self.volume_history.pop(0)
        if len(self.peak_history) > 100:
            self.peak_history.pop(0)
        if len(self.beat_history) > 50:
            self.beat_history.pop(0)

        return self.metrics

    def get_metrics(self) -> AudioMetrics:
        """Get current audio metrics"""
        return self.metrics
