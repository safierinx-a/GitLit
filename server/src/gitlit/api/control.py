from typing import Any, Dict, List, Optional, Union
import logging

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, validator

from ..core.control import SystemController
from ..core.exceptions import ValidationError
from ..common.patterns import PatternCategory, determine_pattern_category
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
    Parameter,
    ModifierCategory,
    TransitionRequest,
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


async def _register_patterns():
    """Register available patterns using engine metadata"""
    try:
        patterns = await _controller.pattern_engine.get_available_patterns()
        for pattern in patterns:
            pattern_def = PatternDefinition(
                name=pattern["name"],
                category=determine_pattern_category(pattern["name"]),
                description=pattern["description"],
                parameters=[
                    Parameter(
                        name=name,
                        type=param["type"],
                        default=param.get("default"),
                        min_value=param.get("min_value"),
                        max_value=param.get("max_value"),
                        description=param.get("description", ""),
                        units=param.get("units", ""),
                    )
                    for name, param in pattern["parameters"].items()
                ],
                supports_audio=pattern.get("supports_audio", False),
                supports_transitions=pattern.get("supports_transitions", True),
            )
            pattern_registry.register_pattern(pattern_def)
            logger.info(f"Registered pattern: {pattern_def.name}")
    except Exception as e:
        logger.error(f"Failed to register patterns: {e}")
        raise


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


def _determine_modifier_category(modifier_name: str) -> ModifierCategory:
    """Determine modifier category based on name"""
    effect_modifiers = {"brightness", "speed", "direction", "color", "mirror"}
    audio_modifiers = {"beat", "spectrum", "frequency"}
    composite_modifiers = {"stack", "blend", "sequence"}

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

    # Check for unknown parameters
    unknown_params = set(params.keys()) - {spec.name for spec in pattern_def.parameters}
    if unknown_params:
        raise ValidationError(f"Unknown parameters: {', '.join(unknown_params)}")

    for spec in pattern_def.parameters:
        value = params.get(spec.name, spec.default)

        # Required parameter check
        if value is None and spec.default is None:
            raise ValidationError(f"Missing required parameter: {spec.name}")

        # Skip validation if using default value
        if value is None:
            validated[spec.name] = spec.default
            continue

        # Type validation with detailed error message
        try:
            if spec.type == "color":
                if not isinstance(value, dict) or not all(
                    k in value for k in ["red", "green", "blue"]
                ):
                    raise ValidationError(
                        f"Invalid color format for {spec.name}. Expected {{red, green, blue}} dict"
                    )
                validated[spec.name] = value
            else:
                value = spec.type(value)
                validated[spec.name] = value
        except (ValueError, TypeError):
            raise ValidationError(
                f"Invalid type for {spec.name}: expected {spec.type}, got {type(value).__name__}"
            )

        # Range validation with units in error message
        if spec.min_value is not None and value < spec.min_value:
            units_str = f" {spec.units}" if spec.units else ""
            raise ValidationError(f"{spec.name} must be >= {spec.min_value}{units_str}")
        if spec.max_value is not None and value > spec.max_value:
            units_str = f" {spec.units}" if spec.units else ""
            raise ValidationError(f"{spec.name} must be <= {spec.max_value}{units_str}")

    return validated


# Endpoints
@router.get("/state", response_model=SystemState)
async def get_system_state():
    """Get current system state"""
    _check_controller()
    try:
        # Get comprehensive state
        state = await _controller.get_state()
        pattern_state = _controller.pattern_engine.get_current_pattern_state()

        # Create performance metrics
        performance = PerformanceMetrics(
            fps=state["frame_manager"]["actual_fps"],
            frame_time=state["frame_manager"]["avg_frame_time_ms"],
            frame_count=pattern_state["frame_count"],
            dropped_frames=state["frame_manager"]["dropped_frames"],
            buffer_usage=state["frame_manager"]["buffer_usage"],
        )

        return SystemState(
            active_pattern=pattern_state["name"],
            pattern_parameters=pattern_state["parameters"],
            transition_state={
                "active": pattern_state["transition"]["active"],
                "progress": pattern_state["transition"]["progress"],
                "source": pattern_state["transition"]["source"],
                "target": pattern_state["transition"]["target"],
            },
            performance=performance,
            is_running=state["system_state"] == "RUNNING",
        )

    except Exception as e:
        logger.error(f"Failed to get system state: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get system state: {str(e)}"
        )


@router.get("/patterns", response_model=List[PatternDefinition])
async def get_available_patterns(
    category: Optional[PatternCategory] = Query(
        None, description="Filter patterns by category"
    ),
):
    """Get available patterns with optional category filter"""
    _check_controller()
    patterns = pattern_registry.get_all_patterns()
    if category:
        patterns = [p for p in patterns if p.category == category]
    return patterns


@router.get("/patterns/{pattern_name}", response_model=PatternDefinition)
async def get_pattern_info(pattern_name: str):
    """Get detailed pattern information"""
    _check_controller()
    pattern_info = await _controller.pattern_engine.get_pattern_info(pattern_name)
    if not pattern_info:
        raise HTTPException(status_code=404, detail=f"Pattern {pattern_name} not found")
    return PatternDefinition(**pattern_info)


@router.post("/patterns/{pattern_name}", response_model=BaseResponse)
async def set_pattern(
    pattern_name: str,
    request: PatternRequest,
    transition: Optional[TransitionRequest] = None,
):
    """Set active pattern with optional transition"""
    _check_controller()
    try:
        # Get pattern definition
        pattern_def = pattern_registry.get_pattern(pattern_name)
        if not pattern_def:
            raise ValidationError(f"Unknown pattern: {pattern_name}")

        # Validate parameters
        validated_params = _validate_parameters(pattern_def, request.parameters)

        # Prepare transition if specified
        transition_params = None
        if transition and pattern_def.supports_transitions:
            transition_params = {
                "type": transition.type,
                "duration_ms": transition.duration_ms,
            }

        # Set pattern
        await _controller.set_pattern(
            pattern_name, validated_params, transition=transition_params
        )

        return BaseResponse(
            status="success", message=f"Pattern '{pattern_name}' set successfully"
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
