"""Main application entry point."""
from typing import Dict

from fastapi import FastAPI
from ._version import __version__

app = FastAPI(
    title="Google Contacts Cisco Directory",
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__
)


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {"message": "Google Contacts Cisco Directory API"}


@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

