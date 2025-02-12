"""Command queue system for managing system operations."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from uuid import uuid4

from .exceptions import ValidationError
from .transactions import TransactionManager, TransactionContext

logger = logging.getLogger(__name__)


class CommandPriority(Enum):
    """Command priority levels"""

    EMERGENCY = 0  # Emergency stops, critical system commands
    HIGH = 1  # Important state changes, error recovery
    NORMAL = 2  # Regular pattern changes, parameter updates
    LOW = 3  # Metrics updates, non-critical operations
    BACKGROUND = 4  # Cleanup, optimization tasks


class CommandStatus(Enum):
    """Command execution status"""

    PENDING = auto()
    VALIDATING = auto()
    EXECUTING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class CommandContext:
    """Context for command execution"""

    transaction_manager: TransactionManager
    state: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class CommandResult:
    """Result of command execution"""

    success: bool
    status: CommandStatus
    error: Optional[str] = None
    changes: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0


T = TypeVar("T")


@dataclass
class Command(Generic[T]):
    """Base command class"""

    id: str = field(default_factory=lambda: str(uuid4()))
    priority: CommandPriority = CommandPriority.NORMAL
    timestamp: float = field(default_factory=time.time)
    status: CommandStatus = CommandStatus.PENDING

    # Validation and execution functions
    validate: Callable[[CommandContext], bool]
    execute: Callable[[CommandContext], T]

    # Optional callbacks
    on_success: Optional[Callable[[T], None]] = None
    on_failure: Optional[Callable[[str], None]] = None

    # Result tracking
    result: Optional[CommandResult] = None

    def __post_init__(self):
        if not callable(self.validate) or not callable(self.execute):
            raise ValidationError("Command must have validate and execute functions")


class CommandQueue:
    """Prioritized command queue with validation"""

    def __init__(self, transaction_manager: TransactionManager):
        self.transaction_manager = transaction_manager
        self.queues: Dict[CommandPriority, asyncio.PriorityQueue] = {
            priority: asyncio.PriorityQueue() for priority in CommandPriority
        }
        self.history: List[Command] = []
        self.max_history = 100
        self._running = False
        self._processor_task: Optional[asyncio.Task] = None
        self._current_command: Optional[Command] = None

    async def enqueue(self, command: Command) -> None:
        """Enqueue a command with priority"""
        await self.queues[command.priority].put((command.timestamp, command))
        logger.debug(f"Enqueued command {command.id} with priority {command.priority}")

    async def start(self) -> None:
        """Start command processing"""
        if self._running:
            return
        self._running = True
        self._processor_task = asyncio.create_task(self._process_commands())
        logger.info("Command queue processor started")

    async def stop(self) -> None:
        """Stop command processing"""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        logger.info("Command queue processor stopped")

    async def _process_commands(self) -> None:
        """Process commands from queues based on priority"""
        while self._running:
            try:
                # Check queues in priority order
                command = await self._get_next_command()
                if command:
                    self._current_command = command
                    await self._execute_command(command)
                    self._add_to_history(command)
                else:
                    await asyncio.sleep(0.1)  # No commands to process

            except asyncio.CancelledError:
                logger.info("Command processor cancelled")
                raise
            except Exception as e:
                logger.error(f"Error processing commands: {e}")
                await asyncio.sleep(1)  # Delay on error

    async def _get_next_command(self) -> Optional[Command]:
        """Get next command from highest priority non-empty queue"""
        for priority in CommandPriority:
            queue = self.queues[priority]
            if not queue.empty():
                _, command = await queue.get()
                return command
        return None

    async def _execute_command(self, command: Command) -> None:
        """Execute a command within a transaction"""
        start_time = time.time()
        try:
            # Create command context
            context = CommandContext(
                transaction_manager=self.transaction_manager,
                state=self._get_current_state(),
            )

            # Validate command
            command.status = CommandStatus.VALIDATING
            if not await self._run_validation(command, context):
                raise ValidationError("Command validation failed")

            # Execute command
            command.status = CommandStatus.EXECUTING
            async with TransactionContext(self.transaction_manager) as transaction:
                result = await self._run_execution(command, context)
                execution_time = time.time() - start_time

                # Record success
                command.status = CommandStatus.COMPLETED
                command.result = CommandResult(
                    success=True,
                    status=CommandStatus.COMPLETED,
                    changes=transaction.changes,
                    execution_time=execution_time,
                )

                # Call success callback
                if command.on_success:
                    command.on_success(result)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Command {command.id} failed: {error_msg}")

            # Record failure
            command.status = CommandStatus.FAILED
            command.result = CommandResult(
                success=False,
                status=CommandStatus.FAILED,
                error=error_msg,
                execution_time=time.time() - start_time,
            )

            # Call failure callback
            if command.on_failure:
                command.on_failure(error_msg)

    async def _run_validation(self, command: Command, context: CommandContext) -> bool:
        """Run command validation"""
        try:
            return await asyncio.get_event_loop().run_in_executor(
                None, command.validate, context
            )
        except Exception as e:
            logger.error(f"Command validation failed: {e}")
            return False

    async def _run_execution(self, command: Command, context: CommandContext) -> Any:
        """Run command execution"""
        return await asyncio.get_event_loop().run_in_executor(
            None, command.execute, context
        )

    def _get_current_state(self) -> Dict[str, Any]:
        """Get current system state for command context"""
        # This should be implemented to return actual system state
        return {}

    def _add_to_history(self, command: Command) -> None:
        """Add command to history, maintaining max size"""
        self.history.append(command)
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_history(self, count: int = None) -> List[Command]:
        """Get command history"""
        if count is None:
            return self.history.copy()
        return self.history[-count:]

    def get_current_command(self) -> Optional[Command]:
        """Get currently executing command"""
        return self._current_command


# Common command implementations
class SetPatternCommand(Command[None]):
    """Command to change the active pattern"""

    def __init__(
        self,
        pattern_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        priority: CommandPriority = CommandPriority.NORMAL,
    ):
        def validate(context: CommandContext) -> bool:
            # Implement pattern validation
            return True

        async def execute(context: CommandContext) -> None:
            async with TransactionContext(context.transaction_manager) as transaction:
                transaction.add_change("pattern.name", None, pattern_name)
                if parameters:
                    transaction.add_change("pattern.parameters", None, parameters)

        super().__init__(priority=priority, validate=validate, execute=execute)


class EmergencyStopCommand(Command[None]):
    """Emergency stop command"""

    def __init__(self):
        def validate(context: CommandContext) -> bool:
            return True  # Emergency stop should always be valid

        async def execute(context: CommandContext) -> None:
            async with TransactionContext(context.transaction_manager) as transaction:
                transaction.add_change("system.state", None, "SHUTTING_DOWN")

        super().__init__(
            priority=CommandPriority.EMERGENCY, validate=validate, execute=execute
        )
