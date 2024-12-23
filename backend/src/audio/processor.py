import numpy as np
import pyaudio
import time
from typing import Dict, Optional, Callable
from .analysis.models.beat_tracker import BeatTracker
from .analysis.models.feature_extractor import FeatureExtractor
from .analysis.models.music_analyzer import MusicAnalyzer
from dataclasses import dataclass


@dataclass
class ProcessorConfig:
    """Audio processor configuration"""

    sample_rate: int = 44100
    buffer_size: int = 2048
    hop_length: int = 512
    history_size: int = 4  # seconds
    use_gpu: bool = False


class AudioProcessor:
    """Main audio processor integrating SOTA models"""

    SUPPORTED_RATES = [44100, 48000]  # Common audio sample rates

    def __init__(self, config: Optional[ProcessorConfig] = None):
        self.config = config or ProcessorConfig()
        self.pa = pyaudio.PyAudio()

        # Initialize audio components
        self.stream = None
        self.current_device_index = None
        self.current_sample_rate = 44100  # Default rate

        # Initialize analysis models
        print("Initializing analysis models...")
        self.beat_tracker = BeatTracker(self.config)
        self.feature_extractor = FeatureExtractor(self.config)
        self.music_analyzer = MusicAnalyzer(self.config)

        # Analysis state
        self.audio_buffer = np.zeros(
            int(self.config.history_size * self.config.sample_rate)
        )
        self.current_features = {}
        self.current_analysis = {}

        # Callbacks
        self.on_beat = None
        self.on_feature_update = None
        self.on_analysis_update = None

        print("Audio processor initialized")

    def register_callbacks(
        self,
        on_beat: Optional[Callable] = None,
        on_feature_update: Optional[Callable] = None,
        on_analysis_update: Optional[Callable] = None,
    ):
        """Register callback functions"""
        self.on_beat = on_beat
        self.on_feature_update = on_feature_update
        self.on_analysis_update = on_analysis_update

    def list_devices(self) -> Dict:
        """List available audio input devices"""
        devices = {}
        for i in range(self.pa.get_device_count()):
            dev_info = self.pa.get_device_info_by_index(i)
            if dev_info["maxInputChannels"] > 0:
                devices[i] = {
                    "index": i,
                    "name": dev_info["name"],
                    "channels": dev_info["maxInputChannels"],
                    "sample_rate": int(dev_info["defaultSampleRate"]),
                    "is_default": i == self.pa.get_default_input_device_info()["index"],
                }
        return devices

    def get_default_device(self) -> Optional[Dict]:
        """Get default input device, preferring USB audio"""
        devices = self.list_devices()

        # First try to find USB audio device
        for dev in devices.values():
            if "usb" in dev["name"].lower():
                return dev

        # Fall back to system default
        for dev in devices.values():
            if dev["is_default"]:
                return dev

        # Last resort: first available input device
        return next(iter(devices.values())) if devices else None

    def get_device_sample_rate(self, device_index: int) -> int:
        """Get supported sample rate for device"""
        device_info = self.pa.get_device_info_by_index(device_index)
        default_rate = int(device_info["defaultSampleRate"])

        # Check if default rate is supported
        if default_rate in self.SUPPORTED_RATES:
            return default_rate

        # Try to find a supported rate
        for rate in self.SUPPORTED_RATES:
            try:
                supported = self.pa.is_format_supported(
                    rate,
                    input_device=device_index,
                    input_channels=1,
                    input_format=pyaudio.paFloat32,
                )
                if supported:
                    return rate
            except ValueError:
                continue

        # Fall back to 44100 if nothing else works
        return 44100

    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Process incoming audio data"""
        try:
            # Convert to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.float32)

            # Update audio buffer
            self.audio_buffer = np.roll(self.audio_buffer, -len(audio_data))
            self.audio_buffer[-len(audio_data) :] = audio_data

            # Get current timestamp
            current_time = time.time()

            # Extract features
            self.current_features = self.feature_extractor.extract_features(
                self.audio_buffer
            )

            if self.on_feature_update:
                self.on_feature_update(self.current_features)

            # Process beats
            beat_info = self.beat_tracker.process(self.audio_buffer, current_time)

            if beat_info["beats"] and self.on_beat:
                self.on_beat(beat_info)

            # Analyze music
            self.current_analysis = self.music_analyzer.analyze(
                self.audio_buffer, self.current_features
            )

            if self.on_analysis_update:
                self.on_analysis_update(self.current_analysis)

        except Exception as e:
            print(f"Error in audio processing: {e}")

        return (in_data, pyaudio.paContinue)

    def start(self, device_index: Optional[int] = None):
        """Start audio processing"""
        if self.stream is not None:
            self.stop()

        # Use specified device or find default
        if device_index is None:
            default_dev = self.get_default_device()
            if default_dev:
                device_index = default_dev["index"]
            else:
                raise RuntimeError("No input device available")

        # Get device info and supported sample rate
        device_info = self.pa.get_device_info_by_index(device_index)
        self.current_sample_rate = self.get_device_sample_rate(device_index)

        print(f"Starting audio capture on: {device_info['name']}")
        print(f"Using sample rate: {self.current_sample_rate}Hz")

        try:
            self.stream = self.pa.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.current_sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.config.buffer_size,
                stream_callback=self._audio_callback,
            )

            self.current_device_index = device_index
            self.stream.start_stream()
            print("Audio capture started")

        except Exception as e:
            print(f"Error starting audio capture: {e}")
            self.cleanup()
            raise

    def get_current_analysis(self) -> Dict:
        """Get current audio analysis results"""
        return {
            "beat": {
                "tempo": self.beat_tracker.current_tempo,
                "last_beats": self.beat_tracker.beat_history[-5:],
            },
            "spectral": self.current_features.get("spectral", {}),
            "music": self.current_analysis,
        }

    def stop(self):
        """Stop audio processing"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def cleanup(self):
        """Clean up resources"""
        self.stop()
        if self.pa:
            self.pa.terminate()
