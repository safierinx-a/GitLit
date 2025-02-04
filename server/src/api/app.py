from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from typing import Optional

from ..core.config import SystemConfig
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


def init_app(config_updates: dict = None) -> FastAPI:
    """Initialize the FastAPI application with system controller"""
    # Initialize configuration
    config = SystemConfig.create_default()
    if config_updates:
        config.update(config_updates)

    # Initialize system controller
    system_controller = SystemController(config)
    control.init_controller(system_controller)

    # Initialize audio components only if enabled
    global audio_server
    if config.features.audio_enabled:
        # Initialize audio processor and streaming
        audio_processor = AudioProcessor()
        audio_config = AudioStreamConfig(
            sample_rate=44100,  # Default values
            channels=2,
            chunk_size=1024,
            format="float32",
        )
        audio_server = AudioStreamServer(audio_config, audio_processor)

    # Start the system
    system_controller.start()
    return app


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global audio_server
    if audio_server:
        audio_server.stop()
        audio_server = None
