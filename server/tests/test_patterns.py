#!/usr/bin/env python3

"""Tests for pattern functionality."""

import os
import sys
import time

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(project_root)

import yaml
from gitlit.patterns.base import BasePattern
from gitlit.patterns.engine import PatternEngine
from gitlit.patterns.types.static.solid import SolidPattern
from gitlit.patterns.types.static.gradient import GradientPattern
from gitlit.patterns.types.moving.wave import WavePattern
from gitlit.patterns.types.moving.rainbow import RainbowPattern
from gitlit.patterns.types.moving.chase import ChasePattern
from gitlit.patterns.types.moving.scan import ScanPattern
from gitlit.patterns.types.particle.twinkle import TwinklePattern
from gitlit.patterns.types.particle.meteor import MeteorPattern
from gitlit.patterns.types.particle.breathe import BreathePattern
from gitlit.core.exceptions import ValidationError

import pytest
import numpy as np


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


@pytest.fixture
def num_leds():
    """Test LED count"""
    return 60


@pytest.fixture
async def pattern_engine(num_leds):
    """Test pattern engine"""
    engine = PatternEngine(num_leds)
    await engine.start()
    yield engine
    await engine.stop()


class TestPatternBase:
    """Test base pattern functionality"""

    def test_pattern_initialization(self, num_leds):
        """Test pattern initialization"""
        pattern = SolidPattern(num_leds)
        assert pattern.num_leds == num_leds
        assert pattern.frame_buffer.shape == (num_leds, 3)
        assert pattern.frame_buffer.dtype == np.uint8

    async def test_parameter_validation(self, num_leds):
        """Test parameter validation"""
        pattern = SolidPattern(num_leds)

        # Valid parameters
        await pattern.update_parameters({"red": 255, "green": 0, "blue": 0})

        # Invalid parameters
        with pytest.raises(ValidationError):
            await pattern.update_parameters({"red": 300})  # Invalid value


class TestPatternTypes:
    """Test specific pattern implementations"""

    async def test_solid_pattern(self, num_leds):
        """Test solid color pattern"""
        pattern = SolidPattern(num_leds)
        await pattern.update_parameters({"red": 255, "green": 0, "blue": 0})

        frame = await pattern.generate(0)
        assert frame is not None
        assert np.all(frame[:, 0] == 255)  # Red channel
        assert np.all(frame[:, 1:] == 0)  # Green and Blue channels

    async def test_gradient_pattern(self, num_leds):
        """Test gradient pattern"""
        pattern = GradientPattern(num_leds)
        await pattern.update_parameters(
            {
                "color1_r": 255,
                "color1_g": 0,
                "color1_b": 0,
                "color2_r": 0,
                "color2_g": 0,
                "color2_b": 255,
                "position": 0.5,
            }
        )

        frame = await pattern.generate(0)
        assert frame is not None
        assert frame.shape == (num_leds, 3)
        # Check gradient properties
        assert frame[0][0] > frame[-1][0]  # Red decreases
        assert frame[0][2] < frame[-1][2]  # Blue increases

    async def test_rainbow_pattern(self, num_leds):
        """Test rainbow pattern"""
        pattern = RainbowPattern(num_leds)
        await pattern.update_parameters({"speed": 1.0, "scale": 1.0})

        # Generate multiple frames to test movement
        frame1 = await pattern.generate(0)
        frame2 = await pattern.generate(1000)  # 1 second later

        assert not np.array_equal(frame1, frame2)  # Pattern should move


class TestPatternEngine:
    """Test pattern engine functionality"""

    async def test_pattern_registration(self, pattern_engine):
        """Test pattern registration"""
        patterns = await pattern_engine.get_available_patterns()
        assert len(patterns) > 0
        assert any(p["name"] == "solid" for p in patterns)

    async def test_pattern_transition(self, pattern_engine):
        """Test pattern transitions"""
        # Set initial pattern
        await pattern_engine.set_pattern("solid", {"red": 255, "green": 0, "blue": 0})

        # Transition to new pattern
        await pattern_engine.set_pattern(
            "gradient",
            {
                "color1_r": 0,
                "color1_g": 255,
                "color1_b": 0,
                "color2_r": 0,
                "color2_g": 0,
                "color2_b": 255,
            },
            transition="crossfade",
            duration_ms=100,
        )

        # Check transition state
        assert pattern_engine.transition_state.is_active
        assert pattern_engine.transition_state.source_pattern == "solid"
        assert pattern_engine.transition_state.target_pattern == "gradient"


class TestErrorHandling:
    """Test pattern error handling"""

    async def test_invalid_parameters(self, pattern_engine):
        """Test invalid parameter handling"""
        with pytest.raises(ValidationError):
            await pattern_engine.set_pattern("solid", {"red": 300})

    async def test_frame_generation_error(self, num_leds):
        """Test frame generation error handling"""
        pattern = SolidPattern(num_leds)
        # Force an error in frame generation
        pattern._generate = lambda t: None  # Invalid frame

        frame = await pattern.generate(0)
        assert frame is not None  # Should return emergency frame
        assert frame.shape == (num_leds, 3)
