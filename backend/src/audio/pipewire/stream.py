import pipewire as pw
import numpy as np
from typing import Optional, Callable
from ..config import AudioConfig


class PWStream:
    """PipeWire stream handler"""

    def __init__(self, config: AudioConfig):
        self.config = config
        self.loop = pw.Loop()
        self.stream: Optional[pw.Stream] = None
        self.callback: Optional[Callable] = None

    def setup(self, callback: Callable[[np.ndarray], None]):
        """Set up PipeWire stream with callback"""
        self.callback = callback
        self.stream = pw.Stream(self.loop)

        # Configure stream
        self.stream.connect_capture(
            audio_format=pw.AudioFormat.FLOAT32,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            target=self.config.target,
        )

        # Set up data callback
        self.stream.set_data_callback(self._process_data)

    def _process_data(self, data: np.ndarray):
        """Process incoming audio data"""
        if self.callback:
            self.callback(data)

    def start(self):
        """Start the stream"""
        if self.stream:
            self.stream.activate()
            self.loop.start()

    def stop(self):
        """Stop the stream"""
        if self.stream:
            self.loop.stop()
            self.stream.deactivate()

    def cleanup(self):
        """Clean up resources"""
        if self.stream:
            self.stream.disconnect()
        self.loop.cleanup()
