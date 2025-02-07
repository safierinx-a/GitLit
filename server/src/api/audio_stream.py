import asyncio
import logging
import struct
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

import numpy as np
from fastapi import WebSocket

from ..audio.processor import AudioProcessor
from .websocket import manager as ws_manager

logger = logging.getLogger(__name__)


@dataclass
class AudioStreamConfig:
    """Configuration for audio streaming"""

    sample_rate: int = 44100
    channels: int = 2
    chunk_size: int = 1024
    format: str = "float32"  # or int16


class AudioStreamServer:
    """UDP server for receiving audio streams"""

    def __init__(self, config: AudioStreamConfig, audio_processor: AudioProcessor):
        self.config = config
        self.audio_processor = audio_processor
        self.transport: Optional[asyncio.DatagramTransport] = None
        self._lock = asyncio.Lock()

        # Calculate packet size based on format
        self.bytes_per_sample = 4 if config.format == "float32" else 2
        self.packet_size = config.chunk_size * config.channels * self.bytes_per_sample

    async def start(self, host: str = "0.0.0.0", port: int = 5000):
        """Start the UDP server"""
        loop = asyncio.get_running_loop()

        try:
            self.transport, _ = await loop.create_datagram_endpoint(
                lambda: AudioStreamProtocol(self), local_addr=(host, port)
            )
            logger.info(f"Audio stream server listening on {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to start audio stream server: {e}")
            raise

    def stop(self):
        """Stop the UDP server"""
        if self.transport:
            self.transport.close()
            self.transport = None

    async def process_audio_chunk(self, data: bytes):
        """Process received audio data"""
        try:
            # Convert bytes to numpy array based on format
            if self.config.format == "float32":
                samples = np.frombuffer(data, dtype=np.float32)
            else:
                samples = (
                    np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                )

            # Reshape if stereo
            if self.config.channels == 2:
                samples = samples.reshape(-1, 2)

            # Process audio
            features = self.audio_processor.process(samples)

            # Broadcast features via WebSocket
            await ws_manager.broadcast(
                {
                    "type": "audio_features",
                    "data": {
                        "volume": float(features.volume),
                        "beat": bool(features.beat_detected),
                        "onset": bool(features.onset_detected),
                        "spectral": {
                            "centroid": float(features.spectral_centroid),
                            "rolloff": float(features.spectral_rolloff),
                            "flux": float(features.spectral_flux),
                        },
                    },
                }
            )

        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")


class AudioStreamProtocol(asyncio.DatagramProtocol):
    """Protocol for handling UDP audio stream packets"""

    def __init__(self, server: AudioStreamServer):
        self.server = server
        self.transport: Optional[asyncio.DatagramTransport] = None

    def connection_made(self, transport: asyncio.DatagramTransport):
        """Called when connection is established"""
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        """Called when UDP packet is received"""
        if len(data) != self.server.packet_size:
            logger.warning(
                f"Received packet with incorrect size: {len(data)} != {self.server.packet_size}"
            )
            return

        # Process audio data asynchronously
        asyncio.create_task(self.server.process_audio_chunk(data))

    async def handle_audio_stream(self, websocket: WebSocket):
        """Handle incoming audio stream from client"""
        try:
            await websocket.accept()
            self.active_connections.append(websocket)

            while True:
                try:
                    # Receive audio data from client
                    data = await websocket.receive_bytes()

                    # Process audio data
                    self.processor.process_audio_data(
                        np.frombuffer(data, dtype=np.float32)
                    )

                except Exception as e:
                    print(f"Error processing audio data: {e}")
                    break

        except Exception as e:
            print(f"WebSocket connection error: {e}")

        finally:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
