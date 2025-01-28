import pyaudio
import numpy as np
import threading
import time
from typing import Dict, Optional, Callable, List, Any, Set


class AudioDeviceManager:
    """Manages audio input devices and streams with hot-plug support"""

    SUPPORTED_RATES = [44100, 48000]  # Common audio sample rates

    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.current_device = None
        self.current_sample_rate = 44100
        self.callback = None

        # Device monitoring
        self._known_devices: Set[str] = set()
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False
        self._lock = threading.Lock()

        # Device change callbacks
        self.on_device_added: List[Callable[[Dict[str, Any]], None]] = []
        self.on_device_removed: List[Callable[[Dict[str, Any]], None]] = []
        self.on_device_error: List[Callable[[str], None]] = []

        # Auto-reconnect settings
        self.auto_reconnect = True
        self.reconnect_delay = 1.0  # seconds
        self._preferred_device_index: Optional[int] = None

    def _get_device_signature(self, device_info: Dict[str, Any]) -> str:
        """Generate unique device signature"""
        return f"{device_info['name']}_{device_info['index']}"

    def _monitor_devices(self) -> None:
        """Monitor for device changes"""
        while self._monitor_running:
            try:
                current_devices = self.list_devices()
                current_signatures = {
                    self._get_device_signature(dev): dev
                    for dev in current_devices.values()
                }

                # Check for new devices
                for sig, dev in current_signatures.items():
                    if sig not in self._known_devices:
                        self._known_devices.add(sig)
                        for callback in self.on_device_added:
                            try:
                                callback(dev)
                            except Exception as e:
                                print(f"Error in device added callback: {e}")

                # Check for removed devices
                for sig in list(self._known_devices):
                    if sig not in current_signatures:
                        self._known_devices.remove(sig)
                        removed_dev = next(
                            (
                                d
                                for d in current_devices.values()
                                if self._get_device_signature(d) == sig
                            ),
                            None,
                        )
                        if removed_dev:
                            for callback in self.on_device_removed:
                                try:
                                    callback(removed_dev)
                                except Exception as e:
                                    print(f"Error in device removed callback: {e}")

                            # Handle reconnection if current device was removed
                            if (
                                self.current_device
                                and self._get_device_signature(self.current_device)
                                == sig
                            ):
                                self._handle_device_disconnection()

            except Exception as e:
                print(f"Error monitoring devices: {e}")
                for callback in self.on_device_error:
                    try:
                        callback(str(e))
                    except Exception as cb_err:
                        print(f"Error in device error callback: {cb_err}")

            time.sleep(1)  # Check every second

    def _handle_device_disconnection(self) -> None:
        """Handle device disconnection"""
        print("Audio device disconnected")

        with self._lock:
            # Stop current stream
            if self.stream:
                self.stop()

            if self.auto_reconnect:
                print("Attempting to reconnect...")
                threading.Thread(target=self._attempt_reconnection).start()

    def _attempt_reconnection(self) -> None:
        """Attempt to reconnect to a device"""
        while self.auto_reconnect:
            try:
                # Try preferred device first
                if self._preferred_device_index is not None:
                    try:
                        self.start(
                            device_index=self._preferred_device_index,
                            callback=self.callback,
                            sample_rate=self.current_sample_rate,
                        )
                        print("Reconnected to preferred device")
                        return
                    except Exception:
                        pass

                # Try any available device
                default_dev = self.get_default_device()
                if default_dev:
                    self.start(
                        device_index=default_dev["index"],
                        callback=self.callback,
                        sample_rate=self.current_sample_rate,
                    )
                    print("Reconnected to default device")
                    return

            except Exception as e:
                print(f"Reconnection attempt failed: {e}")

            time.sleep(self.reconnect_delay)

    def start_monitoring(self) -> None:
        """Start monitoring for device changes"""
        if self._monitor_thread is not None:
            return

        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=self._monitor_devices)
        self._monitor_thread.daemon = True
        self._monitor_thread.start()

    def stop_monitoring(self) -> None:
        """Stop monitoring for device changes"""
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
            self._monitor_thread = None

    def list_devices(self) -> Dict[int, Dict[str, Any]]:
        """List available audio input devices"""
        devices = {}
        for i in range(self.pa.get_device_count()):
            dev_info = self.pa.get_device_info_by_index(i)
            if dev_info["maxInputChannels"] > 0:  # Only input devices
                devices[i] = {
                    "index": i,
                    "name": dev_info["name"],
                    "channels": dev_info["maxInputChannels"],
                    "default_sample_rate": int(dev_info["defaultSampleRate"]),
                    "is_default": i == self.pa.get_default_input_device_info()["index"],
                }
        return devices

    def get_default_device(self) -> Optional[Dict[str, Any]]:
        """Get default input device, preferring USB audio interfaces"""
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

    def get_supported_sample_rates(self, device_index: int) -> List[int]:
        """Get supported sample rates for device"""
        supported_rates = []
        for rate in self.SUPPORTED_RATES:
            try:
                supported = self.pa.is_format_supported(
                    rate,
                    input_device=device_index,
                    input_channels=1,
                    input_format=pyaudio.paFloat32,
                )
                if supported:
                    supported_rates.append(rate)
            except ValueError:
                continue
        return supported_rates

    def _audio_callback(self, in_data, frame_count, time_info, status) -> tuple:
        """PyAudio callback for processing incoming audio data"""
        if status:
            print(f"PyAudio status: {status}")

        try:
            # Convert to numpy array
            audio_data = np.frombuffer(in_data, dtype=np.float32)

            # Process audio in user callback
            if self.callback:
                self.callback(audio_data)

        except Exception as e:
            print(f"Error in audio callback: {e}")

        return (in_data, pyaudio.paContinue)

    def start(
        self,
        device_index: Optional[int] = None,
        callback: Optional[Callable] = None,
        sample_rate: int = 44100,
        buffer_size: int = 2048,
    ) -> None:
        """Start audio capture"""
        with self._lock:
            if self.stream is not None:
                self.stop()

            # Store settings for reconnection
            self._preferred_device_index = device_index
            self.callback = callback

            # Use specified device or find default
            if device_index is None:
                default_dev = self.get_default_device()
                if default_dev:
                    device_index = default_dev["index"]
                else:
                    raise RuntimeError("No input device available")

            # Get device info
            device_info = self.pa.get_device_info_by_index(device_index)

            # Verify sample rate support
            supported_rates = self.get_supported_sample_rates(device_index)
            if not supported_rates:
                raise RuntimeError(
                    f"No supported sample rates found for device {device_index}"
                )

            if sample_rate not in supported_rates:
                print(f"Warning: Requested sample rate {sample_rate} not supported")
                sample_rate = supported_rates[0]
                print(f"Using {sample_rate}Hz instead")

            self.current_sample_rate = sample_rate

            try:
                print(f"Starting audio capture on: {device_info['name']}")
                print(f"Sample rate: {sample_rate}Hz")
                print(f"Buffer size: {buffer_size} frames")

                self.stream = self.pa.open(
                    format=pyaudio.paFloat32,
                    channels=1,
                    rate=sample_rate,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=buffer_size,
                    stream_callback=self._audio_callback,
                )

                self.current_device = device_info
                self.stream.start_stream()
                print("Audio capture started successfully")

                # Start device monitoring if not already running
                self.start_monitoring()

            except Exception as e:
                print(f"Error starting audio capture: {e}")
                self.cleanup()
                raise

    def stop(self) -> None:
        """Stop audio capture"""
        with self._lock:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
                self.current_device = None

    def cleanup(self) -> None:
        """Clean up resources"""
        self.stop_monitoring()
        self.stop()
        if self.pa:
            self.pa.terminate()

    def __del__(self):
        """Ensure cleanup on deletion"""
        self.cleanup()
