from typing import Any, Dict, List, Optional, Union
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator

from ..core.control import SystemController
from ..core.exceptions import ValidationError

router = APIRouter(prefix="/control", tags=["control"])


class ColorValue(BaseModel):
    """RGB color value"""

    red: int = Field(0, ge=0, le=255)
    green: int = Field(0, ge=0, le=255)
    blue: int = Field(0, ge=0, le=255)


class Position(BaseModel):
    """Position value"""

    value: float = Field(..., ge=0.0, le=1.0)


class Speed(BaseModel):
    """Speed value"""

    value: float = Field(1.0, gt=0.0)


class Brightness(BaseModel):
    """Brightness value"""

    value: float = Field(..., ge=0.0, le=1.0)


class PatternType(str, Enum):
    """Available pattern types"""

    SOLID = "solid"
    GRADIENT = "gradient"
    WAVE = "wave"
    RAINBOW = "rainbow"
    CHASE = "chase"
    SCAN = "scan"
    TWINKLE = "twinkle"
    METEOR = "meteor"
    BREATHE = "breathe"


class PatternParameters(BaseModel):
    """Base pattern parameters"""

    color: Optional[ColorValue] = None
    color1: Optional[ColorValue] = None
    color2: Optional[ColorValue] = None
    speed: Optional[float] = Field(None, gt=0.0)
    brightness: Optional[float] = Field(None, ge=0.0, le=1.0)
    position: Optional[float] = Field(None, ge=0.0, le=1.0)

    @validator("speed")
    def validate_speed(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Speed must be greater than 0")
        return v


class PatternRequest(BaseModel):
    """Pattern request with validated type and parameters"""

    pattern: PatternType
    params: PatternParameters = Field(default_factory=PatternParameters)


class ModifierType(str, Enum):
    """Available modifier types"""

    BLINK = "blink"
    FADE = "fade"
    PULSE = "pulse"
    SPARKLE = "sparkle"
    AUDIO = "audio"


class ModifierParameters(BaseModel):
    """Base modifier parameters"""

    speed: Optional[float] = Field(None, gt=0.0)
    intensity: Optional[float] = Field(None, ge=0.0, le=1.0)
    color: Optional[ColorValue] = None
    enabled: bool = True


class ModifierRequest(BaseModel):
    """Modifier request with validated type and parameters"""

    name: ModifierType
    params: ModifierParameters = Field(default_factory=ModifierParameters)


class AudioMetricType(str, Enum):
    """Available audio metrics"""

    VOLUME = "volume"
    BEAT = "beat"
    ONSET = "onset"
    SPECTRAL_CENTROID = "spectral_centroid"
    SPECTRAL_ROLLOFF = "spectral_rolloff"
    SPECTRAL_FLUX = "spectral_flux"


class AudioBindingRequest(BaseModel):
    """Audio binding request"""

    modifier_name: ModifierType
    parameter: str
    audio_metric: AudioMetricType
    scale: float = Field(1.0, gt=0.0)
    offset: float = Field(0.0)


class BrightnessRequest(BaseModel):
    """Brightness control request"""

    value: float = Field(..., ge=0.0, le=1.0)


class PerformanceMetrics(BaseModel):
    """Performance metrics"""

    fps: float
    frame_time: float
    avg_frame_time: float


class AudioState(BaseModel):
    """Audio processing state"""

    enabled: bool
    active_bindings: List[AudioBindingRequest] = []


class SystemState(BaseModel):
    """Complete system state"""

    pattern: PatternType
    active_modifiers: List[ModifierType] = []
    performance: PerformanceMetrics
    audio: Optional[AudioState] = None
    brightness: float = Field(1.0, ge=0.0, le=1.0)


class ParameterMetadata(BaseModel):
    """Parameter metadata"""

    type: str
    min: Optional[float] = None
    max: Optional[float] = None
    default: Any = None
    description: Optional[str] = None
    units: Optional[str] = None


class PatternMetadata(BaseModel):
    """Pattern metadata"""

    name: PatternType
    description: str
    parameters: Dict[str, ParameterMetadata]
    supported_modifiers: List[ModifierType]


class ModifierMetadata(BaseModel):
    """Modifier metadata"""

    name: ModifierType
    description: str
    parameters: Dict[str, ParameterMetadata]
    supported_audio_metrics: Optional[List[AudioMetricType]] = None


# Global controller instance (will be set during app startup)
_controller: SystemController = None


def init_controller(controller: SystemController):
    """Initialize the global controller instance"""
    global _controller
    _controller = controller


def _check_controller():
    """Check if controller is initialized"""
    if not _controller:
        raise HTTPException(
            status_code=503,
            detail="System not initialized. Please try again in a moment.",
        )


# Endpoints
@router.get("/state", response_model=SystemState)
async def get_system_state():
    """Get current system state"""
    _check_controller()
    try:
        state = _controller.get_state()
        return SystemState(
            pattern=state["pattern"],
            active_modifiers=state["modifiers"],
            performance=PerformanceMetrics(
                fps=state["performance"]["fps"],
                frame_time=state["performance"]["frame_time"],
                avg_frame_time=state["performance"].get("avg_frame_time", 0.0),
            ),
            audio=AudioState(
                enabled=state["audio"]["enabled"],
                active_bindings=state["audio"].get("bindings", []),
            )
            if state.get("audio")
            else None,
            brightness=_controller.config.led.brightness,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get system state: {str(e)}"
        )


@router.post("/pattern")
async def set_pattern(request: PatternRequest):
    """Set active pattern with validated parameters"""
    _check_controller()
    try:
        # Convert the structured parameters to dict format expected by controller
        params = request.params.dict(exclude_none=True)
        if "color" in params:
            params["color"] = params["color"].dict()
        if "color1" in params:
            params["color1"] = params["color1"].dict()
        if "color2" in params:
            params["color2"] = params["color2"].dict()

        await _controller.set_pattern(request.pattern.value, params)
        return {
            "status": "success",
            "message": f"Pattern {request.pattern.value} set successfully",
        }
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to set pattern: {str(e)}")


@router.post("/modifier")
async def toggle_modifier(request: ModifierRequest):
    """Toggle pattern modifier with validated parameters"""
    _check_controller()
    try:
        params = request.params.dict(exclude_none=True)
        if "color" in params:
            params["color"] = params["color"].dict()

        await _controller.toggle_modifier(request.name.value, params)
        return {
            "status": "success",
            "message": f"Modifier {request.name.value} toggled successfully",
        }
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to toggle modifier: {str(e)}"
        )


