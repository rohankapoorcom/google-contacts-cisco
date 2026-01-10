"""Main application entry point."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

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
    description="""
# Google Contacts to Cisco IP Phone Application

A comprehensive web application that syncs Google Contacts and serves them to Cisco IP Phones via XML directory service.

## Features

* **OAuth 2.0 Authentication**: Secure integration with Google Contacts API
* **Automatic Synchronization**: Full and incremental sync support with scheduling
* **REST API**: Complete API for contact management and search
* **Cisco XML Directory**: Three-level hierarchy for Cisco IP Phones
* **Full-Text Search**: Fast contact search by name and phone number
* **Modern Frontend**: Vue 3 web interface for management

## Getting Started

1. **Authenticate**: Complete OAuth flow via `/auth/google`
2. **Sync Contacts**: Trigger sync with `POST /api/sync`
3. **Configure Phones**: Point Cisco phones to `/directory`

## Documentation

* **Interactive Docs**: [/docs](/docs) (Swagger UI)
* **Alternative Docs**: [/redoc](/redoc) (ReDoc)
* **API Guide**: See documentation folder for detailed guides
* **Postman Collection**: Available in docs/postman/

## Support

For issues and questions, check the troubleshooting guide or review application logs.
    """,
    version=__version__,
    debug=settings.debug,
    lifespan=lifespan,
    contact={
        "name": "Google Contacts Cisco Support",
        "url": "https://github.com/rohankapoorcom/google-contacts-cisco",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=[
        {
            "name": "authentication",
            "description": "OAuth 2.0 authentication with Google. Complete the OAuth flow to access Google Contacts API.",
        },
        {
            "name": "contacts",
            "description": "Contact management endpoints. List, search, and retrieve contact information.",
        },
        {
            "name": "synchronization",
            "description": "Sync operations with Google Contacts. Supports full and incremental synchronization.",
        },
        {
            "name": "Cisco Directory",
            "description": "XML directory endpoints for Cisco IP Phones. Provides three-level hierarchy (main → group → contact).",
        },
        {
            "name": "google",
            "description": "Google API integration and connection testing.",
        },
    ],
)

# Proxy headers middleware (for reverse proxy deployments)
# This must be added before other middleware to properly handle X-Forwarded-* headers
if settings.trusted_proxies:
    app.add_middleware(
        ProxyHeadersMiddleware,
        trusted_hosts=settings.trusted_proxies,
    )
    logger.info(
        "Proxy headers middleware enabled - trusting X-Forwarded-* headers from: %s",
        ", ".join(settings.trusted_proxies),
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
        from fastapi import HTTPException

        # Skip API and other backend routes
        api_prefixes = ("api/", "auth/", "directory/", "health", "docs", "openapi.json")
        if full_path.startswith(api_prefixes):
            # Return 404 for non-existent API routes
            raise HTTPException(status_code=404, detail="Not found")

        # Sanitize path to prevent traversal attacks
        # Remove any path components that attempt traversal
        path_parts = [
            part for part in full_path.split("/")
            if part and part not in (".", "..")
        ]
        sanitized_path = "/".join(path_parts)

        # Check for static file first (e.g., vite.svg, favicon.ico)
        # Prevent path traversal attacks with multiple layers of validation
        try:
            static_file = STATIC_DIR / sanitized_path
            # Use strict=True to raise FileNotFoundError if path doesn't exist
            # This prevents symlink-based attacks
            resolved = static_file.resolve(strict=False)

            # Verify the resolved path is within STATIC_DIR
            resolved_static = STATIC_DIR.resolve(strict=True)
            resolved.relative_to(resolved_static)

            # Additional check: ensure no symlinks in the path
            if resolved.exists() and resolved.is_symlink():
                logger.warning(
                    "Blocked symlink access attempt: path=%s, client=%s",
                    full_path,
                    _request.client.host if _request.client else "unknown"
                )
                raise HTTPException(status_code=403, detail="Forbidden")

            if resolved.exists() and resolved.is_file():
                return FileResponse(resolved)

        except (ValueError, OSError) as e:
            # Path is outside STATIC_DIR or invalid - likely a traversal attempt
            logger.warning(
                "Blocked path traversal attempt: path=%s, client=%s, error=%s",
                full_path,
                _request.client.host if _request.client else "unknown",
                str(e)
            )
            raise HTTPException(status_code=403, detail="Forbidden")

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
