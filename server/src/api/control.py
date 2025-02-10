from typing import Any, Dict, List, Optional, Union
from enum import Enum
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator

from ..core.control import SystemController
from ..core.exceptions import ValidationError
from ..patterns.base import BasePattern
from .models import (
    PatternRequest,
    ModifierRequest,
    AudioBinding,
    SystemState,
    PatternRegistry,
    ModifierRegistry,
    PerformanceMetrics,
    BaseResponse,
    ErrorResponse,
    PatternDefinition,
    ModifierDefinition,
    PatternCategory,
    ModifierCategory,
    ParameterType,
    ParameterSpec,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["control"])

# Global registries
pattern_registry = PatternRegistry()
modifier_registry = ModifierRegistry()

# Global controller instance (will be set during app startup)
_controller: Optional[SystemController] = None


def init_controller(controller: SystemController):
    """Initialize the global controller instance"""
    global _controller
    _controller = controller
    _register_patterns()
    _register_modifiers()


def _check_controller():
    """Check if controller is initialized"""
    if not _controller:
        raise HTTPException(
            status_code=503,
            detail="System not initialized. Please try again in a moment.",
        )


def _register_patterns():
    """Register available patterns using their specs"""
    patterns = _controller.pattern_engine.get_available_patterns()
    for pattern in patterns:
        pattern_def = PatternDefinition(
            name=pattern["name"],
            category=_determine_category_from_name(pattern["name"]),
            description=pattern["description"],
            parameters=[
                ParameterSpec(
                    name=name,
                    type=param["type"],
                    default=param.get("default"),
                    min_value=param.get("min"),
                    max_value=param.get("max"),
                    description=param.get("description", ""),
                    units=param.get("units", ""),
                )
                for name, param in pattern["parameters"].items()
            ],
        )
        pattern_registry.register_pattern(pattern_def)
        logger.info(f"Registered pattern: {pattern_def.name}")


def _register_modifiers():
    """Register available modifiers from the pattern engine"""
    modifiers = _controller.pattern_engine.get_available_modifiers()
    for modifier in modifiers:
        modifier_def = ModifierDefinition(
            name=modifier["name"],
            category=_determine_modifier_category(modifier["name"]),
            description=modifier["description"],
            parameters=modifier["parameters"],
            supported_audio_metrics=modifier.get("supported_audio_metrics"),
        )
        modifier_registry.register_modifier(modifier_def)


def _determine_category_from_name(pattern_name: str) -> PatternCategory:
    """Determine pattern category based on pattern name"""
    static_patterns = {"solid", "gradient"}
    moving_patterns = {"wave", "rainbow", "chase", "scan"}
    particle_patterns = {"twinkle", "meteor", "breathe"}

    if pattern_name in static_patterns:
        return PatternCategory.STATIC
    elif pattern_name in moving_patterns:
        return PatternCategory.MOVING
    elif pattern_name in particle_patterns:
        return PatternCategory.PARTICLE
    return PatternCategory.OTHER


def _determine_modifier_category(modifier_name: str) -> ModifierCategory:
    """Determine modifier category based on name and characteristics"""
    effect_modifiers = {"brightness", "speed", "direction", "color", "strobe", "fade"}
    audio_modifiers = {"volume", "beat", "spectrum"}
    composite_modifiers = {"multi", "transition", "sequence"}

    if modifier_name in effect_modifiers:
        return ModifierCategory.EFFECT
    elif modifier_name in audio_modifiers:
        return ModifierCategory.AUDIO
    elif modifier_name in composite_modifiers:
        return ModifierCategory.COMPOSITE
    return ModifierCategory.CUSTOM


def _validate_parameters(
    pattern_def: PatternDefinition, params: Dict[str, Any]
) -> Dict[str, Any]:
    """Validate parameters against pattern specs"""
    validated = {}
    for spec in pattern_def.parameters:
        value = params.get(spec.name, spec.default)
        if value is None and spec.default is None:
            raise ValidationError(f"Missing required parameter: {spec.name}")

        # Type validation
        try:
            value = spec.type(value)
        except (ValueError, TypeError):
            raise ValidationError(
                f"Invalid type for {spec.name}: expected {spec.type.__name__}"
            )

        # Range validation
        if spec.min_value is not None and value < spec.min_value:
            raise ValidationError(f"{spec.name} must be >= {spec.min_value}")
        if spec.max_value is not None and value > spec.max_value:
            raise ValidationError(f"{spec.name} must be <= {spec.max_value}")

        validated[spec.name] = value

    return validated


