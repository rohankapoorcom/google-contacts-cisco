"""Main application entry point."""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI

from ._version import __version__
from .api.google import router as google_router
from .api.routes import router as auth_router
from .config import settings
from .config_utils import print_configuration_summary, validate_configuration

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown events."""
    # Startup
    logger.info("Starting %s v%s", settings.app_name, __version__)
    print_configuration_summary()

    is_valid, errors = validate_configuration()
    if not is_valid:
        logger.warning("Configuration warnings:")
        for error in errors:
            logger.warning("  - %s", error)
        if not settings.debug:
            # In production, log warning but allow app to start
            # The OAuth setup page will guide users to configure credentials
            logger.warning(
                "Google OAuth credentials not configured. "
                "Please complete setup at /setup after starting the application."
            )

    # Ensure required directories exist
    settings.ensure_directories()
    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__,
    debug=settings.debug,
    lifespan=lifespan,
)

# Include API routers
app.include_router(auth_router)
app.include_router(google_router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": f"{settings.app_name} API", "version": __version__}


@app.get("/health")
async def health() -> dict[str, Any]:
    """Health check endpoint."""
    is_valid, errors = validate_configuration()
    return {
        "status": "healthy",
        "version": __version__,
        "debug": settings.debug,
        "config_valid": is_valid,
        "config_errors": errors if not is_valid else [],
    }
