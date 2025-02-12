import logging
import time
import asyncio
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Type, Set
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from fastapi import WebSocket

from ..core.websocket_manager import manager as ws_manager
from ..core.exceptions import ValidationError, PatternError
from ..core.timing import TimeState, TimingConstraints
from ..common.patterns import determine_pattern_category
from .config import PatternConfig, PatternState
from .base import BasePattern, ModifiableAttribute, Parameter, PatternMetrics
from .modifiers.base import BaseModifier
from .types import (
    BreathePattern,
    ChasePattern,
    GradientPattern,
    MeteorPattern,
    RainbowPattern,
    ScanPattern,
    SolidPattern,
    TwinklePattern,
    WavePattern,
)
from .transitions import CrossFadeTransition, InstantTransition, Transition

logger = logging.getLogger(__name__)


@dataclass
class EngineMetrics:
    """Pattern engine performance metrics"""

    current_pattern: str = ""
    pattern_changes: int = 0
    total_frames: int = 0
    dropped_frames: int = 0
    transition_count: int = 0
    error_count: int = 0
    last_error: str = ""
    last_error_time: float = 0.0
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    pattern_metrics: Dict[str, PatternMetrics] = field(default_factory=dict)

    def record_error(self, error: str, error_type: Optional[str] = None) -> None:
        """Record an error occurrence with additional context"""
        self.error_count += 1
        self.last_error = error
        self.last_error_time = time.time()

        # Keep track of error history (last 10 errors)
        error_entry = {
            "timestamp": self.last_error_time,
            "message": error,
            "type": error_type or "unknown",
            "pattern": self.current_pattern,
        }
        self.error_history.append(error_entry)
        if len(self.error_history) > 10:
            self.error_history.pop(0)

        # Log with appropriate severity
        if isinstance(error, (ValidationError, PatternError)):
            logger.warning(f"Pattern engine error: {error}")
        else:
            logger.error(f"Pattern engine error: {error}", exc_info=True)


@dataclass
class TransitionState:
    """Transition state tracking"""

    is_active: bool = False
    progress: float = 0.0  # 0-1
    source_pattern: Optional[str] = None
    target_pattern: Optional[str] = None
    transition: Optional[Transition] = None
    start_time: float = 0.0
    duration_ms: float = 0.0


