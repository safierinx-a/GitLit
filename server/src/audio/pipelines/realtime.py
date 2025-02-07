import numpy as np
from typing import Dict, Any, Optional

from .base import PipelineConfig, AudioPipeline
from ..analysis.realtime.onset import OnsetDetector


class RealtimePipeline(AudioPipeline):
    """Real-time audio processing pipeline for immediate feature extraction"""

    def _initialize(self) -> None:
        """Initialize pipeline components"""
        # Initialize feature extractors
        self.onset_detector = OnsetDetector(
            sample_rate=self.config.sample_rate,
            frame_size=self.config.buffer_size,
            hop_size=self.config.hop_length,
        )

        # State tracking
        self.last_rms = 0.0
        self.last_onset = False
        self.feature_history = []
        self._max_history = 100

    def process(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Process audio frame and extract features"""
        if not self.is_running or len(audio_data) == 0:
            return {}

        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Calculate basic features
        rms = np.sqrt(np.mean(np.square(audio_data)))
        peak = np.max(np.abs(audio_data))
        zero_crossings = np.sum(np.diff(np.signbit(audio_data)))

        # Detect onsets
        onset_detected = self.onset_detector.process(audio_data)

        # Update state
        self.last_rms = rms
        self.last_onset = onset_detected

        # Store features
        features = {
            "rms": float(rms),
            "peak": float(peak),
            "zero_crossings": int(zero_crossings),
            "onset_detected": onset_detected,
        }

        self.feature_history.append(features)
        if len(self.feature_history) > self._max_history:
            self.feature_history.pop(0)

        return features

    def reset(self) -> None:
        """Reset pipeline state"""
        self.last_rms = 0.0
        self.last_onset = False
        self.feature_history.clear()
        if hasattr(self, "onset_detector"):
            self.onset_detector.reset()

    def get_state(self) -> Dict[str, Any]:
        """Get current pipeline state"""
        return {
            "last_rms": self.last_rms,
            "last_onset": self.last_onset,
            "feature_history_length": len(self.feature_history),
        }
