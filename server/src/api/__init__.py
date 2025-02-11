"""REST API and WebSocket interfaces for LED control system"""

from .app import app, init_app
from .models import (
    PatternRequest,
    SystemState,
    PatternDefinition,
    TransitionRequest,
    BaseResponse,
    ErrorResponse,
    PatternCategory,
)
from .control import router as control_router
from .websocket import router as websocket_router

__all__ = [
    # Application
    "app",
    "init_app",
    # Routers
    "control_router",
    "websocket_router",
    # Models
    "PatternRequest",
    "SystemState",
    "PatternDefinition",
    "TransitionRequest",
    "BaseResponse",
    "ErrorResponse",
    "PatternCategory",
]
