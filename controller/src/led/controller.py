from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from dataclasses import dataclass, field
import threading
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class LEDState:
    """Current state of LED strip"""

    pixels: np.ndarray  # RGB values (N, 3)
    brightness: float = 1.0
    is_on: bool = True
    pattern_active: bool = False
    last_update: float = field(default_factory=time.time)
    error_count: int = 0
    max_errors: int = 10

    def record_error(self) -> bool:
        """Record an error and return True if max errors exceeded"""
        self.error_count += 1
        return self.error_count >= self.max_errors

    def clear_errors(self):
        """Reset error count"""
        self.error_count = 0


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

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        """Get current controller state"""
        pass


class DirectLEDController(LEDController):
    """Direct LED control for Raspberry Pi"""

    def __init__(self, num_pixels: int, pin: int = 18, freq: int = 800000):
        try:
            import board
            import neopixel
        except ImportError as e:
            logger.error(f"Failed to import LED libraries: {e}")
            raise

        # State management first
        self._state = LEDState(
            pixels=np.zeros((num_pixels, 3), dtype=np.uint8), brightness=1.0, is_on=True
        )
        self._lock = threading.Lock()

        # Initialize LED strip
        try:
            self.pixels = neopixel.NeoPixel(
                pin=getattr(board, f"D{pin}"),
                n=num_pixels,
                auto_write=False,
                pixel_order=neopixel.RGB,
            )
            # Initialize with all pixels off
            self.pixels.fill((0, 0, 0))
            self.pixels.show()
        except Exception as e:
            logger.error(f"Failed to initialize LED strip: {e}")
            raise

        logger.info(f"Initialized LED strip with {num_pixels} pixels on pin {pin}")

    def set_pixels(self, pixels: np.ndarray) -> None:
        """Set pixel colors with thread safety and error handling"""
        with self._lock:
            if not self._state.is_on:
                return

            try:
                # Input validation
                if not isinstance(pixels, np.ndarray):
                    pixels = np.array(pixels)

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
                self._state.last_update = time.time()
                self._state.clear_errors()

            except Exception as e:
                logger.error(f"Error setting pixels: {e}")
                if self._state.record_error():
                    logger.critical("Too many errors, turning off LED strip")
                    self.turn_off()

    def set_brightness(self, brightness: float) -> None:
        """Set global brightness with thread safety"""
        with self._lock:
            try:
                brightness = np.clip(brightness, 0, 1)
                self._state.brightness = brightness
                self.set_pixels(self._state.pixels)
                logger.debug(f"Set brightness to {brightness}")
            except Exception as e:
                logger.error(f"Error setting brightness: {e}")

    def turn_on(self) -> None:
        """Turn on LED strip with thread safety"""
        with self._lock:
            try:
                self._state.is_on = True
                self.set_pixels(self._state.pixels)
                logger.info("LED strip turned on")
            except Exception as e:
                logger.error(f"Error turning on: {e}")

    def turn_off(self) -> None:
        """Turn off LED strip with thread safety"""
        with self._lock:
            try:
                self._state.is_on = False
                self.pixels.fill((0, 0, 0))
                self.pixels.show()
                logger.info("LED strip turned off")
            except Exception as e:
                logger.error(f"Error turning off: {e}")

    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            self.turn_off()
            logger.info("LED strip cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get current controller state"""
        with self._lock:
            return {
                "is_on": self._state.is_on,
                "brightness": self._state.brightness,
                "pixel_count": len(self._state.pixels),
                "last_update": self._state.last_update,
                "error_count": self._state.error_count,
            }


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

    def get_state(self) -> Dict[str, Any]:
        """Get current controller state"""
        return {
            "is_on": self._state.is_on,
            "brightness": self._state.brightness,
            "pixel_count": len(self._state.pixels),
            "last_update": self._state.last_update,
            "error_count": self._state.error_count,
        }


def create_controller(config: Dict[str, Any]) -> LEDController:
    """Factory function to create appropriate LED controller"""
    controller_type = config.get("type", "direct")
    num_pixels = config["num_pixels"]

    if controller_type == "direct":
        # Check if we're on a Raspberry Pi
        try:
            with open("/proc/cpuinfo", "r") as f:
                is_raspberry_pi = any(
                    "Raspberry Pi" in line for line in f if line.startswith("Model")
                )
        except:
            is_raspberry_pi = False

        if is_raspberry_pi:
            return DirectLEDController(
                num_pixels=num_pixels,
                pin=config.get("pin", 18),
                freq=config.get("freq", 800000),
            )
        else:
            from .mock import MockLEDController

            logger.info("Not running on Raspberry Pi, using mock LED controller")
            return MockLEDController(num_pixels=num_pixels)

    elif controller_type == "remote":
        return RemoteLEDController(host=config["host"], port=config.get("port", 8888))
    elif controller_type == "mock":
        from .mock import MockLEDController

        return MockLEDController(num_pixels=num_pixels)
    else:
        raise ValueError(f"Unknown controller type: {controller_type}")
