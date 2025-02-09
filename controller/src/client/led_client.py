import asyncio
import json
import logging
import signal
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
    led_count: int = 300
    led_pin: int = 18
    led_freq: int = 800000
    brightness: float = 1.0
    reconnect_delay: float = 5.0
    controller_type: str = "direct"  # "direct" or "mock"


class LEDClient:
    """WebSocket client for LED control"""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.ws_client: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.shutdown_event = asyncio.Event()

        # Initialize LED controller
        controller_config = {
            "type": config.controller_type,
            "num_pixels": config.led_count,
            "pin": config.led_pin,
            "freq": config.led_freq,
        }
        self.led_controller = create_controller(controller_config)
        self.led_controller.set_brightness(config.brightness)
        logger.info(
            f"Initialized {config.controller_type} LED controller with {config.led_count} pixels"
        )

    async def start(self):
        """Start WebSocket connection with reconnection handling"""
        self.running = True

        # Setup signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            asyncio.get_event_loop().add_signal_handler(sig, self._signal_handler)

        while self.running and not self.shutdown_event.is_set():
            try:
                await self._connect_and_process()
            except Exception as e:
                logger.error(f"Connection error: {e}")
                if self.running:
                    logger.info(
                        f"Reconnecting in {self.config.reconnect_delay} seconds..."
                    )
                    await asyncio.sleep(self.config.reconnect_delay)

    async def _connect_and_process(self):
        """Handle WebSocket connection and message processing"""
        ws_url = f"ws://{self.config.server_host}:{self.config.ws_port}/ws"

        async with websockets.connect(ws_url) as websocket:
            self.ws_client = websocket
            logger.info(f"Connected to WebSocket at {ws_url}")

            try:
                while self.running and not self.shutdown_event.is_set():
                    message = await websocket.recv()
                    await self._handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed")
            finally:
                self.ws_client = None

    def _signal_handler(self):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal")
        self.shutdown_event.set()
        self.stop()

    def stop(self):
        """Stop client and clean up resources"""
        self.running = False
        if self.led_controller:
            try:
                self.led_controller.cleanup()
            except Exception as e:
                logger.error(f"Error during cleanup: {e}")

    async def _handle_message(self, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            msg_type = data.get("type", "")

            if msg_type == "pattern":
                pattern_data = data.get("data", {})
                if "frame" in pattern_data:
                    self.led_controller.set_pixels(pattern_data["frame"])
                else:
                    logger.warning("Received pattern message without frame data")

            elif msg_type == "brightness":
                brightness = float(data.get("data", {}).get("value", 1.0))
                self.led_controller.set_brightness(brightness)
                logger.debug(f"Updated brightness to {brightness}")

            elif msg_type == "clear":
                self.led_controller.turn_off()
                logger.debug("Cleared LED strip")

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error("Received invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")


async def main():
    """Main entry point with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(description="LED Control Client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server WebSocket port")
    parser.add_argument("--led-count", type=int, default=300, help="Number of LEDs")
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
        await client.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        client.stop()


if __name__ == "__main__":
    asyncio.run(main())
