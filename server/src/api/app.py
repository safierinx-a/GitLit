import logging
from typing import Optional

from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import SystemConfig
from ..core.control import SystemController
from . import control, websocket

logger = logging.getLogger(__name__)

app = FastAPI(
    title="GitLit Control API",
    description="LED pattern control system",
    version="1.0.0",
)

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


# Include routers
app.include_router(control.router)
app.include_router(websocket.router, dependencies=[Depends(get_controller)])


@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup"""
    global system_controller

    try:
        logger.info("Starting GitLit Control API")

        # Initialize configuration
        config = SystemConfig.create_default()
        logger.info("Configuration loaded")

        # Initialize system controller
        system_controller = SystemController(config)
        control.init_controller(system_controller)
        logger.info("System controller initialized")

        # Initialize audio components only if enabled
        if config.features.audio_enabled:
            try:
                # Import audio components only when needed
                from ..audio.processor import AudioProcessor
                from .audio_stream import AudioStreamConfig

                audio_processor = AudioProcessor()
                audio_config = AudioStreamConfig(
                    sample_rate=config.audio.sample_rate,
                    channels=config.audio.channels,
                    chunk_size=config.audio.chunk_size,
                    format=config.audio.format,
                )
                system_controller.init_audio(audio_processor)
                logger.info("Audio processing initialized")
            except Exception as e:
                logger.error(f"Failed to initialize audio: {e}")
                # Continue without audio support
                config.features.audio_enabled = False

        # Start the system
        await system_controller.start()
        logger.info("System controller started successfully")

    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        # Clean up any partially initialized components
        if system_controller:
            try:
                await system_controller.stop()
            except:
                pass
            system_controller = None
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on shutdown"""
    global system_controller

    if system_controller:
        logger.info("Shutting down GitLit Control API")
        try:
            await system_controller.stop()
            logger.info("System controller stopped")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            system_controller = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "controller": system_controller is not None,
        "patterns_active": system_controller.is_running if system_controller else False,
    }
