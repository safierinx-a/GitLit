import asyncio
import json
import logging
import numpy as np
import websockets
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from led.controller import LEDController

logger = logging.getLogger(__name__)


class LEDClient:
    """Simple WebSocket client that receives frames and displays them"""

    def __init__(self, host: str, port: int, num_pixels: int, pin: int = 18):
        self.uri = f"ws://{host}:{port}/ws"
        self.led_controller = LEDController(num_pixels=num_pixels, pin=pin)
        self.running = True
        self.last_heartbeat = 0
        self.frames_received = 0
        logger.info(f"Initialized LED client connecting to {self.uri}")

    async def run(self):
        """Main client loop"""
        retry_delay = 1.0
        max_retry_delay = 30.0

        while self.running:
            try:
                async with websockets.connect(self.uri) as websocket:
                    logger.info(f"Connected to {self.uri}")
                    retry_delay = 1.0  # Reset retry delay on successful connection

                    # Request initial state
                    await websocket.send(json.dumps({"type": "get_state"}))
                    logger.debug("Requested initial state")

                    while True:
                        try:
                            message = await websocket.recv()
                            await self._handle_message(message, websocket)
                        except websockets.ConnectionClosed:
                            logger.warning("WebSocket connection closed")
                            break
                        except Exception as e:
                            logger.error(f"Error handling message: {e}")
                            # Don't break on message handling errors

            except Exception as e:
                logger.error(f"Connection error: {e}")
                await asyncio.sleep(retry_delay)
                retry_delay = min(
                    retry_delay * 2, max_retry_delay
                )  # Exponential backoff

    async def _handle_message(
        self, message: str, websocket: websockets.WebSocketClientProtocol
    ):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "pattern":
                pattern_data = data.get("data", {})
                if "frame" in pattern_data:
                    frame = np.array(pattern_data["frame"], dtype=np.uint8)
                    self.led_controller.display_frame(frame)
                    self.frames_received += 1
                    if self.frames_received % 100 == 0:  # Log every 100 frames
                        logger.info(f"Received {self.frames_received} frames")

            elif msg_type == "heartbeat":
                # Respond to heartbeat
                await websocket.send(json.dumps({"type": "pong"}))
                logger.debug("Heartbeat received and responded")

            elif msg_type == "error":
                error_msg = data.get("data", {}).get("message", "Unknown error")
                logger.error(f"Received error from server: {error_msg}")

            else:
                logger.debug(f"Received message of type: {msg_type}")

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            raise  # Re-raise to let run() handle it

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.led_controller.cleanup()
        logger.info(
            f"LED client cleaned up. Total frames received: {self.frames_received}"
        )


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="LED Control Client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server WebSocket port")
    parser.add_argument("--led-count", type=int, default=600, help="Number of LEDs")
    parser.add_argument("--led-pin", type=int, default=18, help="LED GPIO pin")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create and run client
    client = LEDClient(
        host=args.host,
        port=args.port,
        num_pixels=args.led_count,
        pin=args.led_pin,
    )

    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        client.cleanup()


if __name__ == "__main__":
    main()
