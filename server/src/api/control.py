from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from ..core.control import SystemController

router = APIRouter(prefix="/control", tags=["control"])


# Request/Response Models
class PatternRequest(BaseModel):
    name: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ModifierRequest(BaseModel):
    name: str
    params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class AudioBindingRequest(BaseModel):
    modifier_name: str
    parameter: str
    audio_metric: str
    scale: float = 1.0
    offset: float = 0.0


class BrightnessRequest(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0)


class SystemState(BaseModel):
    pattern: str
    modifiers: List[str]
    performance: Dict[str, float]
    audio: Optional[Dict[str, Any]] = None


class ParameterMetadata(BaseModel):
    """Metadata for a pattern/modifier parameter"""

    type: str  # "float", "int", "color", "bool", etc.
    min: Optional[float] = None
    max: Optional[float] = None
    default: Any = None
    description: Optional[str] = None


class PatternMetadata(BaseModel):
    """Metadata for a pattern"""

    name: str
    description: str
    parameters: Dict[str, ParameterMetadata]
    supported_modifiers: List[str]


class ModifierMetadata(BaseModel):
    """Metadata for a pattern modifier"""

    name: str
    description: str
    parameters: Dict[str, ParameterMetadata]
    supported_audio_metrics: Optional[List[str]] = None


# Global controller instance (will be set during app startup)
_controller: SystemController = None


def init_controller(controller: SystemController):
    """Initialize the global controller instance"""
    global _controller
    _controller = controller


# Endpoints
@router.get("/state", response_model=SystemState)
async def get_system_state():
    """Get current system state"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    return _controller.get_state()


@router.post("/pattern")
async def set_pattern(request: PatternRequest):
    """Set active pattern"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    _controller.set_pattern(request.name, request.params)
    return {"status": "success"}


@router.post("/modifier")
async def toggle_modifier(request: ModifierRequest):
    """Toggle pattern modifier"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    _controller.toggle_modifier(request.name, request.params)
    return {"status": "success"}


@router.post("/brightness")
async def set_brightness(request: BrightnessRequest):
    """Set LED brightness"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    _controller.set_brightness(request.value)
    return {"status": "success"}


@router.post("/audio/bind")
async def add_audio_binding(request: AudioBindingRequest):
    """Add audio parameter binding"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    _controller.add_audio_binding(
        request.modifier_name,
        request.parameter,
        request.audio_metric,
        request.scale,
        request.offset,
    )
    return {"status": "success"}


@router.delete("/audio/bind/{modifier_name}")
async def remove_audio_binding(modifier_name: str):
    """Remove audio parameter binding"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    _controller.remove_audio_binding(modifier_name)
    return {"status": "success"}


@router.get("/patterns", response_model=List[PatternMetadata])
async def get_available_patterns():
    """Get list of available patterns with metadata"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    return _controller.pattern_engine.get_available_patterns()


@router.get("/patterns/{pattern_name}", response_model=PatternMetadata)
async def get_pattern_metadata(pattern_name: str):
    """Get metadata for a specific pattern"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    try:
        return _controller.pattern_engine.get_pattern_metadata(pattern_name)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Pattern '{pattern_name}' not found"
        )


@router.get("/modifiers", response_model=List[ModifierMetadata])
async def get_available_modifiers():
    """Get list of available modifiers with metadata"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    return _controller.pattern_engine.get_available_modifiers()


@router.get("/modifiers/{modifier_name}", response_model=ModifierMetadata)
async def get_modifier_metadata(modifier_name: str):
    """Get metadata for a specific modifier"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    try:
        return _controller.pattern_engine.get_modifier_metadata(modifier_name)
    except KeyError:
        raise HTTPException(
            status_code=404, detail=f"Modifier '{modifier_name}' not found"
        )


@router.get("/audio/metrics", response_model=List[str])
async def get_available_audio_metrics():
    """Get list of available audio metrics for bindings"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    if not _controller.audio_enabled:
        raise HTTPException(status_code=400, detail="Audio processing is not enabled")
    return [
        "volume",
        "beat",
        "onset",
        "spectral_centroid",
        "spectral_rolloff",
        "spectral_flux",
    ]