class PatternEngine:
    """Manages patterns with improved state handling"""

    def __init__(self, num_leds: int):
        """Initialize pattern engine"""
        self.num_leds = num_leds
        self.patterns: Dict[str, Type[BasePattern]] = {}
        self.pattern_instances: Dict[str, BasePattern] = {}
        self.current_pattern: Optional[BasePattern] = None
        self.previous_pattern: Optional[BasePattern] = None

        # State management
        self.time_state = TimeState()
        self.transition_state = TransitionState()
        self.metrics = EngineMetrics()

        # Frame management
        self.frame_buffer = np.zeros((num_leds, 3), dtype=np.uint8)
        self._last_valid_frame = None

        # Timing constraints
        self.timing = TimingConstraints.from_config(num_leds)

        # Initialize transitions
        self._init_transitions()

    def _init_transitions(self) -> None:
        """Initialize available transitions"""
        self.transitions = {
            "crossfade": CrossFadeTransition(),
            "instant": InstantTransition(),
        }
        self.default_transition = "crossfade"
        self.default_transition_duration_ms = 500.0

    async def register_pattern(self, pattern_class: Type[BasePattern]) -> None:
        """Register a pattern class"""
        try:
            # Create test instance to validate pattern
            test_instance = pattern_class(self.num_leds)
            test_frame = await self._generate_test_frame(test_instance)

            if test_frame is not None:
                name = pattern_class.name.lower()
                self.patterns[name] = pattern_class
                self.pattern_instances[name] = test_instance
                logger.info(f"Registered pattern: {name}")
            else:
                raise PatternError("Pattern failed to generate test frame")

        except Exception as e:
            logger.error(f"Failed to register pattern {pattern_class.__name__}: {e}")
            self.metrics.record_error(f"Pattern registration failed: {str(e)}")

    async def _generate_test_frame(self, pattern: BasePattern) -> Optional[np.ndarray]:
        """Generate a test frame from a pattern"""
        try:
            frame = await pattern.generate(time.perf_counter() * 1000)
            if frame is None or frame.shape != (self.num_leds, 3):
                raise PatternError("Invalid frame generated")
            return frame
        except Exception as e:
            logger.error(f"Test frame generation failed: {e}")
            return None

    async def set_pattern(
        self,
        pattern_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        transition: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Set active pattern with transition"""
        try:
            # Validate pattern exists
            if pattern_name not in self.patterns:
                raise ValidationError(f"Unknown pattern: {pattern_name}")

            # Get or create pattern instance
            new_pattern = self.pattern_instances.get(pattern_name)
            if new_pattern is None:
                new_pattern = self.patterns[pattern_name](self.num_leds)
                self.pattern_instances[pattern_name] = new_pattern

            # Update parameters if provided
            if parameters:
                await new_pattern.update_parameters(parameters)

            # Setup transition
            if self.current_pattern is not None:
                transition_name = transition or self.default_transition
                transition_obj = self.transitions.get(transition_name)
                if transition_obj is None:
                    logger.warning(
                        f"Unknown transition {transition_name}, using default"
                    )
                    transition_obj = self.transitions[self.default_transition]

                self.transition_state.is_active = True
                self.transition_state.progress = 0.0
                self.transition_state.source_pattern = self.current_pattern.name
                self.transition_state.target_pattern = pattern_name
                self.transition_state.transition = transition_obj
                self.transition_state.start_time = time.perf_counter()
                self.transition_state.duration_ms = (
                    duration_ms or self.default_transition_duration_ms
                )

            # Update state
            self.previous_pattern = self.current_pattern
            self.current_pattern = new_pattern
            self.metrics.pattern_changes += 1
            self.metrics.current_pattern = pattern_name

            logger.info(f"Set pattern to {pattern_name}")

        except Exception as e:
            self.metrics.record_error(f"Pattern change failed: {str(e)}")
            raise

    async def update_parameters(self, parameters: Dict[str, Any]) -> None:
        """Update current pattern parameters"""
        if self.current_pattern is None:
            raise ValidationError("No active pattern")

        try:
            await self.current_pattern.update_parameters(parameters)
        except Exception as e:
            self.metrics.record_error(f"Parameter update failed: {str(e)}")
            raise

    async def generate_frame(self, time_ms: float) -> Optional[np.ndarray]:
        """Generate frame with transition handling"""
        try:
            if self.current_pattern is None:
                return self.frame_buffer

            # Update timing
            self.time_state.update()

            # Handle transition
            if self.transition_state.is_active:
                frame = await self._handle_transition(time_ms)
            else:
                frame = await self.current_pattern.generate(time_ms)

            # Validate and store frame
            if frame is not None:
                if frame.shape != (self.num_leds, 3):
                    raise PatternError(f"Invalid frame shape: {frame.shape}")
                self._last_valid_frame = frame.copy()
                self.frame_buffer = frame
                self.metrics.total_frames += 1
            else:
                self.metrics.dropped_frames += 1
                frame = (
                    self._last_valid_frame
                    if self._last_valid_frame is not None
                    else self.frame_buffer
                )

            return frame

        except Exception as e:
            self.metrics.record_error(f"Frame generation failed: {str(e)}")
            self.metrics.dropped_frames += 1
            return (
                self._last_valid_frame
                if self._last_valid_frame is not None
                else self.frame_buffer
            )

    async def _handle_transition(self, time_ms: float) -> Optional[np.ndarray]:
        """Handle pattern transition"""
        try:
            # Calculate transition progress
            elapsed = time.perf_counter() - self.transition_state.start_time
            progress = min(1.0, elapsed * 1000 / self.transition_state.duration_ms)
            self.transition_state.progress = progress

            # Generate frames from both patterns
            source_frame = (
                await self.previous_pattern.generate(time_ms)
                if self.previous_pattern is not None
                else None
            )
            target_frame = await self.current_pattern.generate(time_ms)

            # Apply transition
            if source_frame is not None and target_frame is not None:
                frame = self.transition_state.transition.apply(
                    source_frame, target_frame, progress
                )
            else:
                frame = target_frame if target_frame is not None else source_frame

            # Check if transition is complete
            if progress >= 1.0:
                self.transition_state.is_active = False
                self.metrics.transition_count += 1
                logger.debug("Transition complete")

            return frame

        except Exception as e:
            self.metrics.record_error(f"Transition failed: {str(e)}")
            self.transition_state.is_active = False
            return None

    def get_state(self) -> Dict[str, Any]:
        """Get engine state"""
        return {
            "current_pattern": self.current_pattern.name
            if self.current_pattern
            else None,
            "available_patterns": list(self.patterns.keys()),
            "transition": {
                "active": self.transition_state.is_active,
                "progress": self.transition_state.progress,
                "source": self.transition_state.source_pattern,
                "target": self.transition_state.target_pattern,
                "duration_ms": self.transition_state.duration_ms,
            },
            "metrics": {
                "total_frames": self.metrics.total_frames,
                "dropped_frames": self.metrics.dropped_frames,
                "pattern_changes": self.metrics.pattern_changes,
                "transition_count": self.metrics.transition_count,
                "error_count": self.metrics.error_count,
                "last_error": self.metrics.last_error,
            },
            "timing": self.time_state.get_metrics(),
        }

    async def cleanup(self) -> None:
        """Cleanup engine resources"""
        self.current_pattern = None
        self.previous_pattern = None
        self.pattern_instances.clear()
        self.patterns.clear()
        self.frame_buffer.fill(0)
        self._last_valid_frame = None
        logger.info("Pattern engine cleaned up")

    async def get_available_patterns(self) -> List[Dict[str, Any]]:
        """Get available pattern definitions"""
        patterns = []
        for name, pattern_class in self.patterns.items():
            try:
                # Create test instance to validate pattern
                test_instance = pattern_class(self.num_leds)

                # Get pattern metadata
                pattern_info = {
                    "name": name,
                    "description": pattern_class.description,
                    "parameters": {},
                    "category": determine_pattern_category(name),
                    "supports_audio": hasattr(pattern_class, "process_audio"),
                    "supports_transitions": True,  # All patterns support transitions
                }

                # Get parameter specifications
                for param in pattern_class.parameters:
                    pattern_info["parameters"][param.name] = {
                        "type": param.type.__name__,
                        "default": param.default,
                        "min_value": param.min_value,
                        "max_value": param.max_value,
                        "description": param.description,
                        "units": param.units,
                    }

                patterns.append(pattern_info)

            except Exception as e:
                logger.error(f"Failed to get pattern info for {name}: {e}")
                continue

        return patterns

    async def get_pattern_info(self, pattern_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific pattern"""
        if pattern_name not in self.patterns:
            return None

        pattern_class = self.patterns[pattern_name]
        try:
            test_instance = pattern_class(self.num_leds)

            return {
                "name": pattern_name,
                "description": pattern_class.description,
                "parameters": {
                    param.name: {
                        "type": param.type.__name__,
                        "default": param.default,
                        "min_value": param.min_value,
                        "max_value": param.max_value,
                        "description": param.description,
                        "units": param.units,
                    }
                    for param in pattern_class.parameters
                },
                "category": determine_pattern_category(pattern_name),
                "supports_audio": hasattr(pattern_class, "process_audio"),
                "supports_transitions": True,
                "state": test_instance.get_state()
                if hasattr(test_instance, "get_state")
                else None,
            }
        except Exception as e:
            logger.error(f"Failed to get pattern info for {pattern_name}: {e}")
            return None

    def get_current_pattern_state(self) -> Dict[str, Any]:
        """Get current pattern state"""
        if not self.current_pattern:
            return {
                "active": False,
                "name": None,
                "parameters": {},
                "frame_count": 0,
                "transition": {
                    "active": False,
                    "progress": 0,
                    "source": None,
                    "target": None,
                },
            }

        return {
            "active": True,
            "name": self.current_pattern.name,
            "parameters": self.current_pattern.state.parameters,
            "frame_count": self.current_pattern.state.frame_count,
            "transition": {
                "active": self.transition_state.is_active,
                "progress": self.transition_state.progress,
                "source": self.transition_state.source_pattern,
                "target": self.transition_state.target_pattern,
            },
            "metrics": self.current_pattern.state.metrics.get_metrics(),
        }
