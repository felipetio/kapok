#!/bin/bash
# Start web server with ASGI for async MCP support

# Exit immediately if a command exits with a non-zero status
set -e

# Start web server (uvicorn for ASGI/async support)
exec uvicorn config.asgi:application --host 0.0.0.0 --port "$PORT"
