# Kapok

Monorepo for Kapok: Django backend + React frontend for managing Brazilian indigenous land data.

## Project Structure

```
kapok/
├── backend/          # Django REST API
│   ├── app/          # Django app (models, views, etc.)
│   ├── config/       # Django settings
│   └── docs/         # Backend documentation
├── frontend/         # React (Vite + TypeScript)
│   ├── src/          # React components
│   └── dist/         # Production build
└── docker-compose.yml
```

## Quick Start

```bash
# Start database services
docker compose up -d

# Backend setup
cd backend
uv sync
cp .env.example .env
uv run python manage.py migrate
uv run python manage.py loaddata fixtures.json

# Frontend setup
cd ../frontend
npm install
```

## Development

**Terminal 1 - Backend (port 8000):**
```bash
cd backend
uv run python manage.py runserver
```

**Terminal 2 - Frontend (port 5173):**
```bash
cd frontend
npm run dev
```

Access the app at http://localhost:3000 (Vite proxies /api to Django)

Django Admin: http://localhost:8000/admin (admin / admin)

## Testing

```bash
# Backend tests
cd backend && uv run pytest

# Frontend build
cd frontend && npm run build
```

## Tech Stack

**Backend:**
- Python 3.13, Django 5.2, PostgreSQL 16, Redis 7

**Frontend:**
- React 18, Vite, TypeScript

## License

GPLv3
