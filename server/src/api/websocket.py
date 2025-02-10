import asyncio
import json
import logging
from typing import Any, Dict, Set
from weakref import WeakSet

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from ..core.control import SystemController

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            # Use WeakSet to automatically remove dead connections
            self.active_connections: Set[WebSocket] = WeakSet()
            self._lock = asyncio.Lock()
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

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connections with rate limiting"""
        if not self.active_connections:
            return

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
        except Exception as e:
            logger.error(f"Broadcast error: {e}")


# Global singleton connection manager
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    controller: SystemController = Depends(lambda: router.dependencies[0].dependency()),
):
    """WebSocket endpoint for real-time updates"""
    client_id = id(websocket)
    logger.info(f"New connection attempt from client {client_id}")

    try:
        await manager.connect(websocket)
        logger.info(f"Client {client_id} connected successfully")

        # Send initial pattern state
        try:
            await controller.pattern_engine.handle_client_connect(websocket)
            logger.debug(f"Sent initial state to client {client_id}")
        except Exception as e:
            logger.error(f"Failed to send initial state to client {client_id}: {e}")
            return

        while True:
            try:
                # Keep connection alive and handle client messages
                data = await websocket.receive_text()
                message = json.loads(data)

                # Log client messages for debugging
                logger.debug(f"Received message from client {client_id}: {message}")

                # Handle client commands
                msg_type = message.get("type")
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "client_id": client_id})
                elif msg_type == "get_state":
                    # Re-sync client state if requested
                    await controller.pattern_engine.handle_client_connect(websocket)
                else:
                    await websocket.send_json({"status": "ok", "client_id": client_id})

            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from client {client_id}")
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON", "client_id": client_id}
                )
            except WebSocketDisconnect:
                raise
            except Exception as e:
                logger.error(f"Error handling message from client {client_id}: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"Client {client_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        await manager.disconnect(websocket)
        logger.info(f"Cleaned up connection for client {client_id}")
