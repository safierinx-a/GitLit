import torch
import torchaudio
import torchaudio.transforms as T
import numpy as np
from typing import Dict


class FeatureExtractor:
    """Audio feature extraction using torchaudio's pretrained models"""

    def __init__(self, config):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Initialize transforms
        self.mel_spec = T.MelSpectrogram(
            sample_rate=config.sample_rate,
            n_fft=2048,
            hop_length=512,
            n_mels=128,
            f_min=20,
            f_max=8000,
        ).to(self.device)

        # Initialize pretrained models
        self.bundle = torchaudio.pipelines.WAV2VEC2_BASE
        self.model = self.bundle.get_model().to(self.device)
        self.model.eval()

        print(f"Feature extractor initialized on {self.device}")

    def extract_features(self, audio: np.ndarray) -> Dict:
        """Extract rich audio features"""
        with torch.no_grad():
            # Convert to tensor
            audio_tensor = torch.from_numpy(audio).float().to(self.device)

            # Get mel spectrogram
            mel = self.mel_spec(audio_tensor)

            # Get wav2vec features
            wav2vec_out = self.model(audio_tensor.unsqueeze(0))

            return {
                "mel": mel.cpu().numpy(),
                "wav2vec": wav2vec_out.cpu().numpy(),
                "spectral": self._analyze_spectrum(mel),
                "timbre": self._analyze_timbre(mel),
            }

    def _analyze_spectrum(self, mel_spec: torch.Tensor) -> Dict:
        """Analyze mel spectrogram for frequency information"""
        # Define frequency bands (mel scale)
        bands = {
            "sub_bass": (0, 4),  # 20-60 Hz
            "bass": (4, 8),  # 60-250 Hz
            "low_mid": (8, 16),  # 250-500 Hz
            "mid": (16, 32),  # 500-2000 Hz
            "high_mid": (32, 48),  # 2000-4000 Hz
            "high": (48, 80),  # 4000-8000 Hz
            "presence": (80, 128),  # 8000+ Hz
        }

        energies = {}
        for band, (start, end) in bands.items():
            energy = torch.mean(mel_spec[:, start:end]).item()
            energies[band] = energy

        return energies

    def _analyze_timbre(self, mel_spec: torch.Tensor) -> Dict:
        """Analyze timbre characteristics"""
        # Spectral centroid (brightness)
        freqs = torch.linspace(0, self.config.sample_rate / 2, mel_spec.size(1))
        centroid = torch.sum(freqs * torch.mean(mel_spec, dim=0)) / torch.sum(mel_spec)

        # Spectral rolloff (warmth)
        cumsum = torch.cumsum(torch.mean(mel_spec, dim=0), dim=0)
        rolloff = torch.where(cumsum > 0.85 * torch.sum(mel_spec))[0][0]

        return {
            "brightness": float(centroid),
            "warmth": float(128 - rolloff) / 128,
            "roughness": float(torch.std(mel_spec)),
            "attack": float(torch.mean(torch.diff(mel_spec, dim=0).clip(min=0))),
        }
