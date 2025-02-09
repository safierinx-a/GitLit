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


class PatternRequest(BaseModel):
    """Request to set a pattern"""

    pattern_name: str
    parameters: Dict[str, Any]

    @validator("parameters")
    def validate_parameters(cls, v):
        """Validate parameters against pattern specs"""
        # Ensure all color values are integers
        for key in ["red", "green", "blue"]:
            if key in v:
                try:
                    v[key] = int(v[key])
                    if not 0 <= v[key] <= 255:
                        raise ValueError(f"{key} must be between 0 and 255")
                except (TypeError, ValueError):
                    raise ValueError(f"Invalid {key} value: {v[key]}")

        # Set defaults for missing color parameters
        for key in ["red", "green", "blue"]:
            if key not in v:
                v[key] = 255  # Default to full intensity

        return v


class PatternDefinition(BaseModel):
    """Pattern definition using parameter specs"""

    name: str
    category: str
    description: str
    parameters: List[ParameterSpec]


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
    """System performance information"""

    fps: float
    frame_time: float
    avg_frame_time: float
    memory_usage: Optional[float] = None


class SystemState(BaseModel):
    """Current system state"""

    active_pattern: Optional[str]
    pattern_parameters: Optional[Dict[str, Any]]
    active_modifiers: List[str] = []
    modifier_parameters: Dict[str, Any] = {}
    audio_bindings: List[AudioBinding] = []
    performance: Optional[PerformanceMetrics] = None
    is_running: bool


# Registry Models
class PatternRegistry:
    """Registry of available patterns"""

    def __init__(self):
        self._patterns: Dict[str, PatternDefinition] = {}

    def register_pattern(self, pattern: PatternDefinition):
        """Register a pattern definition"""
        self._patterns[pattern.name] = pattern

    def get_pattern(self, name: str) -> Optional[PatternDefinition]:
        """Get pattern by name"""
        return self._patterns.get(name)

    def get_all_patterns(self) -> List[PatternDefinition]:
        """Get all registered patterns"""
        return list(self._patterns.values())


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
