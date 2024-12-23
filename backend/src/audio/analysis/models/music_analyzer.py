import torch
import torchaudio
import numpy as np
from typing import Dict


class MusicAnalyzer:
    """Music analysis using torchaudio's pretrained models"""

    def __init__(self, config):
        self.config = config
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Load pretrained classifier
        self.bundle = torchaudio.pipelines.HUBERT_BASE
        self.model = self.bundle.get_model().to(self.device)
        self.model.eval()

        # Analysis state
        self.feature_history = []
        self.energy_history = []

        print("Music analyzer initialized")

    def analyze(self, audio: np.ndarray, features: Dict) -> Dict:
        """Analyze musical characteristics"""
        try:
            with torch.no_grad():
                # Extract high-level features
                audio_tensor = torch.from_numpy(audio).float().to(self.device)
                emissions, _ = self.model(audio_tensor.unsqueeze(0))

                # Analyze musical structure
                feature_seq = emissions.squeeze().cpu().numpy()
                self.feature_history.append(feature_seq)
                if len(self.feature_history) > 50:
                    self.feature_history.pop(0)

                # Detect musical events
                spectral = features["spectral"]
                energy = np.mean(list(spectral.values()))
                self.energy_history.append(energy)
                if len(self.energy_history) > 100:
                    self.energy_history.pop(0)

                # Analyze energy trend
                energy_trend = np.polyfit(
                    np.arange(len(self.energy_history)), self.energy_history, 1
                )[0]

                return {
                    "structure": {
                        "section_change": self._detect_section_change(feature_seq),
                        "complexity": float(np.std(feature_seq)),
                    },
                    "energy": {"level": float(energy), "trend": float(energy_trend)},
                    "events": {
                        "build_up": energy_trend > 0.1 and energy > 0.6,
                        "drop": self._detect_drop(spectral, energy),
                    },
                }

        except Exception as e:
            print(f"Error in music analysis: {e}")
            return {
                "structure": {"section_change": False, "complexity": 0.0},
                "energy": {"level": 0.0, "trend": 0.0},
                "events": {"build_up": False, "drop": False},
            }

    def _detect_section_change(self, features: np.ndarray) -> bool:
        """Detect significant changes in musical structure"""
        if len(self.feature_history) < 2:
            return False

        current = features.mean(axis=0)
        previous = self.feature_history[-2].mean(axis=0)
        diff = np.mean(np.abs(current - previous))

        return diff > np.std(features) * 2

    def _detect_drop(self, spectral: Dict, current_energy: float) -> bool:
        """Detect musical drops"""
        if len(self.energy_history) < 10:
            return False

        # Check for sudden energy increase with bass emphasis
        recent_energy = np.mean(self.energy_history[-5:])
        past_energy = np.mean(self.energy_history[-10:-5])

        bass_energy = spectral["bass"] + spectral["sub_bass"]
        high_energy = spectral["high"] + spectral["presence"]

        return (
            recent_energy > past_energy * 1.5
            and bass_energy > high_energy * 1.5
            and current_energy > 0.7
        )
