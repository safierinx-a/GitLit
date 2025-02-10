import asyncio
import json
import logging
from typing import Set
from weakref import WeakSet

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.active_connections: Set[WebSocket] = WeakSet()
            self._lock = asyncio.Lock()
            self._last_broadcast = 0
            self.min_broadcast_interval = 1 / 60  # 60fps max
            self.initialized = True

    async def connect(self, websocket: WebSocket):
        """Accept and store new connection"""
        try:
            await websocket.accept()
            async with self._lock:
                self.active_connections.add(websocket)
                logger.info(
                    f"Client connected. Total connections: {len(self.active_connections)}"
                )
        except Exception as e:
            logger.error(f"Error accepting connection: {e}")
            raise

    async def disconnect(self, websocket: WebSocket):
        """Remove stored connection"""
        async with self._lock:
            try:
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                    logger.info(
                        f"Client disconnected. Total connections: {len(self.active_connections)}"
                    )
            except Exception as e:
                logger.error(f"Error during disconnect: {e}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connections with rate limiting"""
        if not self.active_connections:
            return

        # Apply rate limiting
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_broadcast
        if time_since_last < self.min_broadcast_interval:
            await asyncio.sleep(self.min_broadcast_interval - time_since_last)

        try:
            # Convert message to JSON once for all clients
            data = json.dumps(message)
            async with self._lock:
                dead_connections = set()
                for connection in self.active_connections:
                    try:
                        await connection.send_text(data)
                    except WebSocketDisconnect:
                        dead_connections.add(connection)
                    except Exception as e:
                        logger.error(f"Failed to send message: {e}")
                        dead_connections.add(connection)

                # Clean up dead connections
                if dead_connections:
                    self.active_connections.difference_update(dead_connections)
                    logger.info(f"Removed {len(dead_connections)} dead connections")

            self._last_broadcast = asyncio.get_event_loop().time()
        except Exception as e:
            logger.error(f"Broadcast error: {e}")


# Global singleton instance
manager = ConnectionManager()
