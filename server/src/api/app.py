import logging
import sys
from typing import Optional

from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import SystemConfig
from ..core.control import SystemController
from ..core.exceptions import ValidationError
from . import control, websocket

logger = logging.getLogger(__name__)


def init_app() -> FastAPI:
    """Create and configure the FastAPI application"""
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
    app.state.system_controller = None
    app.state.startup_complete = False

    def get_controller() -> SystemController:
        """Dependency injection for system controller"""
        if not app.state.startup_complete:
            raise HTTPException(
                status_code=503,
                detail="System is still starting up. Please try again in a moment.",
            )
        if app.state.system_controller is None:
            raise HTTPException(
                status_code=503,
                detail="System controller not initialized or has failed",
            )
        return app.state.system_controller

    # Include routers with dependencies
    control.router.dependencies = [Depends(get_controller)]
    websocket.router.dependencies = [Depends(get_controller)]

    # Include routers
    app.include_router(control.router)
    app.include_router(websocket.router)

    @app.on_event("startup")
    async def startup_event():
        """Initialize the system on startup"""
        try:
            logger.info("Starting GitLit Control API")

            # Initialize configuration
            try:
                config = SystemConfig.create_default()
                logger.info("Configuration loaded")
            except Exception as e:
                logger.error(f"Failed to load configuration: {e}")
                sys.exit(1)

            # Validate configuration
            try:
                # TODO: Add configuration validation
                pass
            except ValidationError as e:
                logger.error(f"Invalid configuration: {e}")
                sys.exit(1)

            # Initialize system controller
            try:
                app.state.system_controller = SystemController(config)
                control.init_controller(app.state.system_controller)
                logger.info("System controller initialized")
            except Exception as e:
                logger.error(f"Failed to initialize system controller: {e}")
                raise

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
                    app.state.system_controller.init_audio(audio_processor)
                    logger.info("Audio processing initialized")
                except ImportError:
                    logger.warning("Audio processing modules not available")
                    config.features.audio_enabled = False
                except Exception as e:
                    logger.error(f"Failed to initialize audio: {e}")
                    config.features.audio_enabled = False

            # Start the system
            await app.state.system_controller.start()
            logger.info("System controller started successfully")

            # Mark startup as complete
            app.state.startup_complete = True

        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            # Clean up any partially initialized components
            if app.state.system_controller:
                try:
                    await app.state.system_controller.stop()
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")
                finally:
                    app.state.system_controller = None
            app.state.startup_complete = False
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up resources on shutdown"""
        if app.state.system_controller:
            logger.info("Shutting down GitLit Control API")
            try:
                await app.state.system_controller.stop()
                logger.info("System controller stopped")
            except Exception as e:
                logger.error(f"Error during shutdown: {e}")
            finally:
                app.state.system_controller = None
                app.state.startup_complete = False

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy" if app.state.startup_complete else "starting",
            "controller": app.state.system_controller is not None,
            "patterns_active": app.state.system_controller.is_running
            if app.state.system_controller
            else False,
        }

    return app


# Create the application instance
app = init_app()

# This allows running with either app or init_app
__all__ = ["app", "init_app"]
