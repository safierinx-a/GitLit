import torch
import torch.nn.functional as F
import torchaudio
from transformers import Wav2Vec2Processor, Wav2Vec2Model
from typing import Dict, Optional
import numpy as np


class AudioFeatureExtractor:
    """Audio feature extraction using wav2vec 2.0"""

    def __init__(self, config):
        self.config = config

        # Initialize wav2vec model and processor
        self.processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base")
        self.model = Wav2Vec2Model.from_pretrained("facebook/wav2vec2-base")

        # Move to device
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() and config.use_gpu else "cpu"
        )
        self.model.to(self.device)
        self.model.eval()

        # Mel spectrogram transform for additional features
        self.mel_transform = torchaudio.transforms.MelSpectrogram(
            sample_rate=config.sample_rate,
            n_fft=2048,
            hop_length=config.hop_length,
            n_mels=128,
        ).to(self.device)

        # Feature history
        self.feature_history = []
        self.spectral_history = []

    def extract_features(self, audio: np.ndarray) -> Dict[str, torch.Tensor]:
        """Extract rich audio features

        Args:
            audio: Audio buffer (mono)

        Returns:
            Dictionary containing:
                - wav2vec_features: High-level audio features
                - mel_features: Mel spectrogram features
                - spectral_features: Frequency band energies
        """
        with torch.no_grad():
            # Prepare input
            inputs = self.processor(
                audio, sampling_rate=self.config.sample_rate, return_tensors="pt"
            )
            inputs = inputs.to(self.device)

            # Extract wav2vec features
            outputs = self.model(**inputs)
            features = outputs.last_hidden_state

            # Extract mel spectrogram
            audio_tensor = torch.from_numpy(audio).float().to(self.device)
            mel_spec = self.mel_transform(audio_tensor)

            # Calculate frequency band energies
            spectral_features = self._calculate_band_energies(mel_spec)

            # Update history
            self.feature_history.append(features)
            self.spectral_history.append(spectral_features)

            if len(self.feature_history) > 10:
                self.feature_history.pop(0)
                self.spectral_history.pop(0)

            return {
                "wav2vec_features": features,
                "mel_features": mel_spec,
                "spectral_features": spectral_features,
                "timbre": self._extract_timbre_features(mel_spec),
            }

    def _calculate_band_energies(self, mel_spec: torch.Tensor) -> Dict[str, float]:
        """Calculate energy in frequency bands"""
        # Define frequency band ranges in mel bins
        bands = {
            "sub_bass": (0, 4),  # ~20-60 Hz
            "bass": (4, 8),  # ~60-250 Hz
            "low_mid": (8, 16),  # ~250-500 Hz
            "mid": (16, 32),  # ~500-2000 Hz
            "high_mid": (32, 48),  # ~2000-4000 Hz
            "high": (48, 80),  # ~4000-8000 Hz
            "presence": (80, 128),  # ~8000-20000 Hz
        }

        energies = {}
        for band, (start, end) in bands.items():
            energy = torch.mean(mel_spec[:, start:end]).item()
            energies[band] = energy

        return energies

    def _extract_timbre_features(self, mel_spec: torch.Tensor) -> Dict[str, float]:
        """Extract timbral characteristics"""
        # Spectral centroid (brightness)
        freqs = torch.linspace(0, self.config.sample_rate / 2, mel_spec.size(1))
        centroid = torch.sum(freqs * torch.mean(mel_spec, dim=0)) / torch.sum(mel_spec)

        # Spectral rolloff (warmth)
        cumsum = torch.cumsum(torch.mean(mel_spec, dim=0), dim=0)
        rolloff = torch.where(cumsum > 0.85 * torch.sum(mel_spec))[0][0]

        # Spectral flatness (roughness)
        flatness = torch.exp(torch.mean(torch.log(mel_spec + 1e-6))) / (
            torch.mean(mel_spec) + 1e-6
        )

        # Attack time
        onset_env = torch.mean(torch.diff(mel_spec, dim=0).clip(min=0), dim=0)
        attack = torch.mean(onset_env)

        return {
            "brightness": centroid.item(),
            "warmth": (128 - rolloff.item()) / 128,
            "roughness": flatness.item(),
            "attack": attack.item(),
        }

    def get_feature_delta(self) -> Optional[torch.Tensor]:
        """Calculate feature change over time"""
        if len(self.feature_history) >= 2:
            return torch.mean(
                torch.abs(self.feature_history[-1] - self.feature_history[-2])
            ).item()
        return None
