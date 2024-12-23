import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, Tuple
import numpy as np


class MusicUnderstandingModel(nn.Module):
    """Deep model for music understanding"""

    def __init__(self, input_size: int, hidden_size: int = 512):
        super().__init__()

        # Feature processing
        self.feature_net = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Dropout(0.2),
        )

        # Task-specific heads
        self.genre_head = nn.Linear(hidden_size, 10)  # 10 genre classes
        self.mood_head = nn.Linear(hidden_size, 8)  # 8 mood classes
        self.energy_head = nn.Linear(hidden_size, 1)  # Energy level
        self.section_head = nn.Linear(hidden_size, 6)  # 6 section types

        # Event detection head
        self.event_head = nn.Linear(hidden_size, 4)  # 4 event types

    def forward(
        self, features: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Forward pass

        Args:
            features: Audio features from wav2vec

        Returns:
            genre_pred: Genre predictions
            mood_pred: Mood predictions
            energy_pred: Energy level prediction
            section_pred: Section type predictions
            event_pred: Event predictions
        """
        # Process features
        x = self.feature_net(features)

        # Task predictions
        genre_pred = F.softmax(self.genre_head(x), dim=-1)
        mood_pred = F.softmax(self.mood_head(x), dim=-1)
        energy_pred = torch.sigmoid(self.energy_head(x))
        section_pred = F.softmax(self.section_head(x), dim=-1)
        event_pred = torch.sigmoid(self.event_head(x))

        return genre_pred, mood_pred, energy_pred, section_pred, event_pred


class MusicAnalyzer:
    """High-level music analysis interface"""

    GENRES = [
        "electronic",
        "hip_hop",
        "pop",
        "rock",
        "ambient",
        "classical",
        "jazz",
        "metal",
        "folk",
        "other",
    ]

    MOODS = [
        "energetic",
        "calm",
        "happy",
        "sad",
        "aggressive",
        "ethereal",
        "dark",
        "uplifting",
    ]

    SECTIONS = ["intro", "verse", "chorus", "bridge", "breakdown", "outro"]

    EVENTS = ["drop", "build_up", "breakdown", "transition"]

    def __init__(self, config):
        self.config = config

        # Initialize model
        self.model = MusicUnderstandingModel(
            input_size=config.feature_size, hidden_size=512
        )

        # Move to device
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() and config.use_gpu else "cpu"
        )
        self.model.to(self.device)
        self.model.eval()

        # Analysis state
        self.genre_history = []
        self.mood_history = []
        self.section_history = []

    def analyze(self, features: torch.Tensor) -> Dict:
        """Analyze musical features

        Args:
            features: Audio features from wav2vec

        Returns:
            Dictionary containing musical analysis
        """
        with torch.no_grad():
            # Get predictions
            genre_pred, mood_pred, energy_pred, section_pred, event_pred = self.model(
                features
            )

            # Get top predictions
            genre_idx = torch.argmax(genre_pred, dim=-1)
            mood_idx = torch.argmax(mood_pred, dim=-1)
            section_idx = torch.argmax(section_pred, dim=-1)

            # Update history
            self.genre_history.append(self.GENRES[genre_idx])
            self.mood_history.append(self.MOODS[mood_idx])
            self.section_history.append(self.SECTIONS[section_idx])

            # Keep history bounded
            if len(self.genre_history) > 50:
                self.genre_history.pop(0)
                self.mood_history.pop(0)
                self.section_history.pop(0)

            # Detect events (with thresholding)
            events = {
                event: pred > 0.5 for event, pred in zip(self.EVENTS, event_pred[0])
            }

            return {
                "genre": self.GENRES[genre_idx],
                "mood": self.MOODS[mood_idx],
                "energy": float(energy_pred[0]),
                "section": self.SECTIONS[section_idx],
                "events": events,
                "confidence": {
                    "genre": float(torch.max(genre_pred)),
                    "mood": float(torch.max(mood_pred)),
                    "section": float(torch.max(section_pred)),
                },
            }
