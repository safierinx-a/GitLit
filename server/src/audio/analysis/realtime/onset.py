from dataclasses import dataclass
from typing import List, Tuple

import essentia
import numpy as np


@dataclass
class OnsetDetection:
    """Onset detection results"""

    positions: List[float]  # Onset positions in seconds
    strengths: List[float]  # Onset detection function values
    confidence: float  # Overall detection confidence


class OnsetDetector:
    """Real-time onset detection using multiple detection functions"""

    def __init__(self, frame_size: int, hop_size: int, sample_rate: int = 44100):
        self.frame_size = frame_size
        self.hop_size = hop_size
        self.sample_rate = sample_rate

        # Initialize Essentia algorithms
        self.w = essentia.standard.Windowing(type="hann")
        self.spectrum = essentia.standard.Spectrum(size=frame_size)

        # Multiple onset detection functions for robustness
        self.onset_hfc = essentia.standard.OnsetDetection(
            method="hfc", sampleRate=sample_rate
        )
        self.onset_complex = essentia.standard.OnsetDetection(
            method="complex", sampleRate=sample_rate
        )
        self.onset_flux = essentia.standard.OnsetDetection(
            method="flux", sampleRate=sample_rate
        )

        # Dynamic thresholding
        self.threshold = 0.3  # Initial threshold
        self.alpha = 0.05  # Threshold adaptation rate

        # State
        self.prev_spectrum = None
        self.detection_buffer = []
        self.last_onset_time = 0.0

    def process(self, audio_data: np.ndarray) -> bool:
        """Process audio data and return whether an onset was detected"""
        # Ensure frame size
        if len(audio_data) != self.frame_size:
            # Pad or truncate to match frame size
            if len(audio_data) < self.frame_size:
                audio_data = np.pad(audio_data, (0, self.frame_size - len(audio_data)))
            else:
                audio_data = audio_data[: self.frame_size]

        # Process frame
        detection = self.process_frame(audio_data)
        return len(detection.positions) > 0

    def process_frame(self, frame: np.ndarray) -> OnsetDetection:
        """Process a single frame and detect onsets"""
        # Prepare frame
        windowed = self.w(frame)
        spectrum = self.spectrum(windowed)

        # Calculate detection functions
        onset_hfc = self.onset_hfc(spectrum, self.prev_spectrum)
        onset_complex = self.onset_complex(spectrum, self.prev_spectrum)
        onset_flux = self.onset_flux(spectrum, self.prev_spectrum)

        # Combine detection functions
        detection = (onset_hfc + onset_complex + onset_flux) / 3.0

        # Update state
        self.prev_spectrum = spectrum
        self.detection_buffer.append(float(detection))

        # Keep buffer size manageable
        if len(self.detection_buffer) > 44100 // self.hop_size:  # ~1 second
            self.detection_buffer.pop(0)

        # Dynamic threshold
        local_mean = np.mean(self.detection_buffer)
        local_std = np.std(self.detection_buffer)
        dynamic_threshold = local_mean + self.threshold * local_std

        # Detect onsets
        current_time = len(self.detection_buffer) * self.hop_size / self.sample_rate
        is_onset = detection > dynamic_threshold

        # Minimum time between onsets (50ms)
        min_onset_gap = 0.05  # seconds
        if is_onset and (current_time - self.last_onset_time) > min_onset_gap:
            self.last_onset_time = current_time
            confidence = (detection - dynamic_threshold) / dynamic_threshold
            return OnsetDetection(
                positions=[current_time],
                strengths=[float(detection)],
                confidence=float(confidence),
            )

        return OnsetDetection(
            positions=[], strengths=[float(detection)], confidence=0.0
        )

    def reset(self) -> None:
        """Reset detector state"""
        self.prev_spectrum = None
        self.detection_buffer = []
        self.last_onset_time = 0.0
