#!/usr/bin/env python3

import os
import sys
import time

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.led.controller import LEDController, LEDConfig
import yaml
from src.patterns import (
    WavePattern,
    RainbowPattern,
    ChasePattern,
    ScanPattern,
    TwinklePattern,
    MeteorPattern,
    BreathePattern,
)


def load_config():
    config_path = os.path.join(project_root, "config/led_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return LEDConfig(
        led_count=config["led_strip"]["count"],
        brightness=config["led_strip"]["startup_brightness"],
    )


def test_patterns():
    """Test each pattern on the actual LED strip"""
    config = load_config()
    controller = LEDController(config)

    patterns = [
        (
            WavePattern(config.led_count),
            {"speed": 1.0, "wavelength": 1.0, "red": 255, "green": 0, "blue": 0},
        ),
        (RainbowPattern(config.led_count), {"speed": 1.0, "scale": 1.0}),
        (
            ChasePattern(config.led_count),
            {"speed": 1.0, "count": 3, "size": 2, "red": 0, "green": 255, "blue": 0},
        ),
        (
            ScanPattern(config.led_count),
            {"speed": 1.0, "width": 3, "red": 0, "green": 0, "blue": 255},
        ),
        (
            TwinklePattern(config.led_count),
            {"density": 0.1, "fade_speed": 1.0, "red": 255, "green": 255, "blue": 255},
        ),
        (
            MeteorPattern(config.led_count),
            {
                "speed": 1.0,
                "size": 3,
                "trail_length": 0.5,
                "red": 255,
                "green": 165,
                "blue": 0,
            },
        ),
        (
            BreathePattern(config.led_count),
            {
                "speed": 1.0,
                "min_brightness": 0.0,
                "max_brightness": 1.0,
                "red": 255,
                "green": 0,
                "blue": 255,
            },
        ),
    ]

    try:
        print("Testing patterns. Press Ctrl+C to stop.")

        while True:
            for pattern, params in patterns:
                print(f"\nTesting {pattern.__class__.__name__}...")
                start_time = time.time() * 1000

                # Run pattern for 5 seconds
                for _ in range(300):  # 5 seconds at ~60fps
                    current_time = time.time() * 1000 - start_time
                    frame = pattern.generate(current_time, params)

                    # Update LEDs
                    for i, color in enumerate(frame):
                        controller.set_pixel(i, color[0], color[1], color[2])
                    controller.show()

                    time.sleep(1 / 60)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    print("Running pattern tests...")
    test_patterns()
    print("\nTests completed!")
