from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
from dataclasses import dataclass, field
import threading
import time
import logging
from rpi_ws281x import PixelStrip, Color

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
            from rpi_ws281x import PixelStrip, Color
        except ImportError as e:
            logger.error(f"Failed to import LED libraries: {e}")
            raise

        # State management first
        self._state = LEDState(
            pixels=np.zeros((num_pixels, 3), dtype=np.uint8), brightness=1.0, is_on=True
        )
        self._lock = threading.Lock()

        # LED strip configuration
        LED_COUNT = num_pixels  # Number of LED pixels
        LED_PIN = pin  # GPIO pin
        LED_FREQ_HZ = freq  # LED signal frequency in Hz
        LED_DMA = 10  # DMA channel for generating signal
        LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
        LED_INVERT = False  # True to invert the signal
        LED_CHANNEL = 0  # PWM channel

        # Initialize LED strip
        try:
            self.pixels = PixelStrip(
                LED_COUNT,
                LED_PIN,
                LED_FREQ_HZ,
                LED_DMA,
                LED_INVERT,
                LED_BRIGHTNESS,
                LED_CHANNEL,
            )
            self.pixels.begin()
            # Initialize with all pixels off
            for i in range(num_pixels):
                self.pixels.setPixelColor(i, Color(0, 0, 0))
            self.pixels.show()
        except Exception as e:
            logger.error(f"Failed to initialize LED strip: {e}")
            raise

        logger.info(f"Initialized LED strip with {num_pixels} pixels on pin {pin}")

    def set_pixels(self, pixels: np.ndarray) -> None:
        """Set pixel colors with error recovery"""
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

                # Update hardware with retry
                max_retries = 3
                last_error = None

                for attempt in range(max_retries):
                    try:
                        for i in range(len(pixels)):
                            r, g, b = pixels[i]
                            self.pixels.setPixelColor(i, Color(r, g, b))
                        self.pixels.show()

                        # Success - update state and clear errors
                        self._state.pixels = pixels
                        self._state.last_update = time.time()
                        self._state.clear_errors()
                        return

                    except Exception as e:
                        last_error = e
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} after error: {e}"
                        )
                        time.sleep(0.1)

                # If we get here, all retries failed
                raise last_error or Exception("Failed to update LED strip")

            except Exception as e:
                logger.error(f"Error setting pixels: {e}")
                if self._state.record_error():
                    logger.critical("Too many errors, turning off LED strip")
                    self.turn_off()
                    # Notify any error handlers
                    self._handle_critical_error(str(e))

    def _handle_critical_error(self, error_msg: str) -> None:
        """Handle critical errors that require immediate attention"""
        try:
            # Log to system log
            logger.critical(f"Critical LED controller error: {error_msg}")

            # Turn off LEDs for safety
            self.turn_off()

            # Reset state
            self._state.is_on = False
            self._state.pattern_active = False

            # Could add additional error handling here:
            # - Send error notification
            # - Trigger system restart
            # - etc.

        except Exception as e:
            logger.error(f"Error during critical error handling: {e}")

    def set_brightness(self, brightness: float) -> None:
        """Set global brightness with thread safety"""
        with self._lock:
            try:
                brightness = np.clip(brightness, 0, 1)
                self._state.brightness = brightness
                # Convert 0-1 to 0-255
                self.pixels.setBrightness(int(brightness * 255))
                self.pixels.show()
                logger.debug(f"Set brightness to {brightness}")
            except Exception as e:
                logger.error(f"Error setting brightness: {e}")

    def turn_on(self) -> None:
        """Turn on LED strip with thread safety"""
        with self._lock:
            try:
                self._state.is_on = True
                self.pixels.setBrightness(int(self._state.brightness * 255))
                self.set_pixels(self._state.pixels)
                logger.info("LED strip turned on")
            except Exception as e:
                logger.error(f"Error turning on: {e}")

    def turn_off(self) -> None:
        """Turn off LED strip with safety checks"""
        with self._lock:
            try:
                self._state.is_on = False
                # Try multiple times to ensure LEDs are off
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        # Set all pixels to black
                        for i in range(len(self._state.pixels)):
                            self.pixels.setPixelColor(i, Color(0, 0, 0))
                        self.pixels.setBrightness(0)
                        self.pixels.show()
                        logger.info("LED strip turned off successfully")
                        return
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} turning off LEDs: {e}"
                        )
                        time.sleep(0.1)
            except Exception as e:
                logger.error(f"Failed to turn off LED strip: {e}")
                # In case of critical failure, try hardware reset if available
                self._emergency_shutdown()

    def _emergency_shutdown(self) -> None:
        """Emergency hardware shutdown in case of critical failure"""
        try:
            # Could add hardware-specific shutdown here:
            # - Reset GPIO pins
            # - Power cycle LED strip
            # - etc.
            logger.critical("Emergency shutdown initiated")
        except Exception as e:
            logger.critical(f"Emergency shutdown failed: {e}")

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
