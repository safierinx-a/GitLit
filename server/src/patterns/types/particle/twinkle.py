from ...base import BasePattern, ParameterSpec, ModifiableAttribute, ColorSpec
import numpy as np
from typing import Dict, Any, List
import random


class TwinklePattern(BasePattern):
    """Random twinkling lights that fade in and out"""

    def __init__(self, led_count: int):
        super().__init__(led_count)
        self.state.cached_data[
            "active_twinkles"
        ] = {}  # {position: (brightness, color)}
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
            ParameterSpec(
                name="min_brightness",
                type=float,
                default=0.0,
                min_value=0.0,
                max_value=1.0,
                description="Minimum brightness of twinkle",
            ),
            ParameterSpec(
                name="max_brightness",
                type=float,
                default=1.0,
                min_value=0.0,
                max_value=1.0,
                description="Maximum brightness of twinkle",
            ),
        ]

    def _generate(self, time_ms: float, params: Dict[str, Any]) -> np.ndarray:
        active_twinkles = self.state.cached_data["active_twinkles"]
        density = params.get("density", 0.1)
        fade_speed = params.get("fade_speed", 1.0)
        min_brightness = params.get("min_brightness", 0.0)
        max_brightness = params.get("max_brightness", 1.0)
        random_color = params.get("random_color", False)
        base_color = np.array(
            [params.get("red", 255), params.get("green", 255), params.get("blue", 255)],
            dtype=np.uint8,
        )

        self.frame_buffer.fill(0)

        # Spawn new twinkles
        spawn_chance = density * self.timing.delta_time * 30
        if random.random() < spawn_chance:
            pos = random.randint(0, self.led_count - 1)
            color = (
                np.array([random.randint(0, 255) for _ in range(3)], dtype=np.uint8)
                if random_color
                else base_color
            )
            brightness = random.uniform(min_brightness, max_brightness)
            active_twinkles[pos] = (brightness, color)

        # Update existing twinkles
        to_remove = []
        for pos, (brightness, color) in active_twinkles.items():
            brightness -= fade_speed * self.timing.delta_time * self.timing.time_scale
            if brightness <= min_brightness:
                to_remove.append(pos)
            else:
                active_twinkles[pos] = (brightness, color)
                self.frame_buffer[pos] = (color * brightness).astype(np.uint8)

        for pos in to_remove:
            del active_twinkles[pos]

        return self.frame_buffer
