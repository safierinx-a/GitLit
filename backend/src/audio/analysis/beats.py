import numpy as np
from typing import List, Tuple, Dict
from collections import deque


class BeatDetector:
    """Beat detection and tempo analysis"""

    def __init__(self, sample_rate: int):
        self.sample_rate = sample_rate

        # Beat detection parameters
        self.min_bpm = 60
        self.max_bpm = 180
        self.beat_threshold = 1.5  # Energy multiplier for beat detection

        # History
        self.energy_history = deque(maxlen=100)
        self.beat_history = deque(maxlen=100)
        self.tempo_history = deque(maxlen=10)

        # State
        self.last_beat_time = 0
        self.current_bpm = 0
        self.beat_confidence = 0

    def detect(
        self, buffer: np.ndarray, band_energies: Dict[str, float], current_time: float
    ) -> Tuple[bool, float, float]:
        """Detect beats and estimate tempo"""
        # Calculate low frequency energy (focus on bass and low-mids)
        current_energy = band_energies["bass"] * 0.7 + band_energies["low_mid"] * 0.3

        # Update energy history
        self.energy_history.append(current_energy)

        # Calculate local energy average
        local_avg = np.mean(list(self.energy_history)[-8:])

        # Beat detection
        beat_detected = False
        if len(self.energy_history) >= 8:
            # Check if current energy is significantly above local average
            if (
                current_energy > local_avg * self.beat_threshold
                and current_time - self.last_beat_time > 0.2
            ):  # Minimum 200ms between beats
                beat_detected = True
                self.last_beat_time = current_time

                # Update beat history
                self.beat_history.append(current_time)

                # Calculate tempo
                if len(self.beat_history) >= 2:
                    intervals = np.diff(list(self.beat_history)[-8:])
                    if len(intervals) > 0:
                        avg_interval = np.mean(intervals)
                        if avg_interval > 0:
                            bpm = 60.0 / avg_interval
                            # Only accept reasonable tempos
                            if self.min_bpm <= bpm <= self.max_bpm:
                                self.tempo_history.append(bpm)
                                self.current_bpm = np.median(self.tempo_history)

        # Calculate beat confidence based on regularity
        if len(self.beat_history) >= 4:
            intervals = np.diff(list(self.beat_history)[-4:])
            variance = np.var(intervals) if len(intervals) > 0 else float("inf")
            self.beat_confidence = 1.0 / (1.0 + variance)

        return beat_detected, self.current_bpm, self.beat_confidence
