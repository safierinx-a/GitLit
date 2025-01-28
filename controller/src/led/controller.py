from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import numpy as np
from dataclasses import dataclass
import threading
import time


@dataclass
class LEDState:
    """Current state of LED strip"""

    pixels: np.ndarray  # RGB values (N, 3)
    brightness: float = 1.0
    is_on: bool = True
    pattern_active: bool = False


class LEDController(ABC):
    """Abstract LED controller interface"""

    @abstractmethod
    def set_pixels(self, pixels: np.ndarray) -> None:
        """Set pixel colors (RGB values 0-255)"""
        pass

    @abstractmethod
    def set_brightness(self, brightness: float) -> None:
        """Set global brightness (0-1)"""
        pass

    @abstractmethod
    def turn_on(self) -> None:
        """Turn on LED strip"""
        pass

    @abstractmethod
    def turn_off(self) -> None:
        """Turn off LED strip"""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources"""
        pass


class DirectLEDController(LEDController):
    """Direct LED control for Raspberry Pi"""

    def __init__(self, num_pixels: int, pin: int = 18, freq: int = 800000):
        import board
        import neopixel

        # Initialize LED strip
        self.pixels = neopixel.NeoPixel(
            pin=getattr(board, f"D{pin}"),
            n=num_pixels,
            auto_write=False,
            pixel_order=neopixel.RGB,
        )

        # State management
        self._state = LEDState(
            pixels=np.zeros((num_pixels, 3), dtype=np.uint8), brightness=1.0, is_on=True
        )
        self._lock = threading.Lock()

    def set_pixels(self, pixels: np.ndarray) -> None:
        """Set pixel colors with thread safety"""
        with self._lock:
            if not self._state.is_on:
                return

            # Ensure correct shape and type
            pixels = np.clip(pixels, 0, 255).astype(np.uint8)
            if pixels.shape != self._state.pixels.shape:
                raise ValueError(
                    f"Expected shape {self._state.pixels.shape}, got {pixels.shape}"
                )

            # Apply brightness
            pixels = (pixels * self._state.brightness).astype(np.uint8)

            # Update hardware
            self.pixels[:] = [tuple(p) for p in pixels]
            self.pixels.show()

            # Update state
            self._state.pixels = pixels

    def set_brightness(self, brightness: float) -> None:
        """Set global brightness with thread safety"""
        with self._lock:
            brightness = np.clip(brightness, 0, 1)
            self._state.brightness = brightness

            # Re-apply current pixels with new brightness
            self.set_pixels(self._state.pixels)

    def turn_on(self) -> None:
        """Turn on LED strip with thread safety"""
        with self._lock:
            self._state.is_on = True
            self.set_pixels(self._state.pixels)

    def turn_off(self) -> None:
        """Turn off LED strip with thread safety"""
        with self._lock:
            self._state.is_on = False
            self.pixels.fill((0, 0, 0))
            self.pixels.show()

    def cleanup(self) -> None:
        """Clean up resources"""
        self.turn_off()


class RemoteLEDController(LEDController):
    """Network-based LED control (placeholder for future ESP32 support)"""

    def __init__(self, host: str, port: int = 8888):
        self.host = host
        self.port = port
        self._state = LEDState(
            pixels=np.array([]),  # Will be set on connection
            brightness=1.0,
            is_on=True,
        )
        # Network setup would go here

    def set_pixels(self, pixels: np.ndarray) -> None:
        """Send pixel data over network (to be implemented)"""
        pass

    def set_brightness(self, brightness: float) -> None:
        """Send brightness command over network (to be implemented)"""
        pass

    def turn_on(self) -> None:
        """Send turn on command over network (to be implemented)"""
        pass

    def turn_off(self) -> None:
        """Send turn off command over network (to be implemented)"""
        pass

    def cleanup(self) -> None:
        """Clean up network resources (to be implemented)"""
        pass


def create_controller(config: Dict[str, Any]) -> LEDController:
    """Factory function to create appropriate LED controller"""
    controller_type = config.get("type", "direct")

    if controller_type == "direct":
        return DirectLEDController(
            num_pixels=config["num_pixels"],
            pin=config.get("pin", 18),
            freq=config.get("freq", 800000),
        )
    elif controller_type == "remote":
        return RemoteLEDController(host=config["host"], port=config.get("port", 8888))
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")
