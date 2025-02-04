import time
import threading
import atexit
from typing import Dict, Optional, Callable, Any
import numpy as np

from .pipelines.base import PipelineConfig
from .pipelines.realtime import RealtimePipeline
from .pipelines.analysis import AnalysisPipeline
from .state.manager import StateManager
from .buffer.circular import CircularAudioBuffer
from .devices import AudioDeviceManager


class AudioProcessor:
    """Main audio processing system integrating real-time and analysis pipelines"""

    def __init__(self, config: Optional[PipelineConfig] = None):
        self.config = config or PipelineConfig()

        # Initialize components
        self.state_manager = StateManager()
        self.device_manager = AudioDeviceManager()

        # Audio buffer for processing
        buffer_size = int(self.config.sample_rate * 2)  # 2 seconds of audio
        self.audio_buffer = CircularAudioBuffer(buffer_size)

        # Initialize pipelines
        self.realtime_pipeline = RealtimePipeline(self.config)
        self.analysis_pipeline = AnalysisPipeline(self.config)

        # Processing control
        self.is_running = False
        self.processing_thread = None
        self.analysis_thread = None
        self._lock = threading.Lock()
        self._shutdown_event = threading.Event()

        # Performance monitoring
        self.last_process_time = 0.0
        self.average_latency = 0.0
        self.latency_history = []
        self._max_latency_history = 100

        # Event callbacks
        self.callbacks = {
            "on_beat": [],
            "on_feature_update": [],
            "on_analysis_update": [],
            "on_error": [],
        }

        # Register cleanup on exit
        atexit.register(self.cleanup)

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register a callback for specific events"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def _notify_callbacks(self, event_type: str, data: Any) -> None:
        """Notify registered callbacks"""
        for callback in self.callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                self._handle_error(f"Callback error ({event_type}): {e}")

    def _handle_error(self, error_msg: str) -> None:
        """Handle errors in processing"""
        print(f"Error: {error_msg}")
        self._notify_callbacks("on_error", error_msg)

    def _process_audio(self, audio_data: np.ndarray) -> None:
        """Process incoming audio data"""
        if not self.is_running or self._shutdown_event.is_set():
            return

        start_time = time.time()

        try:
            # Update audio buffer
            self.audio_buffer.write(audio_data)

            # Real-time processing
            realtime_features = self.realtime_pipeline.process(audio_data)

            # Update state
            if realtime_features:
                self.state_manager.update_realtime_features(realtime_features)
                self._notify_callbacks("on_feature_update", realtime_features)

                # Check for beats
                if realtime_features.get("beat", {}).get("confidence", 0) > 0.5:
                    self._notify_callbacks("on_beat", realtime_features["beat"])

            # Monitor performance
            process_time = time.time() - start_time
            self.latency_history.append(process_time)
            if len(self.latency_history) > self._max_latency_history:
                self.latency_history.pop(0)
            self.average_latency = np.mean(self.latency_history)

        except Exception as e:
            self._handle_error(f"Processing error: {e}")

    def _run_analysis(self) -> None:
        """Run musical analysis in background"""
        while self.is_running and not self._shutdown_event.is_set():
            try:
                # Get latest audio buffer for analysis
                audio_data = self.audio_buffer.get_latest(
                    int(self.config.sample_rate * 5)  # 5 seconds for analysis
                )

                if audio_data is not None:
                    # Run analysis
                    analysis_results = self.analysis_pipeline.process(audio_data)

                    # Update state
                    if analysis_results:
                        self.state_manager.update_analysis_features(analysis_results)
                        self._notify_callbacks("on_analysis_update", analysis_results)

                # Sleep to prevent CPU overload
                time.sleep(0.1)

            except Exception as e:
                self._handle_error(f"Analysis error: {e}")
                if not self.is_running or self._shutdown_event.is_set():
                    break
                time.sleep(1.0)  # Wait before retrying

    def start(self, device_index: Optional[int] = None) -> None:
        """Start audio processing"""
        with self._lock:
            if self.is_running:
                return

            # Reset shutdown event
            self._shutdown_event.clear()

            # Initialize audio device
            try:
                self.device_manager.start(
                    device_index=device_index,
                    callback=self._process_audio,
                    sample_rate=self.config.sample_rate,
                    buffer_size=self.config.buffer_size,
                )
            except Exception as e:
                self._handle_error(f"Failed to start audio device: {e}")
                return

            # Start pipelines
            self.realtime_pipeline.start()
            self.analysis_pipeline.start()

            # Start analysis thread
            self.is_running = True
            self.analysis_thread = threading.Thread(target=self._run_analysis)
            self.analysis_thread.daemon = True
            self.analysis_thread.start()

    def stop(self) -> None:
        """Stop audio processing"""
        with self._lock:
            if not self.is_running:
                return

            self.is_running = False
            self._shutdown_event.set()

            # Stop device
            self.device_manager.stop()

            # Stop pipelines
            self.realtime_pipeline.stop()
            self.analysis_pipeline.stop()

            # Wait for analysis thread
            if self.analysis_thread and self.analysis_thread.is_alive():
                self.analysis_thread.join(timeout=2.0)
                if self.analysis_thread.is_alive():
                    self._handle_error("Analysis thread failed to stop")

            # Clear state
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up resources"""
        self.stop()
        self.audio_buffer.clear()
        self.latency_history.clear()
        self.callbacks = {k: [] for k in self.callbacks}
        self.state_manager.clear()

    def get_state(self) -> Dict[str, Any]:
        """Get current audio processing state"""
        return {
            "audio": self.state_manager.current_state,
            "performance": {
                "average_latency": self.average_latency,
                "buffer_available": self.audio_buffer.available_samples,
                "is_running": self.is_running,
                "error_count": len([c for c in self.callbacks["on_error"] if c]),
            },
        }

    def __del__(self) -> None:
        """Ensure cleanup on deletion"""
        self.cleanup()
