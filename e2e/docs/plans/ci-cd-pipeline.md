# CI/CD Pipeline

> E2E test automation via GitHub Actions. Three tiers: PR, Main, Nightly.

## Pipeline Tiers

| Tier | Trigger | Tests | Budget | Gate |
|------|---------|-------|--------|------|
| **PR** | Pull request to main/develop | L1 Smoke (desktop) | <5 min | Must pass to merge |
| **Main** | Push to main/develop | L1 Smoke + L2 Workflows | <20 min | Alert on failure |
| **Nightly** | Cron 2:00 AM UTC daily | L1 + L2 + L3 (all layers) | <60 min | Full report |

---

## Workflow Files

| File | Trigger | Description |
|------|---------|-------------|
| `.github/workflows/e2e.yml` | PR + push | L1 smoke (always) + L2 workflows (push only) |
| `.github/workflows/e2e-nightly.yml` | Cron + manual dispatch | Full suite: L1 desktop + L1 mobile + L2 + L3 |
| `e2e/docker/docker-compose.ci.yml` | N/A (compose override) | CI-specific Docker overrides |

---

## Architecture

### PR Pipeline (e2e.yml — `smoke-tests` job)

```
checkout → docker compose up → health checks → install deps → playwright install chromium
  → npx playwright test --project=smoke-desktop
  → upload artifacts → docker compose down
```

- **Timeout**: 8 minutes
- **Concurrency**: Cancels in-progress runs for the same PR
- **Path filter**: Only triggers on changes to `backend/`, `frontend/`, `e2e/`, or the workflow itself
- **Workers**: 2 (CI override from 4 local)
- **Retries**: 1

### Main Pipeline (e2e.yml — `workflow-tests` job)

```
(same setup as smoke-tests)
  → npx playwright test --project=workflows
  → upload artifacts → docker compose down
```

- **Timeout**: 22 minutes
- **Depends on**: `smoke-tests` job (runs sequentially after L1 passes)
- **Condition**: `github.event_name == 'push'` only (not on PR)
- **Workers**: 1 (CI override from 2 local)
- **Retries**: 2

### Nightly Pipeline (e2e-nightly.yml)

```
checkout → docker compose up → health checks → install deps → playwright install chromium
  → L1 Smoke (Desktop)
  → L1 Smoke (Mobile)    [if: always()]
  → L2 Workflows          [if: always()]
  → L3 Scenarios           [if: always()]
  → upload artifacts → docker compose down
```

- **Timeout**: 60 minutes total
- **Schedule**: `cron: '0 2 * * *'` (2:00 AM UTC daily)
- **Manual trigger**: `workflow_dispatch` enabled
- **All steps**: `if: always()` — continues through all layers even if earlier layers fail
- **Artifact retention**: 30 days (vs 14 for PR/Main)

---

## Docker Stack (E2E-Isolated)

| Service | Port | Purpose |
|---------|------|---------|
| `postgres-e2e` | 5433 | E2E-isolated PostgreSQL database |
| `redis-e2e` | 6380 | E2E-isolated cache/channels |
| `backend-e2e` | 8001 | Django ASGI via Daphne (WebSocket support) |
| `frontend-e2e` | 3001 | Next.js production build |

Ports are different from development (5432/6379/8000/3000) to prevent conflicts.

---

## Environment Variables

```yaml
E2E_BASE_URL: http://localhost:3001
E2E_API_URL: http://localhost:8001/api/v1
E2E_WS_URL: ws://localhost:8001/ws
E2E_DB_HOST: localhost
E2E_DB_PORT: "5433"
E2E_DB_NAME: backend_core_e2e_db
E2E_DB_USER: django_user
E2E_DB_PASSWORD: django_password
```

---

## Health Checks

Both pipelines wait up to 150 seconds (30 attempts x 5s) for each service:

```bash
# Backend
curl -sf http://localhost:8001/health/

# Frontend
curl -sf http://localhost:3001/
```

If either fails, Docker logs are printed before the job exits with failure.

---

## Artifacts

| Pipeline | Artifact Name Pattern | Retention | Contents |
|----------|-----------------------|-----------|----------|
| PR | `e2e-smoke-report-{pr_number}` | 14 days | `reports/` + `test-results/` |
| Main | `e2e-workflow-report-{run_number}` | 14 days | `reports/` + `test-results/` |
| Nightly | `e2e-nightly-report-{run_number}` | 30 days | `reports/` + `test-results/` |

Artifacts include:
- Playwright HTML report (`reports/`)
- Screenshots on failure
- Video recordings (L2 on first retry, L3 always)
- Trace files (on first retry)

---

## Configuration Overrides (CI vs Local)

| Setting | Local | CI |
|---------|-------|-----|
| L1 Workers | 4 (desktop) / 2 (mobile) | 2 / 1 |
| L2 Workers | 2 | 1 |
| L3 Workers | 1 (serial) | 1 (serial) |
| L1 Retries | 0 | 1 |
| L2 Retries | 0 | 2 |
| L3 Retries | 0 | 0 |
| Video | Off (L1/L2), On (L3) | On first retry (L1/L2), On (L3) |
| Trace | Off | On first retry |
