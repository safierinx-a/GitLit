from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, Optional
import numpy as np


@dataclass
class PipelineConfig:
    """Base configuration for audio pipelines"""

    sample_rate: int = 44100
    buffer_size: int = 2048
    hop_length: int = 512
    history_size: int = 4  # seconds


class AudioPipeline(ABC):
    """Base class for audio processing pipelines"""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()
        self.is_running = False
        self._initialize()

    @abstractmethod
    def _initialize(self) -> None:
        """Initialize pipeline-specific components"""
        pass

    @abstractmethod
    def process(self, audio_data: np.ndarray) -> Dict[str, Any]:
        """Process audio data and return features"""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset pipeline state"""
        pass

    def start(self) -> None:
        """Start the pipeline"""
        self.is_running = True

    def stop(self) -> None:
        """Stop the pipeline"""
        self.is_running = False
        self.reset()

    @property
    def running(self) -> bool:
        """Check if pipeline is running"""
        return self.is_running
