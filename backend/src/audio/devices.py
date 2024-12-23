import pyaudio
import threading
import time
from typing import Dict, Optional, Callable, Set


class DeviceMonitor:
    """Monitor audio devices for changes"""

    def __init__(self):
        self.pa = pyaudio.PyAudio()
        self.known_devices: Set[str] = set()  # Track devices by name
        self.callbacks: list[Callable] = []
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None

    def get_device_signature(self, info: dict) -> str:
        """Create unique device signature"""
        return f"{info['name']}_{info['index']}"

    def scan_devices(self) -> Dict[int, Dict]:
        """Scan for input devices"""
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

    def register_callback(self, callback: Callable[[str, Dict], None]):
        """Register callback for device changes
        callback(event, device_info) where event is 'added' or 'removed'"""
        self.callbacks.append(callback)

    def _notify_callbacks(self, event: str, device_info: Dict):
        """Notify all callbacks of device changes"""
        for callback in self.callbacks:
            try:
                callback(event, device_info)
            except Exception as e:
                print(f"Callback error: {e}")

    def start_monitoring(self):
        """Start monitoring for device changes"""
        if self.monitor_thread is not None:
            return

        self.running = True

        # Initialize known devices
        current_devices = self.scan_devices()
        self.known_devices = {
            self.get_device_signature(dev): dev for dev in current_devices.values()
        }

        def monitor_loop():
            while self.running:
                try:
                    # Scan for current devices
                    current_devices = self.scan_devices()
                    current_sigs = {
                        self.get_device_signature(dev): dev
                        for dev in current_devices.values()
                    }

                    # Check for new devices
                    for sig, dev in current_sigs.items():
                        if sig not in self.known_devices:
                            self._notify_callbacks("added", dev)

                    # Check for removed devices
                    for sig, dev in self.known_devices.items():
                        if sig not in current_sigs:
                            self._notify_callbacks("removed", dev)

                    # Update known devices
                    self.known_devices = current_sigs

                except Exception as e:
                    print(f"Monitor error: {e}")

                time.sleep(1)  # Check every second

        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring for device changes"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            self.monitor_thread = None

    def cleanup(self):
        """Clean up resources"""
        self.stop_monitoring()
        self.pa.terminate()
