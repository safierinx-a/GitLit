"""Atomic state transactions for system state management."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import time

from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class TransactionState(Enum):
    """Transaction states"""

    PENDING = "pending"
    COMMITTING = "committing"
    COMMITTED = "committed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class StateChange:
    """Individual state change within a transaction"""

    path: str  # Dot notation path to state value
    old_value: Any
    new_value: Any
    timestamp: float = field(default_factory=time.time)


@dataclass
class Transaction:
    """Atomic state transaction"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    changes: List[StateChange] = field(default_factory=list)
    state: TransactionState = TransactionState.PENDING
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None

    # Callbacks
    on_commit: Optional[Callable[[], None]] = None
    on_rollback: Optional[Callable[[], None]] = None

    def add_change(self, path: str, old_value: Any, new_value: Any) -> None:
        """Add a state change to the transaction"""
        self.changes.append(StateChange(path, old_value, new_value))

    def get_changes_for_path(self, path: str) -> List[StateChange]:
        """Get all changes for a specific state path"""
        return [c for c in self.changes if c.path.startswith(path)]


class TransactionManager:
    """Manages atomic state transactions"""

    def __init__(self):
        self.active_transaction: Optional[Transaction] = None
        self.transaction_history: List[Transaction] = []
        self.max_history: int = 100
        self._lock = asyncio.Lock()

    async def begin(self) -> Transaction:
        """Begin a new transaction"""
        async with self._lock:
            if self.active_transaction:
                raise ValidationError("Transaction already in progress")

            transaction = Transaction()
            self.active_transaction = transaction
            return transaction

    async def commit(self) -> None:
        """Commit the active transaction"""
        async with self._lock:
            if not self.active_transaction:
                raise ValidationError("No active transaction")

            try:
                self.active_transaction.state = TransactionState.COMMITTING

                # Execute commit callback if exists
                if self.active_transaction.on_commit:
                    self.active_transaction.on_commit()

                self.active_transaction.state = TransactionState.COMMITTED
                self._add_to_history(self.active_transaction)
                self.active_transaction = None

            except Exception as e:
                logger.error(f"Transaction commit failed: {e}")
                await self.rollback()
                raise

    async def rollback(self) -> None:
        """Rollback the active transaction"""
        async with self._lock:
            if not self.active_transaction:
                return

            try:
                self.active_transaction.state = TransactionState.ROLLING_BACK

                # Execute rollback callback if exists
                if self.active_transaction.on_rollback:
                    self.active_transaction.on_rollback()

                self.active_transaction.state = TransactionState.ROLLED_BACK
                self._add_to_history(self.active_transaction)
                self.active_transaction = None

            except Exception as e:
                logger.error(f"Transaction rollback failed: {e}")
                self.active_transaction.state = TransactionState.FAILED
                self.active_transaction.error = str(e)
                self._add_to_history(self.active_transaction)
                self.active_transaction = None
                raise

    def _add_to_history(self, transaction: Transaction) -> None:
        """Add transaction to history, maintaining max size"""
        self.transaction_history.append(transaction)
        if len(self.transaction_history) > self.max_history:
            self.transaction_history.pop(0)

    def get_recent_transactions(self, count: int = 5) -> List[Transaction]:
        """Get most recent transactions"""
        return self.transaction_history[-count:]

    def get_transaction_by_id(self, transaction_id: str) -> Optional[Transaction]:
        """Find transaction by ID"""
        return next(
            (t for t in self.transaction_history if t.id == transaction_id), None
        )


class TransactionContext:
    """Async context manager for transactions"""

    def __init__(self, manager: TransactionManager):
        self.manager = manager
        self.transaction: Optional[Transaction] = None

    async def __aenter__(self) -> Transaction:
        """Start transaction"""
        self.transaction = await self.manager.begin()
        return self.transaction

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Commit or rollback transaction"""
        if exc_type is None:
            await self.manager.commit()
        else:
            await self.manager.rollback()
