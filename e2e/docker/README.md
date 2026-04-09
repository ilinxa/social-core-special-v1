# E2E Docker Infrastructure

Isolated Docker stack for E2E testing. Runs on different ports from dev to prevent conflicts.

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `postgres-e2e` | 5433 | PostgreSQL 17 (DB: `backend_core_e2e_db`) |
| `redis-e2e` | 6380 | Redis 7 (cache + channels) |
| `backend-e2e` | 8001 | Django via Daphne ASGI (WebSocket support) |
| `frontend-e2e` | 3001 | Next.js production build |

## Quick Start

```bash
# From project root:
make e2e-up          # Start all services
make e2e-down        # Stop all services
make e2e-reset       # Full reset (drop volumes, rebuild, migrate)
```

## Manual Commands

```bash
# Start stack
docker compose -f e2e/docker/docker-compose.e2e.yml up -d --build

# Check health
curl http://localhost:8001/health/    # Backend
curl http://localhost:3001/           # Frontend

# View logs
docker compose -f e2e/docker/docker-compose.e2e.yml logs -f backend-e2e

# Stop
docker compose -f e2e/docker/docker-compose.e2e.yml down

# Full reset (destroys all data)
docker compose -f e2e/docker/docker-compose.e2e.yml down -v
docker compose -f e2e/docker/docker-compose.e2e.yml up -d --build
```

## Key Design Decisions

- **Daphne** (not gunicorn/runserver): Required for WebSocket chat testing
- **`CELERY_TASK_ALWAYS_EAGER=True`**: No separate Celery worker needed
- **Standalone Next.js build**: Production-like frontend behavior
- **Isolated ports**: Won't conflict with `make dev` (PG:5432, Redis:6379, Backend:8000, Frontend:3000)
