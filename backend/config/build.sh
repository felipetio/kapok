#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Build frontend
echo "Building frontend..."
cd ../frontend
npm ci
npm run build

# Return to backend
cd ../backend

# Apply database migrations
echo "Applying database migrations..."
uv run python manage.py migrate --noinput

# Collect static files for the Django application
echo "Collecting static files..."
uv run python manage.py collectstatic --noinput

echo "Build complete!"
