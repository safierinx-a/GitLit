import numpy as np
import logging
from rpi_ws281x import PixelStrip, Color, ws

logger = logging.getLogger(__name__)


class LEDController:
    """Simple LED controller that just displays frames"""

    def __init__(self, num_pixels: int, pin: int = 18, freq: int = 800000):
        # LED strip configuration
        LED_COUNT = num_pixels
        LED_PIN = pin
        LED_FREQ_HZ = freq
        LED_DMA = 10
        LED_BRIGHTNESS = 255
        LED_INVERT = False
        LED_CHANNEL = 0
        LED_STRIP = ws.WS2811_STRIP_GRB

        # Initialize the library
        self.strip = PixelStrip(
            LED_COUNT,
            LED_PIN,
            LED_FREQ_HZ,
            LED_DMA,
            LED_INVERT,
            LED_BRIGHTNESS,
            LED_CHANNEL,
            LED_STRIP,
        )
        self.strip.begin()
        logger.info(f"Initialized LED strip with {num_pixels} pixels")

    def display_frame(self, frame: np.ndarray) -> None:
        """Display a single frame on the LED strip"""
        try:
            # Input validation
            if not isinstance(frame, np.ndarray):
                frame = np.array(frame)

            # Ensure correct shape and type
            frame = np.clip(frame, 0, 255).astype(np.uint8)

            # Update pixels
            for i in range(len(frame)):
                r, g, b = frame[i]
                self.strip.setPixelColor(i, Color(g, r, b))  # Note: GRB order

            self.strip.show()

        except Exception as e:
            logger.error(f"Error displaying frame: {e}")

    def clear(self) -> None:
        """Turn off all LEDs"""
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, Color(0, 0, 0))
        self.strip.show()
        logger.debug("Cleared all LEDs")

    def cleanup(self) -> None:
        """Clean up resources"""
        self.clear()
        logger.info("LED controller cleaned up")
