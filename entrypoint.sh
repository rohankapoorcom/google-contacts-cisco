#!/bin/sh
set -e

echo "Starting Google Contacts Cisco Directory..."
echo "Running database migrations..."

# Run Alembic migrations
alembic upgrade head

echo "Migrations complete. Starting application..."

# Convert LOG_LEVEL to lowercase for uvicorn (it requires lowercase)
LOG_LEVEL_LOWER=$(echo "${LOG_LEVEL:-info}" | tr '[:upper:]' '[:lower:]')

# Start the application
exec uvicorn google_contacts_cisco.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --log-level "${LOG_LEVEL_LOWER}"
