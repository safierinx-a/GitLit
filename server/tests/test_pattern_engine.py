import os
import sys
from time import sleep
import yaml

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.led.controller import LEDController, LEDConfig
from src.patterns.engine import PatternEngine
from src.core.config import PatternConfig


def load_config():
    """Load LED configuration from yaml file"""
    config_path = os.path.join(project_root, "config/led_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return LEDConfig(
        led_count=config["led_strip"]["count"],
        brightness=config["led_strip"]["startup_brightness"],
    )


def test_basic_patterns():
    """Test basic pattern functionality"""
    config = load_config()
    led_controller = LEDController(config)
    pattern_engine = PatternEngine(led_controller)

    try:
        patterns_to_test = [
            # Simple static pattern
            ("solid", {"red": 255, "green": 0, "blue": 0}, 2),
            # Moving pattern
            ("rainbow", {"speed": 1.0, "scale": 1.0, "saturation": 1.0}, 3),
            # Particle pattern
            (
                "twinkle",
                {
                    "density": 0.3,
                    "fade_speed": 1.0,
                    "red": 255,
                    "green": 255,
                    "blue": 255,
                    "random_color": True,
                },
                3,
            ),
        ]

        for pattern_name, params, duration in patterns_to_test:
            print(f"\nTesting {pattern_name} pattern...")
            pattern_engine.set_pattern(
                PatternConfig(name=pattern_name, parameters=params)
            )

            # Run pattern for specified duration
            frames = duration * 30  # 30 fps
            for frame in range(frames):
                pattern_engine.update(frame * 33.3)  # ~30fps
                sleep(0.033)

    finally:
        led_controller.cleanup()


if __name__ == "__main__":
    print("Running pattern engine tests...")
    test_basic_patterns()
    print("Tests completed!")
