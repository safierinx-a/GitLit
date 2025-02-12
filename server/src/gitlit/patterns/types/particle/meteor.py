import random
from typing import Any, Dict, List, Tuple
import numpy as np

from ...base import BasePattern, ColorSpec, ModifiableAttribute, Parameter


class MeteorPattern(BasePattern):
    """Meteor effect with trailing particles"""

    name = "meteor"
    description = "Meteor effect with trailing particles"

    parameters = [
        ColorSpec(name="red", description="Red component"),
        ColorSpec(name="green", description="Green component"),
        ColorSpec(name="blue", description="Blue component"),
        Parameter(
            name="speed",
            type=float,
            default=1.0,
            min_value=0.1,
            max_value=5.0,
            description="Meteor speed",
            units="Hz",
        ),
        Parameter(
            name="size",
            type=int,
            default=3,
            min_value=1,
            max_value=10,
            description="Size of meteor head",
        ),
        Parameter(
            name="trail_length",
            type=float,
            default=0.5,
            min_value=0.0,
            max_value=1.0,
            description="Length of meteor trail",
        ),
        Parameter(
            name="decay",
            type=float,
            default=0.8,
            min_value=0.0,
            max_value=1.0,
            description="Trail decay rate",
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
                    Parameter(
                        name="rate_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Spawn rate multiplier",
                    ),
                    Parameter(
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
                    Parameter(
                        name="speed_scale",
                        type=float,
                        default=1.0,
                        min_value=0.1,
                        max_value=5.0,
                        description="Speed multiplier",
                    ),
                    Parameter(
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
        decay = params.get("decay", 0.8)
        direction = params.get("direction", 1)

        # Clear frame
        self.frame_buffer.fill(0)

        # Update timing
        dt = self.timing.delta_time
        current_time = time_ms / 1000.0

        # Calculate meteor position
        t = (current_time * speed) % 1.0
        pos = int(t * self.led_count)

        # Draw meteor head
        for i in range(size):
            idx = (pos + i) % self.led_count
            self.frame_buffer[idx] = self._get_meteor_color(params)

        # Draw trail
        trail_size = int(self.led_count * trail_length)
        for i in range(trail_size):
            idx = (pos - i) % self.led_count
            fade = (1.0 - (i / trail_size)) * decay
            if fade > 0:
                self.frame_buffer[idx] = (self._get_meteor_color(params) * fade).astype(
                    np.uint8
                )

        return self.frame_buffer