@router.post("/brightness")
async def set_brightness(request: BrightnessRequest):
    """Set LED brightness with validation"""
    _check_controller()
    try:
        await _controller.set_brightness(request.value)
        return {"status": "success", "message": f"Brightness set to {request.value}"}
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to set brightness: {str(e)}"
        )


@router.post("/audio/bind")
async def add_audio_binding(request: AudioBindingRequest):
    """Add audio parameter binding with validation"""
    _check_controller()
    try:
        await _controller.add_audio_binding(
            request.modifier_name.value,
            request.parameter,
            request.audio_metric.value,
            request.scale,
            request.offset,
        )
        return {
            "status": "success",
            "message": f"Audio binding added for {request.modifier_name.value}",
        }
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add audio binding: {str(e)}"
        )


@router.delete("/audio/bind/{modifier_name}")
async def remove_audio_binding(modifier_name: ModifierType):
    """Remove audio parameter binding"""
    _check_controller()
    try:
        await _controller.remove_audio_binding(modifier_name.value)
        return {
            "status": "success",
            "message": f"Audio binding removed for {modifier_name.value}",
        }
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to remove audio binding: {str(e)}"
        )


@router.get("/patterns", response_model=List[PatternMetadata])
async def get_available_patterns():
    """Get list of available patterns with metadata"""
    _check_controller()
    try:
        patterns = _controller.pattern_engine.get_available_patterns()
        return [
            PatternMetadata(
                name=PatternType(pattern["name"]),
                description=pattern["description"],
                parameters=pattern["parameters"],
                supported_modifiers=[
                    ModifierType(m) for m in pattern["supported_modifiers"]
                ],
            )
            for pattern in patterns
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get available patterns: {str(e)}"
        )


@router.get("/patterns/{pattern_name}", response_model=PatternMetadata)
async def get_pattern_metadata(pattern_name: PatternType):
    """Get metadata for a specific pattern"""
    _check_controller()
    try:
        pattern = _controller.pattern_engine.get_pattern_metadata(pattern_name.value)
        return PatternMetadata(
            name=PatternType(pattern["name"]),
            description=pattern["description"],
            parameters=pattern["parameters"],
            supported_modifiers=[
                ModifierType(m) for m in pattern["supported_modifiers"]
            ],
        )
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Pattern '{pattern_name}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get pattern metadata: {str(e)}"
        )


@router.get("/modifiers", response_model=List[ModifierMetadata])
async def get_available_modifiers():
    """Get list of available modifiers with metadata"""
    _check_controller()
    try:
        modifiers = _controller.pattern_engine.get_available_modifiers()
        return [
            ModifierMetadata(
                name=ModifierType(modifier["name"]),
                description=modifier["description"],
                parameters=modifier["parameters"],
                supported_audio_metrics=[
                    AudioMetricType(m) for m in modifier["supported_audio_metrics"]
                ]
                if modifier.get("supported_audio_metrics")
                else None,
            )
            for modifier in modifiers
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get available modifiers: {str(e)}"
        )


@router.get("/modifiers/{modifier_name}", response_model=ModifierMetadata)
async def get_modifier_metadata(modifier_name: ModifierType):
    """Get metadata for a specific modifier"""
    _check_controller()
    try:
        modifier = _controller.pattern_engine.get_modifier_metadata(modifier_name.value)
        return ModifierMetadata(
            name=ModifierType(modifier["name"]),
            description=modifier["description"],
            parameters=modifier["parameters"],
            supported_audio_metrics=[
                AudioMetricType(m) for m in modifier["supported_audio_metrics"]
            ]
            if modifier.get("supported_audio_metrics")
            else None,
        )
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Modifier '{modifier_name}' not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get modifier metadata: {str(e)}"
        )


@router.get("/audio/metrics", response_model=List[AudioMetricType])
async def get_available_audio_metrics():
    """Get list of available audio metrics for bindings"""
    _check_controller()
    if not _controller.audio_enabled:
        raise HTTPException(status_code=400, detail="Audio processing is not enabled")
    return list(AudioMetricType)


@router.post("/modifiers/reset")
async def reset_modifiers():
    """Reset all active modifiers to their default state"""
    _check_controller()
    try:
        await _controller.reset_modifiers()
        return {"status": "success", "message": "All modifiers reset successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset modifiers: {str(e)}"
        )
