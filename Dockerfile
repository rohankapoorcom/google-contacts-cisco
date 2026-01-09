# Multi-stage Dockerfile for Google Contacts Cisco Directory
# Optimized for production deployment with security and size in mind

# =============================================================================
# Stage 1: Build Frontend (Vue 3 + Vite + TypeScript)
# =============================================================================
FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies (including devDependencies needed for build)
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build frontend for production (override outDir to build in container)
RUN npm run build -- --outDir=dist

# Verify build output
RUN ls -la /frontend/dist && \
    test -f /frontend/dist/index.html || (echo "Frontend build failed!" && exit 1)

# =============================================================================
# Stage 2: Build Python Dependencies
# =============================================================================
FROM python:3.13-slim AS python-builder

WORKDIR /app

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml uv.lock ./
COPY google_contacts_cisco/_version.py ./google_contacts_cisco/

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -e .

# =============================================================================
# Stage 3: Production Image
# =============================================================================
FROM python:3.13-slim

# Build argument for version
ARG VERSION=unknown
ENV APP_VERSION=${VERSION}

LABEL maintainer="Google Contacts Cisco <support@example.com>"
LABEL description="Google Contacts to Cisco IP Phone Directory Service"
LABEL version="${VERSION}"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.source="https://github.com/rohankapoorcom/google-contacts-cisco"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/logs && \
    chown -R appuser:appuser /app

# Copy Python virtual environment from builder
COPY --from=python-builder --chown=appuser:appuser /opt/venv /opt/venv

# Copy application code
COPY --chown=appuser:appuser google_contacts_cisco ./google_contacts_cisco
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini ./

# Copy frontend build from builder
COPY --from=frontend-builder --chown=appuser:appuser /frontend/dist ./google_contacts_cisco/static/dist

# Copy entrypoint script
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # Application defaults
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite:///./data/contacts.db

# Expose application port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
ENTRYPOINT ["/app/entrypoint.sh"]
