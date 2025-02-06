#!/usr/bin/env python3

import os
import sys
import time

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

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
    return config["led_strip"]["count"]


def test_patterns():
    """Test each pattern on the actual LED strip"""
    led_count = load_config()

    patterns = [
        (
            WavePattern(led_count),
            {"speed": 1.0, "wavelength": 1.0, "red": 255, "green": 0, "blue": 0},
        ),
        (RainbowPattern(led_count), {"speed": 1.0, "scale": 1.0}),
        (
            ChasePattern(led_count),
            {"speed": 1.0, "count": 3, "size": 2, "red": 0, "green": 255, "blue": 0},
        ),
        (
            ScanPattern(led_count),
            {"speed": 1.0, "width": 3, "red": 0, "green": 0, "blue": 255},
        ),
        (
            TwinklePattern(led_count),
            {"density": 0.1, "fade_speed": 1.0, "red": 255, "green": 255, "blue": 255},
        ),
        (
            MeteorPattern(led_count),
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
            BreathePattern(led_count),
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
        for pattern, params in patterns:
            print(f"\nTesting {pattern.__class__.__name__}...")
            for frame in range(60):  # Run each pattern for 60 frames
                frame = pattern.generate(frame * 33.3, params)  # ~30fps
                print(f"Frame {frame}: {frame[:5]}")  # Show first 5 pixels
                time.sleep(0.033)

    except KeyboardInterrupt:
        print("\nStopping...")


if __name__ == "__main__":
    print("Running pattern tests...")
    test_patterns()
    print("\nTests completed!")
