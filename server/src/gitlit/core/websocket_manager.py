import asyncio
import logging
from typing import Set, Dict, Any, Optional
import time
import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages WebSocket connections with optimized frame delivery"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._frame_buffer = asyncio.Queue(maxsize=2)
        self._last_heartbeat = 0.0
        self._broadcast_task: Optional[asyncio.Task] = None
        self._running = False

    async def connect(self, websocket: WebSocket) -> None:
        """Handle new WebSocket connection"""
        try:
            await websocket.accept()
            self.active_connections.add(websocket)
            logger.info(
                f"Client connected. Active connections: {len(self.active_connections)}"
            )
        except Exception as e:
            logger.error(f"Failed to accept connection: {e}")
            raise

    async def disconnect(self, websocket: WebSocket) -> None:
        """Handle WebSocket disconnection"""
        try:
            self.active_connections.remove(websocket)
            logger.info(
                f"Client disconnected. Active connections: {len(self.active_connections)}"
            )
        except KeyError:
            pass  # Already removed
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")

    async def broadcast_frame(
        self, frame: np.ndarray, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Non-blocking frame broadcast"""
        if not self.active_connections:
            return

        try:
            # Convert frame to bytes only once
            frame_data = frame.tobytes()

            # Prepare message with optional metadata
            message = {
                "type": "frame",
                "data": {"frame": frame_data, "timestamp": time.time() * 1000},
            }
            if metadata:
                message["data"].update(metadata)

            # Broadcast to all connections concurrently
            await asyncio.gather(
                *(ws.send_bytes(frame_data) for ws in self.active_connections),
                return_exceptions=True,
            )
        except Exception as e:
            logger.error(f"Broadcast error: {e}")

    async def broadcast_message(self, message: Dict[str, Any]) -> None:
        """Broadcast a JSON message to all clients"""
        if not self.active_connections:
            return

        dead_connections = set()
        for websocket in self.active_connections:
            try:
                await websocket.send_json(message)
            except WebSocketDisconnect:
                dead_connections.add(websocket)
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                dead_connections.add(websocket)

        # Clean up dead connections
        for ws in dead_connections:
            await self.disconnect(ws)

    async def start(self) -> None:
        """Start the WebSocket manager"""
        if self._running:
            return

        self._running = True
        self._broadcast_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocket manager started")

    async def stop(self) -> None:
        """Stop the WebSocket manager"""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for ws in self.active_connections.copy():
            try:
                await ws.close()
            except Exception as e:
                logger.error(f"Error closing connection: {e}")

        self.active_connections.clear()
        logger.info("WebSocket manager stopped")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to keep connections alive"""
        while self._running:
            try:
                current_time = time.time()
                if current_time - self._last_heartbeat >= 1.0:  # 1 second heartbeat
                    await self.broadcast_message({"type": "heartbeat"})
                    self._last_heartbeat = current_time
                await asyncio.sleep(0.1)  # Small sleep to prevent CPU overload
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(1.0)  # Longer sleep on error


# Global WebSocket manager instance
manager = WebSocketManager()
