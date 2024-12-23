import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Tuple, Optional


class TemporalBlock(nn.Module):
    """TCN block for beat detection"""

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        stride: int,
        dilation: int,
        padding: int,
        dropout: float = 0.1,
    ):
        super().__init__()

        self.conv1 = nn.Conv1d(
            in_channels,
            out_channels,
            kernel_size,
            stride=stride,
            padding=padding,
            dilation=dilation,
        )
        self.bn1 = nn.BatchNorm1d(out_channels)
        self.conv2 = nn.Conv1d(
            out_channels,
            out_channels,
            kernel_size,
            stride=stride,
            padding=padding,
            dilation=dilation,
        )
        self.bn2 = nn.BatchNorm1d(out_channels)
        self.dropout = nn.Dropout(dropout)

        self.downsample = (
            nn.Conv1d(in_channels, out_channels, 1)
            if in_channels != out_channels
            else None
        )

    def forward(self, x):
        """Forward pass"""
        residual = x

        # First conv layer
        out = self.conv1(x)
        out = self.bn1(out)
        out = F.relu(out)
        out = self.dropout(out)

        # Second conv layer
        out = self.conv2(out)
        out = self.bn2(out)

        # Residual connection
        if self.downsample is not None:
            residual = self.downsample(x)

        return F.relu(out + residual)


class BeatTCN(nn.Module):
    """Beat detection using Temporal Convolutional Network"""

    def __init__(
        self,
        input_size: int,
        num_channels: List[int],
        kernel_size: int = 3,
        dropout: float = 0.1,
    ):
        super().__init__()

        layers = []
        num_levels = len(num_channels)

        for i in range(num_levels):
            dilation = 2**i
            in_channels = input_size if i == 0 else num_channels[i - 1]
            out_channels = num_channels[i]

            layers.append(
                TemporalBlock(
                    in_channels,
                    out_channels,
                    kernel_size,
                    stride=1,
                    dilation=dilation,
                    padding=(kernel_size - 1) * dilation,
                    dropout=dropout,
                )
            )

        self.network = nn.Sequential(*layers)
        self.beat_head = nn.Conv1d(num_channels[-1], 1, 1)
        self.tempo_head = nn.Linear(num_channels[-1], 1)

    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """Forward pass

        Args:
            x: Input tensor of shape (batch_size, channels, time)

        Returns:
            beat_predictions: Beat activation function
            tempo_prediction: Estimated tempo in BPM
        """
        features = self.network(x)

        # Beat detection
        beat_predictions = torch.sigmoid(self.beat_head(features))

        # Tempo estimation
        tempo_features = torch.mean(features, dim=2)
        tempo_prediction = self.tempo_head(tempo_features)

        return beat_predictions, tempo_prediction


class BeatDetector:
    """High-level beat detection interface"""

    def __init__(self, config: AnalysisConfig):
        self.config = config

        # Initialize model
        self.model = BeatTCN(
            input_size=config.feature_size,
            num_channels=[128, 128, 256, 256, 512],
            kernel_size=3,
            dropout=0.1,
        )

        # Load pre-trained weights
        self._load_weights()

        # Move to device
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() and config.use_gpu else "cpu"
        )
        self.model.to(self.device)
        self.model.eval()

        # Analysis state
        self.beat_history = []
        self.tempo_history = []

    def _load_weights(self):
        """Load pre-trained model weights"""
        # TODO: Load actual pre-trained weights
        pass

    def process(
        self, features: torch.Tensor, current_time: float
    ) -> Tuple[List[float], float, float]:
        """Process audio features

        Args:
            features: Audio features from wav2vec
            current_time: Current timestamp

        Returns:
            beats: List of beat timestamps
            tempo: Estimated tempo in BPM
            confidence: Beat detection confidence
        """
        with torch.no_grad():
            beat_pred, tempo_pred = self.model(features)

            # Process beat predictions
            beats = []
            confidence = 0.0

            if torch.any(beat_pred > 0.5):
                beat_times = current_time + (
                    torch.where(beat_pred > 0.5)[1]
                    * self.config.hop_length
                    / self.config.sample_rate
                )
                beats.extend(beat_times.cpu().numpy())
                confidence = float(torch.max(beat_pred))

            # Process tempo prediction
            tempo = float(tempo_pred.cpu().numpy())

            return beats, tempo, confidence
