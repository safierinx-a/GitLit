from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from rpi_ws281x import PixelStrip, Color
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LEDConfig:
    """Configuration for LED strip"""

    led_count: int
    pin: int = 18  # PWM pin (18 uses PWM0)
    freq_hz: int = 800000
    dma: int = 10
    brightness: int = 255
    channel: int = 0
    invert: bool = False
    gamma: Optional[List[int]] = None


class LEDController:
    """Controls WS2812B LED strip with safety features and optimizations"""

    def __init__(self, config: LEDConfig):
        self.config = config
        try:
            self._strip = PixelStrip(
                num=config.led_count,
                pin=config.pin,
                freq_hz=config.freq_hz,
                dma=config.dma,
                invert=config.invert,
                brightness=config.brightness,
                channel=config.channel,
            )
            self._strip.begin()
            logger.info(f"LED strip initialized with {config.led_count} LEDs")

            # Force clear on initialization
            self._force_clear()

        except Exception as e:
            logger.error(f"Failed to initialize LED strip: {e}")
            raise

        self._gamma = self._setup_gamma(config.gamma)
        self._enabled = True

    def _force_clear(self) -> None:
        """Force clear all pixels with multiple attempts"""
        for attempt in range(3):  # Try up to 3 times
            try:
                # Set all pixels to black
                black = Color(0, 0, 0)
                for i in range(self.config.led_count):
                    self._strip.setPixelColor(i, black)
                self._strip.show()

                # Verify pixels are off
                all_clear = True
                for i in range(self.config.led_count):
                    if self._strip.getPixelColor(i) != 0:
                        all_clear = False
                        break

                if all_clear:
                    logger.info("All pixels cleared successfully")
                    return

                logger.warning(f"Clear attempt {attempt + 1} failed, retrying...")
                time.sleep(0.1)  # Small delay between attempts

            except Exception as e:
                logger.error(f"Clear attempt {attempt + 1} failed: {e}")

        logger.error("Failed to clear pixels after multiple attempts")

    def _setup_gamma(self, gamma: Optional[List[int]]) -> List[int]:
        """Setup gamma correction table"""
        if gamma is not None and len(gamma) == 256:
            return gamma
        return [int(pow(i / 255.0, 2.8) * 255) for i in range(256)]

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        """Set single pixel color with validation"""
        if not self._enabled or not (0 <= index < self.config.led_count):
            return

        # Validate color values
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))

        # Apply gamma correction
        r = self._gamma[r]
        g = self._gamma[g]
        b = self._gamma[b]

        try:
            color = Color(r, g, b)
            self._strip.setPixelColor(index, color)

            # Verify pixel color was set correctly
            set_color = self._strip.getPixelColor(index)
            if set_color != color:
                logger.warning(
                    f"Pixel {index} color mismatch: expected {color}, got {set_color}"
                )

        except Exception as e:
            logger.error(f"Failed to set pixel {index}: {e}")
            self.emergency_stop()

    def fill(self, r: int, g: int, b: int) -> None:
        """Fill entire strip with a color"""
        if not self._enabled:
            return

        # Apply gamma correction
        r = self._gamma[min(max(r, 0), 255)]
        g = self._gamma[min(max(g, 0), 255)]
        b = self._gamma[min(max(b, 0), 255)]

        # Pack RGB into 24-bit color
        color = Color(r, g, b)

        try:
            for i in range(self.config.led_count):
                self._strip.setPixelColor(i, color)
            self._strip.show()
        except Exception as e:
            logger.error(f"Failed to fill strip: {e}")
            self.emergency_stop()

    def clear(self) -> None:
        """Clear all pixels with verification"""
        if not self._enabled:
            return

        try:
            self._force_clear()
        except Exception as e:
            logger.error(f"Failed to clear strip: {e}")
            self.emergency_stop()

    def show(self) -> None:
        """Update the LED strip"""
        if not self._enabled:
            return

        try:
            self._strip.show()
        except Exception as e:
            logger.error(f"Failed to update strip: {e}")
            self.emergency_stop()

    def set_brightness(self, brightness: int) -> None:
        """Set strip brightness (0-255)"""
        if not self._enabled:
            return

        brightness = min(255, max(0, brightness))
        try:
            self._strip.setBrightness(brightness)
            self._strip.show()
        except Exception as e:
            logger.error(f"Failed to set brightness: {e}")
            self.emergency_stop()

    def emergency_stop(self) -> None:
        """Emergency stop - disable LEDs and stop updates"""
        logger.warning("Emergency stop triggered")
        self._enabled = False
        self.clear()

    def enable(self) -> None:
        """Re-enable LED updates after emergency stop"""
        self._enabled = True
        logger.info("LED controller enabled")

    def cleanup(self) -> None:
        """Clear strip and cleanup resources"""
        logger.info("Cleaning up LED controller...")
        self._force_clear()  # Make sure all pixels are off
        self._enabled = False
        logger.info("LED controller cleaned up")
