import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass
from scipy import signal
from enum import Enum
from scipy import stats


class OnsetDetectionFunction(Enum):
    ENERGY = "energy"
    COMPLEX = "complex"
    PHASE = "phase"
    SPECTRAL_FLUX = "spectral_flux"


@dataclass
class BeatInfo:
    """Detailed beat information"""

    position: float  # Time position of beat
    confidence: float  # Detection confidence
    strength: float  # Beat strength
    type: str  # Beat type (down/up/off)
    sub_division: int  # Beat subdivision (1/4, 1/8, etc)


class AdvancedBeatDetector:
    """State-of-the-art beat detection and tracking"""

    def __init__(self, sample_rate: int, buffer_size: int):
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size

        # Analysis windows
        self.window_size = 2048
        self.hop_size = self.window_size // 4

        # Beat tracking parameters
        self.min_bpm = 50
        self.max_bpm = 200
        self.tempo_buffer_size = 8  # Seconds of tempo history

        # Initialize buffers
        self.audio_buffer = np.zeros(self.window_size * 2)
        self.phase_buffer = np.zeros(self.window_size // 2 + 1)
        self.onset_buffer = []
        self.beat_positions = []

        # Adaptive threshold parameters
        self.alpha = 0.1  # Smoothing factor
        self.threshold = 0.0
        self.median_window = 8

        # Initialize onset detection
        self.onset_types = {
            OnsetDetectionFunction.ENERGY: self._energy_onset,
            OnsetDetectionFunction.COMPLEX: self._complex_onset,
            OnsetDetectionFunction.PHASE: self._phase_onset,
            OnsetDetectionFunction.SPECTRAL_FLUX: self._spectral_flux,
        }

        # Particle filter for beat tracking
        self.n_particles = 100
        self.particles = np.random.uniform(
            60 / self.max_bpm, 60 / self.min_bpm, self.n_particles
        )
        self.particle_weights = np.ones(self.n_particles) / self.n_particles

        # Tempo estimation parameters
        self.tempo_buffer_size = 8  # Seconds of tempo history
        self.tempo_history = []
        self.inter_beat_intervals = []
        self.tempo_scores = np.zeros(self.n_particles)

        # Tempo ranges (common BPM ranges in music)
        self.tempo_ranges = [
            (50, 80),  # Slow
            (80, 120),  # Medium
            (120, 160),  # Fast
            (160, 200),  # Very fast
        ]

    def _energy_onset(
        self, fft: np.ndarray, prev_fft: Optional[np.ndarray] = None
    ) -> float:
        """Energy-based onset detection"""
        return np.sum(np.abs(fft) ** 2)

    def _complex_onset(
        self, fft: np.ndarray, prev_fft: Optional[np.ndarray] = None
    ) -> float:
        """Complex domain onset detection"""
        if prev_fft is None:
            return 0.0

        # Predict current phase
        phase = np.angle(fft)
        phase_diff = phase - np.angle(prev_fft)
        predicted_phase = np.angle(prev_fft) + phase_diff

        # Complex difference
        complex_diff = np.abs(fft - np.abs(prev_fft) * np.exp(1j * predicted_phase))
        return np.sum(complex_diff)

    def _phase_onset(
        self, fft: np.ndarray, prev_fft: Optional[np.ndarray] = None
    ) -> float:
        """Phase-based onset detection"""
        if prev_fft is None:
            return 0.0

        phase = np.angle(fft)
        phase_diff = phase - np.angle(prev_fft)
        phase_diff = np.mod(phase_diff + np.pi, 2 * np.pi) - np.pi
        return np.sum(np.abs(phase_diff))

    def _spectral_flux(
        self, fft: np.ndarray, prev_fft: Optional[np.ndarray] = None
    ) -> float:
        """Spectral flux onset detection"""
        if prev_fft is None:
            return 0.0

        diff = np.abs(fft) - np.abs(prev_fft)
        return np.sum(np.maximum(0, diff))  # Half-wave rectification

    def _adaptive_threshold(self, onset: float) -> float:
        """Calculate adaptive threshold"""
        self.onset_buffer.append(onset)
        if len(self.onset_buffer) > self.median_window:
            self.onset_buffer.pop(0)

        # Moving median + dynamic threshold
        local_median = np.median(self.onset_buffer)
        self.threshold = (
            self.alpha * max(onset, local_median) + (1 - self.alpha) * self.threshold
        )
        return self.threshold

    def _update_particles(self, onset: float, current_time: float):
        """Update particle filter"""
        # Predict
        noise = np.random.normal(0, 0.02, self.n_particles)
        self.particles += noise

        # Update weights based on onset
        if onset > self.threshold:
            for i, period in enumerate(self.particles):
                expected_beat = current_time % period
                weight = np.exp(-0.5 * (expected_beat / period) ** 2)
                self.particle_weights[i] *= weight

        # Normalize weights
        self.particle_weights /= np.sum(self.particle_weights)

        # Resample if needed
        if 1.0 / np.sum(self.particle_weights**2) < self.n_particles / 2:
            indices = np.random.choice(
                self.n_particles, self.n_particles, p=self.particle_weights
            )
            self.particles = self.particles[indices]
            self.particle_weights = np.ones(self.n_particles) / self.n_particles

    def _estimate_tempo(self, current_time: float) -> float:
        """Improved tempo estimation"""
        # Calculate inter-beat intervals
        if len(self.beat_positions) >= 2:
            ibi = np.diff(self.beat_positions[-8:])  # Last 8 beats
            self.inter_beat_intervals.extend(ibi)

            # Keep reasonable length
            if len(self.inter_beat_intervals) > 50:
                self.inter_beat_intervals = self.inter_beat_intervals[-50:]

            if len(self.inter_beat_intervals) >= 4:
                # Convert intervals to BPM
                bpms = 60.0 / np.array(self.inter_beat_intervals)

                # Remove outliers
                bpms = bpms[(bpms >= self.min_bpm) & (bpms <= self.max_bpm)]

                if len(bpms) >= 2:  # Need at least 2 points for KDE
                    try:
                        # Find clusters of tempo estimates
                        kde = stats.gaussian_kde(bpms)
                        x = np.linspace(self.min_bpm, self.max_bpm, 200)
                        scores = kde(x)

                        # Find peaks in tempo distribution
                        peaks = signal.find_peaks(scores, distance=10)[0]
                        if len(peaks) > 0:
                            # Get the strongest peak
                            peak_idx = peaks[np.argmax(scores[peaks])]
                            tempo = x[peak_idx]

                            # Check if tempo is in a reasonable range
                            for low, high in self.tempo_ranges:
                                if low <= tempo <= high:
                                    # Found a reasonable tempo
                                    self.tempo_history.append(tempo)
                                    if len(self.tempo_history) > 10:
                                        self.tempo_history.pop(0)
                                    # Return median of recent tempos
                                    return float(np.median(self.tempo_history))
                    except Exception as e:
                        # Fall back to simple estimation if KDE fails
                        return float(np.median(bpms))

                elif len(bpms) == 1:
                    # Single BPM value
                    return float(bpms[0])

        # If no good tempo found, use particle filter estimate
        return 60.0 / np.average(self.particles, weights=self.particle_weights)

    def process(
        self, buffer: np.ndarray, current_time: float
    ) -> Tuple[List[BeatInfo], float]:
        """Process audio buffer and detect beats"""
        # Update audio buffer
        self.audio_buffer[: -len(buffer)] = self.audio_buffer[len(buffer) :]
        self.audio_buffer[-len(buffer) :] = buffer

        # Calculate FFT
        window = signal.hann(self.window_size)
        fft = np.fft.rfft(self.audio_buffer[-self.window_size :] * window)

        # Calculate onset using all methods and combine
        onsets = []
        prev_fft = np.fft.rfft(
            self.audio_buffer[-2 * self.window_size : -self.window_size] * window
        )

        for onset_func in self.onset_types.values():
            onset = onset_func(fft, prev_fft)
            onsets.append(onset)

        # Combine onset detection functions
        combined_onset = np.mean(onsets)
        threshold = self._adaptive_threshold(combined_onset)

        # Update beat tracking
        self._update_particles(combined_onset, current_time)

        # Improved tempo estimation
        tempo = self._estimate_tempo(current_time)

        # Detect beats with improved confidence
        beats = []
        if combined_onset > threshold:
            # Calculate additional beat information
            strength = (combined_onset - threshold) / threshold

            # Improved confidence calculation
            tempo_confidence = min(len(self.tempo_history) / 10.0, 1.0)
            onset_confidence = strength / (strength + 1.0)
            particle_confidence = np.max(self.particle_weights)

            confidence = (
                0.4 * tempo_confidence
                + 0.4 * onset_confidence
                + 0.2 * particle_confidence
            )

            # Determine beat type and subdivision
            period = 60.0 / tempo
            phase = current_time % period
            beat_type = "down" if phase < period * 0.25 else "up"
            sub_division = int(round(phase / (period / 4)))

            beat = BeatInfo(
                position=current_time,
                confidence=confidence,
                strength=strength,
                type=beat_type,
                sub_division=sub_division,
            )
            beats.append(beat)
            self.beat_positions.append(current_time)

        return beats, tempo
