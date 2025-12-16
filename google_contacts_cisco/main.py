"""Main application entry point."""
from fastapi import FastAPI
from ._version import __version__

app = FastAPI(
    title="Google Contacts Cisco Directory",
    description="Web application for syncing Google Contacts to Cisco IP Phones",
    version=__version__
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Google Contacts Cisco Directory API"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

