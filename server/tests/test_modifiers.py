#!/usr/bin/env python3

import os
import sys
import time
import select

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

from src.patterns import (
    WavePattern,
    RainbowPattern,
    ChasePattern,
    ScanPattern,
    TwinklePattern,
    MeteorPattern,
    BreathePattern,
)
from src.patterns.modifiers import (
    BrightnessModifier,
    SpeedModifier,
    DirectionModifier,
    ColorTempModifier,
    SaturationModifier,
    MirrorModifier,
    SegmentModifier,
    StrobeModifier,
    FadeModifier,
    ColorCycleModifier,
)
import yaml


def load_config():
    config_path = os.path.join(project_root, "config/led_config.yaml")
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config["led_strip"]["count"]


class ModifierState:
    def __init__(self, modifier_class, param_name, values):
        self.modifier = modifier_class()
        self.param_name = param_name
        self.values = values
        self.current_index = 0
        self.enabled = False

    def cycle(self):
        """Cycle through values, enable if disabled"""
        if not self.enabled:
            self.enabled = True
        else:
            self.current_index = (self.current_index + 1) % len(self.values)
            if self.current_index == 0:  # Wrapped around, disable
                self.enabled = False

    def get_params(self):
        return {self.param_name: self.values[self.current_index]}


def main():
    led_count = load_config()

    # Pattern parameter controls
    pattern_controls = {
        "w": ("wavelength", [0.5, 1.0, 2.0]),  # Wave
        "e": ("count", [2, 3, 4, 5]),  # Chase
        "r": ("width", [1, 2, 3, 4, 5]),  # Scan width
        "f": ("fade", [0.1, 0.3, 0.5, 0.7]),  # Scan fade
        "n": ("density", [0.1, 0.3, 0.5]),  # Twinkle
        "x": ("bounce", [True, False]),  # Scan bounce
        "v": ("speed", [0.25, 0.5, 1.0, 2.0]),  # General speed
    }

    # Color controls for base pattern
    colors = {
        "r": ("red", [0, 128, 255]),
        "g": ("green", [0, 128, 255]),
        "b": ("blue", [0, 128, 255]),
    }

    # Color alternation controls (for ColorCycleModifier)
    alt_colors = {
        "h": (
            "color1",
            [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)],
        ),  # First sequence
        "j": (
            "color2",
            [(0, 0, 255), (255, 0, 255), (0, 255, 0), (255, 128, 0)],
        ),  # Second sequence
    }

    # Available patterns
    patterns = {
        "p1": (
            WavePattern,
            {"red": 255, "green": 0, "blue": 0, "speed": 1.0, "wavelength": 1.0},
        ),
        "p2": (RainbowPattern, {"speed": 1.0, "scale": 1.0}),
        "p3": (
            ChasePattern,
            {"red": 0, "green": 255, "blue": 0, "speed": 1.0, "size": 3, "count": 3},
        ),
        "p4": (
            ScanPattern,
            {
                "red": 0,
                "green": 0,
                "blue": 255,
                "speed": 0.5,
                "width": 3,
                "fade": 0.3,
                "bounce": True,
            },
        ),
        "p5": (
            TwinklePattern,
            {"red": 255, "green": 255, "blue": 255, "density": 0.3, "fade_speed": 1.0},
        ),
        "p6": (
            BreathePattern,
            {
                "red": 255,
                "green": 0,
                "blue": 255,
                "speed": 1.0,
                "min_brightness": 0.0,
                "max_brightness": 1.0,
            },
        ),
    }

    # Modifiers
    modifiers = {
        "i": ModifierState(
            BrightnessModifier, "brightness", [1.0, 0.75, 0.5, 0.25, 0.1]
        ),
        "s": ModifierState(SpeedModifier, "speed", [0.5, 1.0, 2.0, 4.0]),
        "d": ModifierState(DirectionModifier, "reverse", [True, False]),
        "m": ModifierState(MirrorModifier, "center", [0.25, 0.5, 0.75]),
        "t": ModifierState(StrobeModifier, "rate", [1.0, 2.0, 4.0]),
        "a": ModifierState(FadeModifier, "period", [0.5, 1.0, 2.0]),
        "c": ModifierState(ColorCycleModifier, "enabled", [True]),
    }

    print("\nPattern Modifier Tester")
    print("\nPatterns (press 'p' then number):")
    print("p1: Wave    p2: Rainbow    p3: Chase")
    print("p4: Scan    p5: Twinkle    p6: Breathe")
    print("\nColors:")
    print("r: Red    g: Green    b: Blue")
    print("h: Alt Color 1    j: Alt Color 2")
    print("\nPattern Parameters:")
    print("w: Wavelength   e: Count       r: Width")
    print("f: Fade        n: Density     x: Bounce")
    print("v: Speed")
    print("\nModifiers:")
    print("i: Brightness   s: Speed      d: Direction")
    print("m: Mirror      t: Strobe     a: Fade")
    print("c: Color Cycle")
    print("\nEnter: Apply changes")
    print("q: Exit")

    # Initialize with first pattern
    current_pattern_key = "p1"
    pattern_class, pattern_params = patterns[current_pattern_key]
    pattern = pattern_class(led_count)
    print(f"Starting with pattern: {pattern_class.__name__}")

    # Track states
    param_states = {k: 0 for k in pattern_controls.keys()}
    color_states = {k: 0 for k in colors.keys()}
    alt_color_states = {k: 0 for k in alt_colors.keys()}

    running = True
    buffer = []
    pattern_select_mode = False

    try:
        while running:
            if sys.stdin in select.select([sys.stdin], [], [], 0.0)[0]:
                key = sys.stdin.read(1).lower()

                if key == "q":
                    running = False

                elif key == "\n":
                    if buffer:
                        print("\nApplying changes...")
                        buffer = []
                        pattern_select_mode = False

                # Pattern selection (two-step)
                elif key == "p":
                    pattern_select_mode = True
                    print("Select pattern (1-6):")
                elif pattern_select_mode and key in "123456":
                    pattern_key = f"p{key}"
                    if pattern_key in patterns:
                        pattern_class, pattern_params = patterns[pattern_key]
                        pattern = pattern_class(led_count)
                        print(f"Switched to pattern {pattern_class.__name__}")
                    pattern_select_mode = False

                # Pattern parameter control
                elif key in pattern_controls:
                    param_name, values = pattern_controls[key]
                    if param_name in pattern_params:
                        param_states[key] = (param_states[key] + 1) % len(values)
                        new_value = values[param_states[key]]
                        pattern_params[param_name] = new_value
                        print(f"Set {param_name} = {new_value}")

                        # Show current parameters for the pattern
                        relevant_params = {
                            k: v
                            for k, v in pattern_params.items()
                            if k in [p[0] for p in pattern_controls.values()]
                        }
                        print(f"Current parameters: {relevant_params}")

                # Color control
                elif key in colors:
                    param_name, values = colors[key]
                    color_states[key] = (color_states[key] + 1) % len(values)
                    new_value = values[color_states[key]]
                    pattern_params[param_name] = new_value
                    print(f"Set {param_name} = {new_value}")
                    print(
                        f"Colors: R:{pattern_params.get('red', 0)} "
                        f"G:{pattern_params.get('green', 0)} "
                        f"B:{pattern_params.get('blue', 0)}"
                    )

                # Alt color control
                elif key in alt_colors:
                    param_name, values = alt_colors[key]
                    alt_color_states[key] = (alt_color_states[key] + 1) % len(values)
                    new_value = values[alt_color_states[key]]
                    if "c" in modifiers and modifiers["c"].enabled:
                        modifiers["c"].modifier.parameters[param_name] = new_value
                        print(f"Set alternating {param_name} = {new_value}")

                # Modifier control
                elif key in modifiers:
                    mod_state = modifiers[key]
                    mod_state.cycle()
                    if mod_state.enabled:
                        print(f"Enabled modifier {key}: {mod_state.get_params()}")
                    else:
                        print(f"Disabled modifier {key}")

            # Generate and display pattern
            current_time = time.time() * 1000
            frame = pattern.generate(current_time, pattern_params)

            # Apply active modifiers
            for mod_state in modifiers.values():
                if mod_state.enabled:
                    frame = mod_state.modifier.apply(frame, mod_state.get_params())

            # Print frame data for visualization
            print("\033[H\033[J")  # Clear screen
            print("Pattern:", pattern_class.__name__)
            print("Active modifiers:", [k for k, v in modifiers.items() if v.enabled])
            print("\nFrame preview (first 10 pixels):")
            print(frame[:10])

            time.sleep(1 / 60)

    except KeyboardInterrupt:
        print("\nStopping...")


if __name__ == "__main__":
    main()
