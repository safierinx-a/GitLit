from typing import Optional

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import SystemConfig
from ..core.control import SystemController
from . import control, websocket

app = FastAPI(title="GitLit Control API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
system_controller: Optional[SystemController] = None


def get_controller() -> SystemController:
    """Dependency injection for system controller"""
    if system_controller is None:
        raise RuntimeError("System controller not initialized")
    return system_controller


# Include routers with dependencies
app.include_router(control.router, dependencies=[Depends(get_controller)])
app.include_router(websocket.router)


def init_app(config_updates: dict = None) -> FastAPI:
    """Initialize the FastAPI application with system controller"""
    global system_controller

    # Initialize configuration
    config = SystemConfig.create_default()
    if config_updates:
        config.update(config_updates)

    # Initialize system controller
    system_controller = SystemController(config)
    control.init_controller(system_controller)

    # Initialize audio components only if enabled
    if config.features.audio_enabled:
        # Import audio components only when needed
        from ..audio.processor import AudioProcessor
        from .audio_stream import AudioStreamConfig, AudioStreamServer

        audio_processor = AudioProcessor()
        audio_config = AudioStreamConfig(
            sample_rate=config.audio.sample_rate,
            channels=config.audio.channels,
            chunk_size=config.audio.chunk_size,
            format=config.audio.format,
        )
        system_controller.init_audio(audio_processor)

    # Start the system
    system_controller.start()
    return app


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global system_controller
    if system_controller:
        system_controller.stop()
        system_controller = None
