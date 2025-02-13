import logging
import sys
from typing import Optional

from fastapi import FastAPI, WebSocket, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import SystemConfig
from ..core.control import SystemController
from ..core.exceptions import ValidationError
from ..core.websocket_manager import manager as ws_manager
from ..core.transactions import TransactionManager
from . import control, websocket

logger = logging.getLogger(__name__)


def init_app(controller: Optional[SystemController] = None) -> FastAPI:
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
    app.state.system_controller = controller
    app.state.startup_complete = controller is not None
    app.state.transaction_manager = (
        TransactionManager() if controller is None else controller.transaction_manager
    )

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

    # Make the dependency available at module level
    app.dependency_overrides[SystemController] = get_controller

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

            # Initialize system controller if not provided
            if app.state.system_controller is None:
                try:
                    app.state.system_controller = SystemController(
                        config, transaction_manager=app.state.transaction_manager
                    )
                    await app.state.system_controller.start()
                    logger.info("System controller started")

                    # Start WebSocket manager
                    await ws_manager.start()
                    logger.info("WebSocket manager started")

                    # Mark startup as complete
                    app.state.startup_complete = True
                    logger.info("Startup complete")

                except Exception as e:
                    logger.error(f"Failed to initialize system: {e}")
                    raise

        except Exception as e:
            logger.error(f"Startup failed: {e}")
            sys.exit(1)

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up system on shutdown"""
        try:
            logger.info("Shutting down GitLit Control API")

            # Stop WebSocket manager
            await ws_manager.stop()
            logger.info("WebSocket manager stopped")

            # Stop system controller
            if app.state.system_controller:
                await app.state.system_controller.stop()
                logger.info("System controller stopped")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise

    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy" if app.state.startup_complete else "starting",
            "controller": app.state.system_controller is not None,
            "patterns_active": app.state.startup_complete
            and app.state.system_controller is not None,
        }

    return app


# Create the application instance
app = init_app()

# This allows running with either app or init_app
__all__ = ["app", "init_app"]
