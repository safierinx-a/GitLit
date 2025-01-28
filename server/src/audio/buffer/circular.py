import numpy as np
from threading import Lock
from typing import Optional, Tuple


class CircularAudioBuffer:
    """Thread-safe circular buffer for audio processing"""

    def __init__(self, capacity: int, channels: int = 1):
        self.capacity = capacity
        self.channels = channels
        self._buffer = np.zeros((channels, capacity), dtype=np.float32)
        self._write_pos = 0
        self._samples_written = 0
        self._lock = Lock()

    def write(self, data: np.ndarray) -> None:
        """Write audio data to buffer"""
        if data.ndim == 1:
            data = data.reshape(1, -1)

        with self._lock:
            samples_to_write = data.shape[1]

            # Handle wrap-around
            first_write = min(samples_to_write, self.capacity - self._write_pos)
            self._buffer[:, self._write_pos : self._write_pos + first_write] = data[
                :, :first_write
            ]

            if first_write < samples_to_write:
                # Wrap around and write remaining samples
                remaining = samples_to_write - first_write
                self._buffer[:, :remaining] = data[:, first_write:]

            self._write_pos = (self._write_pos + samples_to_write) % self.capacity
            self._samples_written += samples_to_write

    def read(self, samples: int, overlap: int = 0) -> Tuple[np.ndarray, bool]:
        """Read audio data from buffer with optional overlap"""
        with self._lock:
            if samples > self.capacity:
                raise ValueError("Requested samples exceeds buffer capacity")

            if self._samples_written < samples:
                return np.zeros((self.channels, samples)), False

            # Calculate read position
            read_pos = (self._write_pos - samples) % self.capacity

            # Handle wrap-around read
            if read_pos + samples <= self.capacity:
                data = self._buffer[:, read_pos : read_pos + samples].copy()
            else:
                first_read = self.capacity - read_pos
                data = np.concatenate(
                    [
                        self._buffer[:, read_pos:],
                        self._buffer[:, : samples - first_read],
                    ],
                    axis=1,
                )

            return data, True

    def get_latest(self, samples: int) -> Optional[np.ndarray]:
        """Get the most recent samples"""
        with self._lock:
            if self._samples_written < samples:
                return None

            if self._write_pos >= samples:
                return self._buffer[
                    :, self._write_pos - samples : self._write_pos
                ].copy()
            else:
                # Handle wrap-around
                first_part = self._buffer[:, -samples + self._write_pos :].copy()
                second_part = self._buffer[:, : self._write_pos].copy()
                return np.concatenate([first_part, second_part], axis=1)

    def clear(self) -> None:
        """Clear the buffer"""
        with self._lock:
            self._buffer.fill(0)
            self._write_pos = 0
            self._samples_written = 0

    @property
    def available_samples(self) -> int:
        """Get number of samples available"""
        return min(self._samples_written, self.capacity)
