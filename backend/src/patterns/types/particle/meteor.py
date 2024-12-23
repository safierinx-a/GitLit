from ...base import BasePattern, ParameterSpec, ModifiableAttribute, ColorSpec
import numpy as np
from typing import Dict, Any, List
import random


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

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        meteors = self.state.cached_data["meteors"]
        size = params.get("size", 3)
        trail_length = params.get("trail_length", 0.5)
        random_color = params.get("random_color", False)
        base_color = np.array(
            [params.get("red", 255), params.get("green", 255), params.get("blue", 255)],
            dtype=np.uint8,
        )

        self.frame_buffer.fill(0)

        # Use timing system for spawn rate
        spawn_chance = 0.1 * self.timing.delta_time * 30  # Scale with frame rate
        if random.random() < spawn_chance:
            color = (
                np.array([random.randint(0, 255) for _ in range(3)], dtype=np.uint8)
                if random_color
                else base_color
            )
            # Start at top with base velocity
            meteors.append({"pos": 0.0, "vel": 1.0, "color": color})

        # Update meteors using delta time
        new_meteors = []
        for meteor in meteors:
            # Update position using delta time and speed scaling
            new_pos = meteor["pos"] + (
                meteor["vel"]
                * self.timing.delta_time
                * self.timing.time_scale
                * 30  # Scale to ~30fps
            )

            if new_pos < self.led_count:
                meteor["pos"] = new_pos
                new_meteors.append(meteor)

                # Draw meteor head and trail
                for i in range(size + int(size * trail_length)):
                    pixel_pos = int(new_pos - i)
                    if 0 <= pixel_pos < self.led_count:
                        # Calculate trail intensity
                        if i < size:
                            intensity = 1.0  # Full brightness for head
                        else:
                            trail_pos = i - size
                            intensity = 1.0 - (trail_pos / (size * trail_length))

                        # Apply intensity to color
                        self.frame_buffer[pixel_pos] = (
                            meteor["color"] * intensity
                        ).astype(np.uint8)

        self.state.cached_data["meteors"] = new_meteors
        return self.frame_buffer
