from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional

from ..core.control import SystemController
from . import control, websocket
from .audio_stream import AudioStreamServer, AudioStreamConfig
from ..audio.processor import AudioProcessor

app = FastAPI(title="GitLit Control API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(control.router)
app.include_router(websocket.router)

# Global instances
audio_server: Optional[AudioStreamServer] = None


def init_app(config: dict) -> FastAPI:
    """Initialize the FastAPI application with system controller"""
    # Initialize system controller
    system_controller = SystemController(config)
    control.init_controller(system_controller)

    # Initialize audio processor and streaming
    audio_processor = AudioProcessor()
    audio_config = AudioStreamConfig(
        sample_rate=config.get("audio", {}).get("sample_rate", 44100),
        channels=config.get("audio", {}).get("channels", 2),
        chunk_size=config.get("audio", {}).get("chunk_size", 1024),
        format=config.get("audio", {}).get("format", "float32"),
    )

    global audio_server
    audio_server = AudioStreamServer(audio_config, audio_processor)

    # Start the system
    system_controller.start()
    return app


@app.on_event("startup")
async def startup_event():
    """Start services on application startup"""
    if audio_server:
        await audio_server.start()


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on application shutdown"""
    if control._controller:
        control._controller.stop()
    if audio_server:
        audio_server.stop()
