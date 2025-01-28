import os
import sys
from time import sleep

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.led.controller import LEDController, LEDConfig
import yaml


def load_config():
    """Load LED configuration from yaml file"""
    config_path = os.path.join(project_root, "config/led_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return LEDConfig(
        led_count=config["led_strip"]["count"],
        brightness=config["led_strip"]["startup_brightness"],
    )


def turn_off_leds():
    """Turn off all LEDs"""
    print("Turning off all LEDs...")
    config = load_config()
    controller = LEDController(config)

    try:
        # First set all pixels to zero explicitly
        for i in range(config.led_count):
            controller.set_pixel(i, 0, 0, 0)
        controller.show()

        # Small delay to ensure data is sent
        sleep(0.001)

        # Then clear the strip
        controller.clear()
        controller.show()

        # Another small delay
        sleep(0.001)

        # Final clear with zero brightness
        controller.set_brightness(0)
        controller.clear()
        controller.show()

        print("LEDs turned off successfully")
    finally:
        controller.cleanup()


if __name__ == "__main__":
    turn_off_leds()
