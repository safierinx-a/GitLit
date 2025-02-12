from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator
from ..patterns.base import ParameterSpec, ColorSpec, ModifiableAttribute


# Base Models
class BaseResponse(BaseModel):
    """Base response model with status and message"""

    status: str
    message: str


class ErrorResponse(BaseResponse):
    """Error response model"""

    detail: str


# Parameter Types
class ParameterType(str, Enum):
    """Types of pattern parameters"""

    COLOR = "color"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ENUM = "enum"
    POSITION = "position"
    SPEED = "speed"
    TIME = "time"
    ANGLE = "angle"
    PERCENTAGE = "percentage"


class ParameterMetadata(BaseModel):
    """Metadata for a pattern parameter"""

    name: str
    type: ParameterType
    description: str
    required: bool = False
    default: Optional[Any] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    units: Optional[str] = None
    options: Optional[List[str]] = None  # For enum types


class Parameter(BaseModel):
    """A pattern parameter value"""

    type: ParameterType
    value: Any

    @validator("value")
    def validate_value(cls, v, values):
        param_type = values.get("type")
        if param_type == ParameterType.COLOR:
            if not isinstance(v, dict) or not all(
                k in v for k in ["red", "green", "blue"]
            ):
                raise ValueError("Color must have red, green, and blue components")
            for component in ["red", "green", "blue"]:
                if not 0 <= v[component] <= 255:
                    raise ValueError(f"Color {component} must be between 0 and 255")
        elif param_type == ParameterType.NUMBER:
            if not isinstance(v, (int, float)):
                raise ValueError("Number must be integer or float")
        elif param_type == ParameterType.BOOLEAN:
            if not isinstance(v, bool):
                raise ValueError("Value must be boolean")
        elif param_type == ParameterType.POSITION:
            if not isinstance(v, (int, float)) or not 0 <= v <= 1:
                raise ValueError("Position must be between 0 and 1")
        elif param_type == ParameterType.SPEED:
            if not isinstance(v, (int, float)) or v <= 0:
                raise ValueError("Speed must be greater than 0")
        elif param_type == ParameterType.PERCENTAGE:
            if not isinstance(v, (int, float)) or not 0 <= v <= 100:
                raise ValueError("Percentage must be between 0 and 100")
        return v


# Pattern Models
class PatternCategory(str, Enum):
    """Categories of patterns"""

    STATIC = "static"
    MOVING = "moving"
    PARTICLE = "particle"
    OTHER = "other"


class TransitionType(str, Enum):
    """Types of pattern transitions"""

    CROSSFADE = "crossfade"
    INSTANT = "instant"
    WIPE = "wipe"
    SLIDE = "slide"
    FADE = "fade"


class TransitionRequest(BaseModel):
    """Pattern transition request"""

    type: TransitionType = TransitionType.CROSSFADE
    duration_ms: float = Field(500.0, ge=0)


class PatternRequest(BaseModel):
    """Request to set a pattern"""

    parameters: Dict[str, Any] = Field(default_factory=dict)
    transition: Optional[TransitionRequest] = None

    @validator("parameters")
    def validate_parameters(cls, v):
        """Validate parameters against pattern specs"""
        # Basic validation, detailed validation happens in the controller
        if not isinstance(v, dict):
            raise ValueError("Parameters must be a dictionary")
        return v


class PatternDefinition(BaseModel):
    """Pattern definition with enhanced metadata"""

    name: str
    category: str
    description: str
    parameters: List[ParameterSpec]
    supports_audio: bool = False
    supports_transitions: bool = True
    preview_url: Optional[str] = None  # URL to pattern preview animation


class TransitionState(BaseModel):
    """Pattern transition state"""

    active: bool
    progress: float = Field(0.0, ge=0.0, le=1.0)
    source: Optional[str] = None
    target: Optional[str] = None


# Modifier Models
class ModifierCategory(str, Enum):
    """Categories of modifiers"""

    EFFECT = "effect"
    AUDIO = "audio"
    COMPOSITE = "composite"
    CUSTOM = "custom"


class ModifierDefinition(BaseModel):
    """Definition of a modifier"""

    name: str
    category: ModifierCategory
    description: str
    parameters: Dict[str, ParameterMetadata]
    supported_audio_metrics: Optional[List[str]] = None


class ModifierRequest(BaseModel):
    """Request to apply a modifier"""

    modifier_name: str
    parameters: Dict[str, Parameter]

    @validator("parameters")
    def validate_parameters(cls, v):
        # Additional validation can be added here
        return v


# Audio Models
class AudioMetric(str, Enum):
    """Available audio metrics"""

    VOLUME = "volume"
    BEAT = "beat"
    ONSET = "onset"
    SPECTRUM = "spectrum"
    FREQUENCY = "frequency"
    CUSTOM = "custom"


class AudioBinding(BaseModel):
    """Audio binding configuration"""

    modifier_name: str
    parameter_name: str
    metric: AudioMetric
    scale: float = Field(1.0, gt=0)
    offset: float = 0.0


# System State Models
class PerformanceMetrics(BaseModel):
    """Enhanced performance metrics"""

    fps: float
    frame_time: float
    frame_count: int
    dropped_frames: int
    buffer_usage: float
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None


class SystemState(BaseModel):
    """Enhanced system state model"""

    active_pattern: Optional[str]
    pattern_parameters: Dict[str, Any]
    transition_state: TransitionState
    performance: Optional[PerformanceMetrics]
    is_running: bool
    error: Optional[str] = None


# Registry Models
class PatternRegistry:
    """Enhanced pattern registry with metadata"""

    def __init__(self):
        self._patterns: Dict[str, PatternDefinition] = {}
        self._categories: Dict[str, List[str]] = {}

    def register_pattern(self, pattern: PatternDefinition) -> None:
        """Register a pattern with category indexing"""
        self._patterns[pattern.name] = pattern

        # Index by category
        if pattern.category not in self._categories:
            self._categories[pattern.category] = []
        self._categories[pattern.category].append(pattern.name)

    def get_pattern(self, name: str) -> Optional[PatternDefinition]:
        """Get pattern by name"""
        return self._patterns.get(name)

    def get_all_patterns(self) -> List[PatternDefinition]:
        """Get all registered patterns"""
        return list(self._patterns.values())

    def get_patterns_by_category(self, category: str) -> List[PatternDefinition]:
        """Get patterns in a category"""
        if category not in self._categories:
            return []
        return [self._patterns[name] for name in self._categories[category]]

    def get_categories(self) -> List[str]:
        """Get available categories"""
        return list(self._categories.keys())


class ModifierRegistry(BaseModel):
    """Registry of available modifiers"""

    modifiers: Dict[str, ModifierDefinition] = {}
    categories: List[ModifierCategory] = []

    def register_modifier(self, modifier: ModifierDefinition) -> None:
        """Register a new modifier"""
        self.modifiers[modifier.name] = modifier
        if modifier.category not in self.categories:
            self.categories.append(modifier.category)

    def get_modifiers_by_category(
        self, category: ModifierCategory
    ) -> List[ModifierDefinition]:
        """Get all modifiers in a category"""
        return [m for m in self.modifiers.values() if m.category == category]
