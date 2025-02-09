import numpy as np
from typing import Dict, Any
import logging
import time
from dataclasses import dataclass, field

from .controller import LEDController, LEDState

logger = logging.getLogger(__name__)


class MockLEDController(LEDController):
    """Mock LED controller for development without hardware"""

    def __init__(self, num_pixels: int):
        self._state = LEDState(
            pixels=np.zeros((num_pixels, 3), dtype=np.uint8),
            brightness=1.0,
            is_on=True,
            pattern_active=False,
        )
        logger.info(f"Initialized mock LED controller with {num_pixels} pixels")

    def set_pixels(self, pixels: np.ndarray) -> None:
        """Set pixel colors (RGB values 0-255)"""
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

            # Apply brightness and store
            self._state.pixels = (pixels * self._state.brightness).astype(np.uint8)
            self._state.last_update = time.time()
            self._state.clear_errors()

            logger.debug(f"Updated pixels with brightness {self._state.brightness}")

        except Exception as e:
            logger.error(f"Error setting pixels: {e}")
            if self._state.record_error():
                logger.critical("Too many errors, turning off mock LED strip")
                self.turn_off()

    def set_brightness(self, brightness: float) -> None:
        """Set global brightness (0-1)"""
        try:
            self._state.brightness = np.clip(brightness, 0, 1)
            # Re-apply current pixels with new brightness
            self.set_pixels(self._state.pixels)
            logger.debug(f"Set brightness to {self._state.brightness}")
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")

    def turn_on(self) -> None:
        """Turn on LED strip"""
        try:
            self._state.is_on = True
            self.set_pixels(self._state.pixels)
            logger.info("Mock LED strip turned on")
        except Exception as e:
            logger.error(f"Error turning on: {e}")

    def turn_off(self) -> None:
        """Turn off LED strip"""
        try:
            self._state.is_on = False
            self._state.pixels.fill(0)
            logger.info("Mock LED strip turned off")
        except Exception as e:
            logger.error(f"Error turning off: {e}")

    def cleanup(self) -> None:
        """Clean up resources"""
        try:
            self.turn_off()
            logger.info("Mock LED strip cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_state(self) -> Dict[str, Any]:
        """Get current controller state"""
        return {
            "is_on": self._state.is_on,
            "brightness": self._state.brightness,
            "pixel_count": len(self._state.pixels),
            "last_update": self._state.last_update,
            "error_count": self._state.error_count,
            "is_mock": True,
        }
