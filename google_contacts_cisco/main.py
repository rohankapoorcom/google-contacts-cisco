"""Main application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ._version import __version__
from .api.contacts import router as contacts_router
from .api.directory_routes import router as directory_router
from .api.google import router as google_router
from .api.routes import router as auth_router
from .api.search_routes import router as search_router
from .api.sync import router as sync_router
from .config import settings
from .config_utils import print_configuration_summary, validate_configuration
from .services.scheduler import start_sync_scheduler, stop_sync_scheduler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get base directory
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static" / "dist"


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

    # Start sync scheduler if configured
    if settings.sync_scheduler_enabled:
        start_sync_scheduler(settings.sync_interval_minutes)
        logger.info(
            "Sync scheduler started (interval: %d minutes)",
            settings.sync_interval_minutes,
        )

    logger.info("Application startup complete")

    yield

    # Shutdown
    # Stop sync scheduler if running
    stop_sync_scheduler()
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS middleware (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]
    if settings.debug
    else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router)
app.include_router(contacts_router)
app.include_router(directory_router)
app.include_router(google_router)
app.include_router(search_router)
app.include_router(sync_router)


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


# Serve Vue static files (production)
# Check if the built frontend exists
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    logger.info("Serving Vue frontend from %s", STATIC_DIR)

    # Mount static assets (JS, CSS, images)
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets_dir)),
            name="assets",
        )

    # Serve index.html for all non-API routes (SPA fallback)
    @app.get("/{full_path:path}")
    async def serve_spa(_request: Request, full_path: str) -> FileResponse:
        """Serve Vue SPA for all non-API routes."""
        # Skip API and other backend routes
        api_prefixes = ("api/", "auth/", "directory/", "health", "docs", "openapi.json")
        if full_path.startswith(api_prefixes):
            # Return 404 for non-existent API routes
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="Not found")

        # Check for static file first (e.g., vite.svg, favicon.ico)
        # Prevent path traversal attacks by resolving and checking path is within STATIC_DIR
        static_file = STATIC_DIR / full_path
        resolved = static_file.resolve()
        try:
            resolved.relative_to(STATIC_DIR)
        except ValueError:
            # Path is outside STATIC_DIR, likely a path traversal attempt
            raise HTTPException(status_code=403, detail="Forbidden")

        if resolved.exists() and resolved.is_file():
            return FileResponse(resolved)

        # Serve index.html for all other routes (SPA routing)
        return FileResponse(STATIC_DIR / "index.html")

else:
    logger.info(
        "Vue frontend not built. "
        "Run 'cd frontend && npm run build' to build the frontend."
    )

    # Root endpoint when frontend is not built
    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint (when frontend is not built)."""
        return {
            "message": f"{settings.app_name} API",
            "version": __version__,
            "docs": "/docs",
            "note": "Frontend not built. Run 'npm run build' in frontend/.",
        }
