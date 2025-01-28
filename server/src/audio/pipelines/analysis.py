import librosa
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from .base import AudioPipeline, PipelineConfig
from ..state.models import AudioState


class AnalysisPipeline(AudioPipeline):
    """Deep analysis pipeline using Librosa for musical understanding"""

    def __init__(self, config: Optional[PipelineConfig] = None):
        super().__init__(config)
        self.frame_size = self.config.buffer_size
        self.hop_size = self.config.hop_length
        self.analysis_buffer = []  # Collect enough audio for analysis
        self.min_analysis_duration = 5  # Minimum seconds needed for analysis

    def _initialize(self) -> None:
        """Initialize analysis components"""
        # Analysis state
        self.current_analysis = {
            "structure": {"boundaries": [], "labels": [], "confidence": 0.0},
            "harmony": {
                "key": None,
                "mode": None,
                "chords": [],
                "chord_timestamps": [],
            },
            "separation": {"harmonic": None, "percussive": None},
            "genre": {"tags": [], "confidence": []},
        }

    def _analyze_structure(self, y: np.ndarray) -> Dict[str, Any]:
        """Analyze musical structure using recurrence matrix"""
        # Compute mel spectrogram for structure analysis
        mel_spec = librosa.feature.melspectrogram(
            y=y, sr=self.config.sample_rate, n_mels=128, hop_length=self.hop_size
        )
        mel_db = librosa.power_to_db(mel_spec, ref=np.max)

        # Compute recurrence matrix
        R = librosa.segment.recurrence_matrix(mel_db, mode="affinity", sym=True)

        # Find segment boundaries
        boundaries = librosa.segment.detect_peaks(
            librosa.segment.structure_feature(R), size=8
        )

        # Convert frame indices to timestamps
        boundary_times = librosa.frames_to_time(boundaries, sr=self.config.sample_rate)

        return {
            "boundaries": boundary_times.tolist(),
            "labels": [f"Section_{i}" for i in range(len(boundaries))],
            "confidence": float(np.mean(R[boundaries, :])),
        }

    def _analyze_harmony(self, y: np.ndarray) -> Dict[str, Any]:
        """Analyze harmonic content (key, mode, chords)"""
        # Key detection
        key_chroma = librosa.feature.chroma_cqt(
            y=y, sr=self.config.sample_rate, hop_length=self.hop_size
        )
        key = librosa.key_to_notes(np.argmax(np.mean(key_chroma, axis=1)))

        # Chord detection
        chroma = librosa.feature.chroma_cqt(
            y=y, sr=self.config.sample_rate, hop_length=self.hop_size
        )

        # Simplified chord detection (could be enhanced with a proper chord model)
        chord_timestamps = librosa.times_like(chroma)
        major_profile = np.array([1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 0, 0])
        minor_profile = np.array([1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0])

        chords = []
        for i in range(chroma.shape[1]):
            frame = chroma[:, i]
            root = np.argmax(frame)
            # Simple major/minor classification
            major_corr = np.correlate(frame, np.roll(major_profile, root))
            minor_corr = np.correlate(frame, np.roll(minor_profile, root))
            chord_type = "maj" if major_corr > minor_corr else "min"
            chords.append(f"{librosa.key_to_notes(root)}{chord_type}")

        return {
            "key": key,
            "mode": "major" if np.mean(major_corr) > np.mean(minor_corr) else "minor",
            "chords": chords,
            "chord_timestamps": chord_timestamps.tolist(),
        }

    def _harmonic_percussive_separation(self, y: np.ndarray) -> Dict[str, np.ndarray]:
        """Separate harmonic and percussive components"""
        harmonic, percussive = librosa.effects.hpss(y)
        return {"harmonic": harmonic, "percussive": percussive}

    def process(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Process audio for long-term analysis"""
        if not self.running:
            return {}

        # Accumulate audio data
        self.analysis_buffer.extend(audio_data.flatten())

        # Only analyze when we have enough data
        if (
            len(self.analysis_buffer)
            >= self.min_analysis_duration * self.config.sample_rate
        ):
            y = np.array(self.analysis_buffer)

            # Perform analysis
            self.current_analysis["structure"] = self._analyze_structure(y)
            self.current_analysis["harmony"] = self._analyze_harmony(y)
            self.current_analysis["separation"] = self._harmonic_percussive_separation(
                y
            )

            # Clear buffer after analysis
            self.analysis_buffer = []

        return self.current_analysis

    def reset(self) -> None:
        """Reset analysis state"""
        self.analysis_buffer = []
        self._initialize()
