#!/bin/bash
# Start web server with ASGI for async MCP support

# Exit immediately if a command exits with a non-zero status
set -e

# Run database migrations
echo "Running migrations..."
uv run python manage.py migrate --noinput

# Start web server (uvicorn for ASGI/async support)
echo "Starting server..."
exec uv run uvicorn config.asgi:application --host 0.0.0.0 --port "$PORT"
