import random
from typing import Any, Dict, List, Tuple
import numpy as np

from ...base import BasePattern, ColorSpec, ModifiableAttribute, ParameterSpec


class MeteorPattern(BasePattern):
    """Falling meteor effect with trails and physics"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data["meteors"] = []  # [(position, velocity, color, trail)]
        self.state.cached_data["last_spawn_time"] = 0.0

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
            ParameterSpec(
                name="gravity",
                type=float,
                default=9.8,
                min_value=0.0,
                max_value=20.0,
                description="Gravitational acceleration",
                units="units/s²",
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
            ParameterSpec(
                name="direction",
                type=int,
                default=1,
                min_value=-1,
                max_value=1,
                description="Meteor direction (-1: up, 1: down)",
            ),
        ]

    @classmethod
    @property
    def modifiable_attributes(cls) -> List[ModifiableAttribute]:
        return [
            ModifiableAttribute(
                name="spawn",
                description="Meteor spawning properties",
                parameter_specs=[
                    ParameterSpec(
                        name="rate_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Spawn rate multiplier",
                    ),
                    ParameterSpec(
                        name="size_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Size multiplier",
                    ),
                ],
                supports_audio=True,
            ),
            ModifiableAttribute(
                name="motion",
                description="Meteor motion properties",
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
                        name="gravity_scale",
                        type=float,
                        default=1.0,
                        min_value=0.0,
                        max_value=5.0,
                        description="Gravity multiplier",
                    ),
                ],
                supports_audio=True,
            ),
        ]

    def _get_meteor_color(self, params: Dict[str, Any]) -> np.ndarray:
        """Get meteor color, either from parameters or random"""
        if params.get("random_color", False):
            return np.array(
                [
                    random.randint(0, 255),
                    random.randint(0, 255),
                    random.randint(0, 255),
                ],
                dtype=np.uint8,
            )
        return np.array(
            [params.get("red", 255), params.get("green", 255), params.get("blue", 255)],
            dtype=np.uint8,
        )

    def _draw_meteor(
        self,
        pos: float,
        size: int,
        trail_length: float,
        color: np.ndarray,
        direction: int,
    ) -> None:
        """Draw a meteor with trail at the given position"""
        # Calculate meteor head position
        head_pos = int(pos)
        if not (0 <= head_pos < self.led_count):
            return

        # Draw meteor head
        for i in range(max(0, head_pos - size + 1), min(self.led_count, head_pos + 1)):
            self.frame_buffer[i] = color

        # Draw trail
        trail_pixels = int(trail_length * self.led_count)
        for i in range(trail_pixels):
            trail_pos = head_pos - (i + size) * direction
            if 0 <= trail_pos < self.led_count:
                fade = 1.0 - (i / trail_pixels)
                self.frame_buffer[trail_pos] = (color * fade).astype(np.uint8)

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        """Generate meteor pattern with physics"""
        # Get parameters
        speed = params.get("speed", 1.0)
        size = params.get("size", 3)
        trail_length = params.get("trail_length", 0.5)
        spawn_rate = params.get("spawn_rate", 0.5)
        gravity = params.get("gravity", 9.8)
        direction = params.get("direction", 1)

        # Clear frame
        self.frame_buffer.fill(0)

        # Update timing
        dt = self.timing.delta_time
        current_time = time_ms / 1000.0

        # Spawn new meteors
        if current_time - self.state.cached_data["last_spawn_time"] > 1.0 / spawn_rate:
            color = self._get_meteor_color(params)
            initial_velocity = speed * 10  # Initial velocity scaling
            self.state.cached_data["meteors"].append(
                [
                    0 if direction > 0 else self.led_count - 1,  # Initial position
                    initial_velocity,
                    color,
                    [],  # Trail positions
                ]
            )
            self.state.cached_data["last_spawn_time"] = current_time

        # Update and draw meteors
        new_meteors = []
        for meteor in self.state.cached_data["meteors"]:
            pos, vel, color, trail = meteor

            # Update physics
            vel += gravity * dt * direction
            new_pos = pos + vel * dt

            # Check if meteor is still on strip
            if 0 <= new_pos < self.led_count:
                # Update trail
                trail.append(pos)
                if len(trail) > size + int(trail_length * self.led_count):
                    trail.pop(0)

                # Draw meteor and trail
                self._draw_meteor(new_pos, size, trail_length, color, direction)

                # Keep meteor
                new_meteors.append([new_pos, vel, color, trail])

        # Update state
        self.state.cached_data["meteors"] = new_meteors
        return self.frame_buffer
