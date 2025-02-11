"""Core system components for LED control"""

from .config import SystemConfig, SystemDefaults, FeatureFlags
from .control import SystemController
from .state import SystemState, SystemStateManager
from .commands import CommandQueue, Command, CommandPriority
from .exceptions import ValidationError, PatternError
from .frame_manager import FrameManager, FrameMetrics
from .timing import TimeState, TimingConstraints
from .transactions import TransactionManager, Transaction
from .websocket_manager import WebSocketManager, manager as ws_manager

__all__ = [
    # Configuration
    "SystemConfig",
    "SystemDefaults",
    "FeatureFlags",
    # Control
    "SystemController",
    # State Management
    "SystemState",
    "SystemStateManager",
    # Command System
    "CommandQueue",
    "Command",
    "CommandPriority",
    # Frame Management
    "FrameManager",
    "FrameMetrics",
    # Timing
    "TimeState",
    "TimingConstraints",
    # Transactions
    "TransactionManager",
    "Transaction",
    # WebSocket
    "WebSocketManager",
    "ws_manager",
    # Exceptions
    "ValidationError",
    "PatternError",
]
