#!/usr/bin/env python3

import time
from rpi_ws281x import PixelStrip, Color

# LED strip configuration:
LED_COUNT = 143  # Number of LED pixels
LED_PIN = 18  # GPIO pin connected to the pixels (18 uses PWM!)
LED_FREQ_HZ = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA = 10  # DMA channel to use for generating signal
LED_BRIGHTNESS = 10  # Set to 0 for darkest and 255 for brightest
LED_CHANNEL = 0  # PWM channel
LED_INVERT = False  # True to invert the signal (when using NPN transistor level shift)


def colorWipe(strip, color, wait_ms=50):
    """Wipe color across display a pixel at a time."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
        strip.show()
        time.sleep(wait_ms / 1000.0)


def theaterChase(strip, color, wait_ms=50, iterations=10):
    """Movie theater light style chaser animation."""
    for j in range(iterations):
        for q in range(3):
            for i in range(0, strip.numPixels(), 3):
                if i + q < strip.numPixels():
                    strip.setPixelColor(i + q, color)
            strip.show()
            time.sleep(wait_ms / 1000.0)
            for i in range(0, strip.numPixels(), 3):
                if i + q < strip.numPixels():
                    strip.setPixelColor(i + q, 0)


def main():
    # Create NeoPixel object with appropriate configuration.
    strip = PixelStrip(
        LED_COUNT,
        LED_PIN,
        LED_FREQ_HZ,
        LED_DMA,
        LED_INVERT,
        LED_BRIGHTNESS,
        LED_CHANNEL,
    )
    # Initialize the library (must be called once before other functions).
    strip.begin()

    print("Press Ctrl-C to quit.")
    try:
        while True:
            print("Color wipe animations.")
            colorWipe(strip, Color(255, 0, 0))  # Red wipe
            colorWipe(strip, Color(0, 255, 0))  # Green wipe
            colorWipe(strip, Color(0, 0, 255))  # Blue wipe
            print("Theater chase animations.")
            theaterChase(strip, Color(127, 127, 127))  # White theater chase
            theaterChase(strip, Color(127, 0, 0))  # Red theater chase
            theaterChase(strip, Color(0, 0, 127))  # Blue theater chase

    except KeyboardInterrupt:
        print("Clearing strip...")
        colorWipe(strip, Color(0, 0, 0), 10)


if __name__ == "__main__":
    main()
