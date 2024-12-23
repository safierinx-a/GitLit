#!/usr/bin/env python3

import os
import sys
import time

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.led.controller import LEDController, LEDConfig
import yaml

# Import all patterns
from src.patterns import (
    # Static Patterns
    SolidPattern,
    GradientPattern,
    # Moving Patterns
    WavePattern,
    RainbowPattern,
    ChasePattern,
    ScanPattern,
    # Particle Patterns
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


def test_static_patterns(controller):
    """Test static patterns with all parameters"""
    print("\nTesting Static Patterns...")

    # Test Solid Pattern
    print("\nTesting SolidPattern")
    pattern = SolidPattern(controller.config.led_count)
    params = {"red": 255, "green": 0, "blue": 0}
    run_pattern(controller, pattern, params, duration=3)

    # Test Gradient Pattern
    print("\nTesting GradientPattern")
    pattern = GradientPattern(controller.config.led_count)
    params = {
        "start_red": 255,
        "start_green": 0,
        "start_blue": 0,
        "end_red": 0,
        "end_green": 0,
        "end_blue": 255,
        "position": 0.5,
    }
    run_pattern(controller, pattern, params, duration=3)


def test_moving_patterns(controller):
    """Test moving patterns with all parameters"""
    print("\nTesting Moving Patterns...")

    # Test Wave Pattern
    print("\nTesting WavePattern")
    pattern = WavePattern(controller.config.led_count)
    params = {
        "speed": 1.0,
        "wavelength": 1.0,
        "amplitude": 1.0,  # New parameter
        "red": 255,
        "green": 0,
        "blue": 0,
    }
    run_pattern(controller, pattern, params, duration=5)

    # Add other moving pattern tests...


def test_particle_patterns(controller):
    """Test particle patterns with all parameters"""
    print("\nTesting Particle Patterns...")

    # Test Twinkle Pattern
    print("\nTesting TwinklePattern")
    pattern = TwinklePattern(controller.config.led_count)
    params = {
        "density": 0.2,
        "fade_speed": 1.0,
        "random_color": True,
        "red": 255,
        "green": 255,
        "blue": 255,
    }
    run_pattern(controller, pattern, params, duration=5)

    # Add other particle pattern tests...


def run_pattern(controller, pattern, params, duration=5):
    """Run a single pattern with given parameters"""
    try:
        start_time = time.time() * 1000
        end_time = start_time + (duration * 1000)

        while time.time() * 1000 < end_time:
            current_time = time.time() * 1000 - start_time
            frame = pattern.generate(current_time, params)

            for i, color in enumerate(frame):
                controller.set_pixel(i, color[0], color[1], color[2])
            controller.show()

            time.sleep(1 / 60)

    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"Error testing {pattern.__class__.__name__}: {e}")


def main():
    config = load_config()
    controller = LEDController(config)

    try:
        test_static_patterns(controller)
        test_moving_patterns(controller)
        test_particle_patterns(controller)

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    main()
