import asyncio
import json
import logging
import signal
import time
import threading
import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Any

import websockets

from led.controller import create_controller

logger = logging.getLogger(__name__)


@dataclass
class ClientConfig:
    """LED client configuration"""

    server_host: str = "localhost"
    ws_port: int = 8000
    led_count: int = 600
    led_pin: int = 18
    led_freq: int = 800000
    brightness: float = 1.0
    reconnect_delay: float = 5.0
    controller_type: str = "direct"  # "direct" or "mock"


class LEDClient:
    """WebSocket client for LED control"""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.led_controller = create_controller(
            {"type": "direct", "num_pixels": config.led_count, "pin": config.led_pin}
        )
        self.reconnect_delay = 1.0  # Start with 1 second delay
        self.max_reconnect_delay = 30.0
        self.running = True
        self.last_heartbeat = time.time()
        self.heartbeat_timeout = 15.0  # Seconds before considering connection dead
        self._lock = threading.Lock()

        # Initialize LED controller
        controller_config = {
            "type": config.controller_type,
            "num_pixels": config.led_count,
            "pin": config.led_pin,
            "freq": config.led_freq,
        }
        self.led_controller = create_controller(controller_config)
        # Set initial brightness without updating pixels
        if hasattr(self.led_controller._state, "brightness"):
            self.led_controller._state.brightness = config.brightness
        logger.info(
            f"Initialized {config.controller_type} LED controller with {config.led_count} pixels"
        )

    async def run(self):
        """Main client loop with reconnection"""
        while self.running:
            try:
                uri = f"ws://{self.config.server_host}:{self.config.ws_port}/ws"
                async with websockets.connect(uri) as websocket:
                    self.reconnect_delay = 1.0  # Reset delay on successful connection
                    logger.info(f"Connected to {uri}")

                    # Start heartbeat checker
                    asyncio.create_task(self._check_heartbeat())

                    while True:
                        try:
                            message = await websocket.recv()
                            await self._handle_message(message)
                        except websockets.ConnectionClosed:
                            logger.warning("WebSocket connection closed")
                            break

            except Exception as e:
                logger.error(f"Connection error: {e}")
                await asyncio.sleep(self.reconnect_delay)
                # Exponential backoff
                self.reconnect_delay = min(
                    self.reconnect_delay * 2, self.max_reconnect_delay
                )

    async def _check_heartbeat(self):
        """Monitor connection health via heartbeat"""
        while self.running:
            if time.time() - self.last_heartbeat > self.heartbeat_timeout:
                logger.error("Heartbeat timeout - connection may be dead")
                # Connection will be re-established by main loop
                break
            await asyncio.sleep(1)

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket messages with improved error handling"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "heartbeat":
                self.last_heartbeat = time.time()
                return

            if msg_type == "pattern":
                pattern_data = data.get("data", {})
                if "frame" in pattern_data:
                    # Convert frame data to numpy array
                    frame = np.array(pattern_data["frame"], dtype=np.uint8)
                    self.led_controller.set_pixels(frame)

                # Handle initial pattern config if provided
                if "config" in pattern_data:
                    logger.info(f"Received pattern config: {pattern_data['config']}")

            elif msg_type == "error":
                logger.error(
                    f"Received error from server: {data.get('data', {}).get('message', 'Unknown error')}"
                )

        except json.JSONDecodeError:
            logger.error("Invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

    def cleanup(self):
        """Clean up resources"""
        self.running = False
        if self.led_controller:
            self.led_controller.cleanup()


async def main():
    """Main entry point with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(description="LED Control Client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server WebSocket port")
    parser.add_argument("--led-count", type=int, default=600, help="Number of LEDs")
    parser.add_argument("--led-pin", type=int, default=18, help="LED GPIO pin")
    parser.add_argument("--brightness", type=float, default=1.0, help="LED brightness")
    parser.add_argument(
        "--controller",
        choices=["direct", "mock"],
        default="direct",
        help="Controller type",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    config = ClientConfig(
        server_host=args.host,
        ws_port=args.port,
        led_count=args.led_count,
        led_pin=args.led_pin,
        brightness=args.brightness,
        controller_type=args.controller,
    )

    client = LEDClient(config)
    try:
        await client.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