# Endpoints
@router.get("/state", response_model=SystemState)
async def get_system_state():
    """Get current system state"""
    _check_controller()
    try:
        state = await _controller.get_state()

        # Create performance metrics if available
        performance = None
        if "performance" in state:
            performance = PerformanceMetrics(
                fps=state["performance"]["fps"],
                frame_time=state["performance"]["frame_time"],
                avg_frame_time=state["performance"].get("avg_frame_time", 0.0),
                memory_usage=state["performance"].get("memory_usage"),
            )

        return SystemState(
            active_pattern=state.get("pattern"),
            pattern_parameters=state.get("pattern_parameters", {}),
            active_modifiers=state.get("modifiers", []),
            modifier_parameters=state.get("modifier_parameters", {}),
            audio_bindings=state.get("audio_bindings", []),
            performance=performance,
            is_running=state.get("is_running", True),
        )
    except Exception as e:
        logger.error(f"Failed to get system state: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get system state: {str(e)}"
        )


@router.post("/pattern", response_model=BaseResponse)
async def set_pattern(request: PatternRequest):
    """Set active pattern using pattern specs for validation"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")

    try:
        # Get pattern definition
        pattern_def = pattern_registry.get_pattern(request.pattern_name)
        if not pattern_def:
            raise ValidationError(f"Unknown pattern: {request.pattern_name}")

        # Validate parameters against specs
        validated_params = _validate_parameters(pattern_def, request.parameters)

        # Set pattern
        await _controller.set_pattern(request.pattern_name, validated_params)
        logger.info(
            f"Set pattern {request.pattern_name} with params: {validated_params}"
        )

        return BaseResponse(
            status="success",
            message=f"Pattern '{request.pattern_name}' set successfully",
        )

    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to set pattern: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modifier", response_model=BaseResponse)
async def toggle_modifier(request: ModifierRequest):
    """Toggle pattern modifier"""
    _check_controller()
    try:
        # Validate modifier exists
        if request.modifier_name not in modifier_registry.modifiers:
            raise ValidationError(f"Modifier '{request.modifier_name}' not found")

        # Convert parameters to engine format
        engine_params = {}
        for param_name, param in request.parameters.items():
            if param.type == "color":
                engine_params.update(
                    {
                        "red": param.value["red"],
                        "green": param.value["green"],
                        "blue": param.value["blue"],
                    }
                )
            else:
                engine_params[param_name] = param.value

        await _controller.toggle_modifier(request.modifier_name, engine_params)
        return BaseResponse(
            status="success",
            message=f"Modifier '{request.modifier_name}' toggled successfully",
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to toggle modifier: {str(e)}"
        )


@router.get("/patterns", response_model=List[PatternDefinition])
async def get_patterns():
    """Get all available patterns with their specs"""
    if not _controller:
        raise HTTPException(status_code=503, detail="System not initialized")
    return pattern_registry.get_all_patterns()


@router.get("/patterns/{category}", response_model=List[PatternDefinition])
async def get_patterns_by_category(category: PatternCategory):
    """Get patterns in a specific category"""
    _check_controller()
    return [p for p in pattern_registry.get_all_patterns() if p.category == category]


@router.get("/modifiers", response_model=List[ModifierDefinition])
async def get_available_modifiers():
    """Get all available modifiers"""
    _check_controller()
    return list(modifier_registry.modifiers.values())


@router.get("/modifiers/{category}", response_model=List[ModifierDefinition])
async def get_modifiers_by_category(category: ModifierCategory):
    """Get modifiers in a specific category"""
    _check_controller()
    return modifier_registry.get_modifiers_by_category(category)


@router.post("/audio/bind", response_model=BaseResponse)
async def add_audio_binding(binding: AudioBinding):
    """Add audio parameter binding"""
    _check_controller()
    try:
        await _controller.add_audio_binding(
            binding.modifier_name,
            binding.parameter_name,
            binding.metric,
            binding.scale,
            binding.offset,
        )
        return BaseResponse(
            status="success",
            message=f"Audio binding added for '{binding.modifier_name}'",
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add audio binding: {str(e)}"
        )


@router.delete("/audio/bind/{modifier_name}", response_model=BaseResponse)
async def remove_audio_binding(modifier_name: str):
    """Remove audio parameter binding"""
    _check_controller()
    try:
        await _controller.remove_audio_binding(modifier_name)
        return BaseResponse(
            status="success", message=f"Audio binding removed for '{modifier_name}'"
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to remove audio binding: {str(e)}"
        )


@router.post("/modifiers/reset", response_model=BaseResponse)
async def reset_modifiers():
    """Reset all active modifiers"""
    _check_controller()
    try:
        await _controller.reset_modifiers()
        return BaseResponse(
            status="success", message="All modifiers reset successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reset modifiers: {str(e)}"
        )
