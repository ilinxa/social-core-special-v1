# Social Media Advertising Platform

A social media advertising platform with business accounts, role-based access control, dynamic forms, transaction workflows, content management, and network features.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.1, Django REST Framework, PostgreSQL 17, Redis 7, Celery |
| Frontend | Next.js 16, React 19, TypeScript 5, Tailwind CSS v4, shadcn/ui |
| Mobile | React Native Expo (planned) |
| Testing | pytest, Vitest, Playwright |
| Infrastructure | Docker, Nginx |

## Monorepo Structure

```
├── backend/          Django REST API
├── frontend/         Next.js web client
├── mobile/           React Native Expo app (planned)
├── docker/           Nginx config, helper scripts
├── e2e/              Playwright end-to-end tests
├── docs/             Descriptions, plans, implementations
├── reviews/          Code review checklists, rules, reports
├── progress/         Feature progress tracking (JSON entries)
├── Makefile          Development commands
├── docker-compose.dev.yml   Dev infrastructure (PostgreSQL + Redis)
└── docker-compose.yml       Production stack
```

## Prerequisites

- Python 3.11+
- Node.js 22+
- Docker and Docker Compose
- Git

## Quick Start

```bash
# 1. Clone the repository
git clone <repository-url>
cd socialmedia_adv_app_v1

# 2. Full setup (install deps, start Docker, migrate, create superuser)
make setup

# 3. Start development server
make dev
```

The backend API runs at `http://localhost:8000`. Frontend runs at `http://localhost:3000`.

## Development Commands

### Backend

| Command | Description |
|---------|-------------|
| `make dev` | Start Django with Docker infrastructure (PostgreSQL + Redis) |
| `make local` | Start Django with SQLite (no Docker, quick prototyping) |
| `make dev-migrate` | Run migrations against Docker PostgreSQL |
| `make dev-shell` | Open Django shell with Docker PostgreSQL |
| `make dev-dbshell` | Open PostgreSQL shell |
| `make dev-worker` | Start Celery worker for async tasks |

### Frontend

```bash
cd frontend
npm install
npm run dev       # Development server (port 3000)
npm run build     # Production build
npm run typecheck # TypeScript checking
```

### Testing

| Command | Description |
|---------|-------------|
| `make test` | Backend unit tests (SQLite, fast) |
| `make test-cov` | Backend tests with coverage report |
| `make test-docker` | Backend tests with Docker PostgreSQL |
| `make test-api` | API integration tests (requires `make dev` running) |
| `cd frontend && npm test` | Frontend unit tests (Vitest) |
| `make e2e` | End-to-end tests (Playwright, headless) |
| `make e2e-ui` | End-to-end tests with interactive UI |

### Code Quality

| Command | Description |
|---------|-------------|
| `make lint` | Run all linters (black, isort, flake8) |
| `make format` | Auto-format code |
| `make check` | Run lint + tests |

## Environment Setup

Copy the example environment files and update values:

```bash
make env-example
```

This creates:
- `.env` from `.env.example` (production variables)
- `.env.dev` from `.env.dev.example` (development variables)

Key environment variables: `DJANGO_SECRET_KEY`, `POSTGRES_*`, `REDIS_URL`, `AWS_*`, `GOOGLE_OAUTH_*`, `APPLE_OAUTH_*`. See `.env.example` for the full list.

## Documentation

Detailed documentation lives in `docs/`:

- `docs/descriptions/` — Feature descriptions and requirements
- `docs/plans/` — Implementation plans
- `docs/implementations/` — Implementation reference docs
- `docs/setup/` — Setup and run mode guides
- `docs/testing/` — Test plans and reports

## License

Proprietary. All rights reserved. See [LICENSE](LICENSE) for details.
