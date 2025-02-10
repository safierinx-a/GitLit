import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends

from ..core.websocket_manager import manager
from ..core.control import SystemController

logger = logging.getLogger(__name__)
router = APIRouter(tags=["websocket"])


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
