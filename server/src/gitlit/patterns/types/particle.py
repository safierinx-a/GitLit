import math
import random
from typing import Any, Dict, List

import numpy as np

from ...core.exceptions import ValidationError
from ...core.state import PatternState
from ..base import BasePattern, ColorSpec, ModifiableAttribute, ParameterSpec


class TwinklePattern(BasePattern):
    """Random twinkling lights that fade in and out"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data["active_twinkles"] = (
            {}
        )  # {position: (brightness, color)}
        self.state.cached_data["last_density"] = 0.1
        self.state.cached_data["last_fade_speed"] = 1.0

    @classmethod
    @property
    def parameters(cls) -> List[ParameterSpec]:
        return [
            ParameterSpec(
                name="density",
                type=float,
                default=0.1,
                min_value=0.01,
                max_value=0.5,
                description="Probability of new twinkle per frame",
            ),
            ParameterSpec(
                name="fade_speed",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=5.0,
                description="Speed of fade in/out",
                units="Hz",
            ),
            ColorSpec(name="red", description="Red component of twinkle color"),
            ColorSpec(name="green", description="Green component of twinkle color"),
            ColorSpec(name="blue", description="Blue component of twinkle color"),
            ParameterSpec(
                name="random_color",
                type=bool,
                default=False,
                description="Randomize colors of each twinkle",
            ),
        ]

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        return [
            ModifiableAttribute(
                name="spawn",
                description="Twinkle spawning properties",
                parameter_specs=[
                    ParameterSpec(
                        name="density_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Spawn rate multiplier",
                    )
                ],
                supports_audio=True,  # Can sync to beat/volume
            ),
            ModifiableAttribute(
                name="lifetime",
                description="Twinkle lifetime properties",
                parameter_specs=[
                    ParameterSpec(
                        name="fade_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Fade speed multiplier",
                    )
                ],
                supports_audio=True,  # Can react to audio features
            ),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate twinkling lights pattern"""
        active_twinkles = self.state.cached_data["active_twinkles"]
        density = params.get("density", 0.1)
        fade_speed = params.get("fade_speed", 1.0)

        # Cache parameters for transitions
        self.state.cache_value("last_density", density)
        self.state.cache_value("last_fade_speed", fade_speed)

        # Use state's delta_time for timing
        if (
            random.random() < density * self.state.delta_time * 30
        ):  # Normalized to ~30fps
            pos = random.randint(0, self.led_count - 1)
            color = self._get_color(params)
            active_twinkles[pos] = (1.0, color)

        # Update using delta_time
        to_remove = []
        for pos, (brightness, color) in active_twinkles.items():
            brightness -= fade_speed * self.state.delta_time
            if brightness <= 0:
                to_remove.append(pos)
            else:
                active_twinkles[pos] = (brightness, color)
                self.frame_buffer[pos] = [int(c * brightness) for c in color]

        for pos in to_remove:
            del active_twinkles[pos]

        return self.frame_buffer


class MeteorPattern(BasePattern):
    """Falling meteor effect with trails"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data["meteors"] = []  # [(position, velocity, color)]

    @classmethod
    @property
    def parameters(cls) -> List[ParameterSpec]:
        return [
            ParameterSpec(
                name="speed",
                type=float,
                default=1.0,
                min_value=0.1,
                max_value=5.0,
                description="Fall speed",
                units="Hz",
            ),
            ParameterSpec(
                name="size",
                type=int,
                default=3,
                min_value=1,
                max_value=10,
                description="Meteor size",
            ),
            ParameterSpec(
                name="trail_length",
                type=float,
                default=0.5,
                min_value=0.0,
                max_value=1.0,
                description="Length of meteor trail",
            ),
            ParameterSpec(
                name="spawn_rate",
                type=float,
                default=0.5,
                min_value=0.1,
                max_value=2.0,
                description="New meteor frequency",
                units="Hz",
            ),
            ColorSpec(name="red", description="Red component of meteor color"),
            ColorSpec(name="green", description="Green component of meteor color"),
            ColorSpec(name="blue", description="Blue component of meteor color"),
            ParameterSpec(
                name="random_color",
                type=bool,
                default=False,
                description="Randomize meteor colors",
            ),
        ]

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        return [
            ModifiableAttribute(
                name="movement",
                description="Meteor movement properties",
                parameter_specs=[
                    ParameterSpec(
                        name="speed_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Speed multiplier",
                    ),
                    ParameterSpec(
                        name="direction",
                        type=bool,
                        default=True,
                        description="Fall direction",
                    ),
                ],
                supports_audio=True,  # Can sync to beat/onset
            ),
            ModifiableAttribute(
                name="spawning",
                description="Meteor spawning properties",
                parameter_specs=[
                    ParameterSpec(
                        name="spawn_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Spawn rate multiplier",
                    )
                ],
                supports_audio=True,  # Can react to volume/onset
            ),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate falling meteors pattern"""
        meteors = self.state.cached_data["meteors"]
        speed = params.get("speed", 1.0)
        size = params.get("size", 3)
        trail_length = params.get("trail_length", 0.5)
        spawn_rate = params.get("spawn_rate", 0.5)
        random_color = params.get("random_color", False)
        base_color = [
            params.get("red", 255),
            params.get("green", 255),
            params.get("blue", 255),
        ]

        # Clear buffer
        self.frame_buffer.fill(0)

        # Spawn new meteors using delta_time for consistent rate
        if (
            random.random() < spawn_rate * self.state.delta_time * 30
        ):  # Normalized to ~30fps
            color = (
                [random.randint(0, 255) for _ in range(3)]
                if random_color
                else base_color
            )
            meteors.append((0, speed, color))  # Start at top

        # Update meteor positions using delta_time
        new_meteors = []
        for pos, vel, color in meteors:
            new_pos = pos + vel * self.state.delta_time * 30
            if new_pos < self.led_count:
                new_meteors.append((new_pos, vel, color))

                # Draw meteor and trail
                for i in range(size + int(size * trail_length)):
                    pixel_pos = int(new_pos - i)
                    if 0 <= pixel_pos < self.led_count:
                        # Calculate fade based on trail position
                        if i < size:
                            intensity = 1.0  # Full brightness for meteor head
                        else:
                            # Fade trail
                            trail_pos = i - size
                            intensity = 1.0 - (trail_pos / (size * trail_length))

                        self.frame_buffer[pixel_pos] = [
                            int(c * intensity) for c in color
                        ]

        # Update meteor list
        self.state.cached_data["meteors"] = new_meteors

        return self.frame_buffer
