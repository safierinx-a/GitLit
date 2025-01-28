import asyncio
import websockets
import socket
import numpy as np
import json
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
import sounddevice as sd

logger = logging.getLogger(__name__)


@dataclass
class StreamConfig:
    """Audio stream configuration"""

    sample_rate: int = 44100
    channels: int = 2
    chunk_size: int = 1024
    format: str = "float32"
    server_host: str = "localhost"
    udp_port: int = 5000
    ws_port: int = 8000


class AudioStreamClient:
    """Client for streaming audio and receiving real-time updates"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ws_client: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self._stream: Optional[sd.InputStream] = None

    async def start(self):
        """Start audio streaming and WebSocket connection"""
        self.running = True

        # Connect WebSocket
        ws_url = f"ws://{self.config.server_host}:{self.config.ws_port}/ws"
        try:
            self.ws_client = await websockets.connect(ws_url)
            logger.info(f"Connected to WebSocket at {ws_url}")
        except Exception as e:
            logger.error(f"Failed to connect to WebSocket: {e}")
            self.running = False
            return

        # Start audio stream
        try:
            self._stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.format,
                blocksize=self.config.chunk_size,
                callback=self._audio_callback,
            )
            self._stream.start()
            logger.info("Started audio stream")

            # Keep running and handle WebSocket messages
            while self.running:
                try:
                    message = await self.ws_client.recv()
                    await self._handle_ws_message(message)
                except websockets.exceptions.ConnectionClosed:
                    logger.error("WebSocket connection closed")
                    break
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {e}")

        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop streaming and clean up"""
        self.running = False

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if self.ws_client and not self.ws_client.closed:
            asyncio.create_task(self.ws_client.close())

        self.udp_socket.close()

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time, status: sd.CallbackFlags
    ):
        """Handle incoming audio data"""
        if status:
            logger.warning(f"Audio callback status: {status}")

        try:
            # Send audio data via UDP
            self.udp_socket.sendto(
                indata.tobytes(), (self.config.server_host, self.config.udp_port)
            )
        except Exception as e:
            logger.error(f"Failed to send audio data: {e}")

    async def _handle_ws_message(self, message: str):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)

            if data.get("type") == "audio_features":
                # Handle audio features
                features = data.get("data", {})
                # TODO: Use features to update LED patterns
                pass

        except json.JSONDecodeError:
            logger.error("Received invalid JSON message")
        except Exception as e:
            logger.error(f"Error handling message: {e}")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Audio streaming client")
    parser.add_argument("--host", default="localhost", help="Server hostname")
    parser.add_argument("--udp-port", type=int, default=5000, help="UDP port")
    parser.add_argument("--ws-port", type=int, default=8000, help="WebSocket port")
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create client
    config = StreamConfig(
        server_host=args.host, udp_port=args.udp_port, ws_port=args.ws_port
    )
    client = AudioStreamClient(config)

    # Run client
    try:
        asyncio.run(client.start())
    except KeyboardInterrupt:
        logger.info("Stopping client...")
    finally:
        client.stop()


if __name__ == "__main__":
    main()
