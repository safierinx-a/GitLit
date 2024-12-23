import os
import sys

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.led.controller import LEDController, LEDConfig
import yaml
from time import sleep


def load_config():
    config_path = os.path.join(project_root, "config/led_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return LEDConfig(
        led_count=config["led_strip"]["count"],
        brightness=config["led_strip"]["startup_brightness"],
    )


def test_basic_functionality():
    """Test basic LED strip functionality"""
    config = load_config()
    controller = LEDController(config)

    try:
        # Test 1: All red
        print("Setting all LEDs to red...")
        controller.fill(255, 0, 0)
        controller.show()
        sleep(1)

        # Test 2: All green
        print("Setting all LEDs to green...")
        controller.fill(0, 255, 0)
        controller.show()
        sleep(1)

        # Test 3: All blue
        print("Setting all LEDs to blue...")
        controller.fill(0, 0, 255)
        controller.show()
        sleep(1)

        # Test 4: Individual pixels
        print("Testing individual pixels...")
        controller.clear()
        for i in range(config.led_count):
            controller.set_pixel(i, 255, 255, 255)
            controller.show()
            sleep(0.05)

        # Test 5: Brightness control
        print("Testing brightness control...")
        controller.fill(255, 255, 255)
        for brightness in [255, 128, 64, 32, 16, 0]:
            controller.set_brightness(brightness)
            sleep(0.5)

    finally:
        controller.cleanup()


def test_safety_features():
    """Test safety features and error handling"""
    config = load_config()
    controller = LEDController(config)

    try:
        # Test emergency stop
        controller.fill(255, 255, 255)
        controller.show()
        sleep(1)

        print("Testing emergency stop...")
        controller.emergency_stop()
        sleep(1)

        # Try to set pixels while stopped
        controller.fill(255, 0, 0)
        controller.show()
        sleep(1)  # Should remain off

        # Re-enable and test
        print("Re-enabling...")
        controller.enable()
        controller.fill(0, 255, 0)
        controller.show()
        sleep(1)

    finally:
        controller.cleanup()


if __name__ == "__main__":
    print("Running LED controller tests...")
    test_basic_functionality()
    print("\nTesting safety features...")
    test_safety_features()
    print("\nTests completed!")
