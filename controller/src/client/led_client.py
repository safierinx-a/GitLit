import asyncio
import json
import logging
import numpy as np
import websockets
from ..led.controller import LEDController

logger = logging.getLogger(__name__)


class LEDClient:
    """Simple WebSocket client that receives frames and displays them"""

    def __init__(self, host: str, port: int, num_pixels: int, pin: int = 18):
        self.uri = f"ws://{host}:{port}/ws"
        self.led_controller = LEDController(num_pixels=num_pixels, pin=pin)
        self.running = True
        logger.info(f"Initialized LED client connecting to {self.uri}")

    async def run(self):
        """Main client loop"""
        while self.running:
            try:
                async with websockets.connect(self.uri) as websocket:
                    logger.info(f"Connected to {self.uri}")

                    while True:
                        try:
                            message = await websocket.recv()
                            await self._handle_message(message)
                        except websockets.ConnectionClosed:
                            logger.warning("WebSocket connection closed")
                            break

            except Exception as e:
                logger.error(f"Connection error: {e}")
                await asyncio.sleep(1)  # Wait before retrying

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)

            if data.get("type") == "pattern":
                pattern_data = data.get("data", {})
                if "frame" in pattern_data:
                    frame = np.array(pattern_data["frame"], dtype=np.uint8)
                    self.led_controller.display_frame(frame)

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        self.led_controller.cleanup()
        logger.info("LED client cleaned up")


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
