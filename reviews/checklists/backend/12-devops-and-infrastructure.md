# 12 — DevOps & Infrastructure Checklist

## 12.1 Docker & Containerization

- [ ] A **`Dockerfile`** exists at the project root — single, well-structured, production-ready
- [ ] **Multi-stage build** is used — separate `builder` and `runtime` stages, build tools absent from final image
- [ ] Base image is **pinned to a specific digest** — `python:3.12.3-slim-bookworm@sha256:...` not a mutable tag
- [ ] **Slim or Alpine base image** is used — not full `python:3.12` with unnecessary system packages
- [ ] Application runs as a **non-root user** — `USER appuser` defined and applied before `CMD`
- [ ] Non-root user is created explicitly — `RUN addgroup --system app && adduser --system --ingroup app appuser`
- [ ] **`WORKDIR`** is set explicitly — `/app` or `/srv/app`, not defaulting to root `/`
- [ ] **`.dockerignore`** exists and is comprehensive — excludes `.git`, `__pycache__`, `.env`, `node_modules`, test files
- [ ] Only **necessary files are copied** into the image — no `COPY . .` without a proper `.dockerignore`
- [ ] **Dependency installation is cached** in a separate layer — `COPY requirements.txt .` → `RUN pip install` → `COPY . .`
- [ ] **`pip install --no-cache-dir`** is used — reducing image size
- [ ] **System packages** installed via `apt-get` are cleaned up in the same `RUN` layer — no dangling cache
- [ ] **`CMD`** uses exec form — `CMD ["gunicorn", "config.wsgi"]` not shell form `CMD gunicorn config.wsgi`
- [ ] **`EXPOSE`** documents the port the app listens on — informational but present
- [ ] **`HEALTHCHECK`** instruction is defined in Dockerfile — container orchestrators use it for readiness
- [ ] Image is **scanned for vulnerabilities** in CI — Trivy, Snyk, or Docker Scout
- [ ] Final image size is **monitored** — target under 500MB, alert on unexpected growth

## 12.2 Docker Compose

- [ ] **`docker-compose.yml`** exists for local development — full stack spins up with one command
- [ ] `docker-compose.yml` defines all required services — `app`, `db`, `redis`, `celery_worker`, `celery_beat`
- [ ] **Service dependencies** are defined — `depends_on` with `condition: service_healthy` not just `service_started`
- [ ] **Health checks** are defined on all services — PostgreSQL, Redis, and app all have health check commands
- [ ] **Named volumes** are used for persistent data — `postgres_data`, `redis_data` — not anonymous volumes
- [ ] **Environment variables** are loaded from `.env` via `env_file` — no hardcoded credentials in `docker-compose.yml`
- [ ] **Port mappings** are explicit — `"5432:5432"` not just `5432` for clarity
- [ ] A **`docker-compose.override.yml`** is used for developer-specific overrides — not polluting the shared file
- [ ] **`docker-compose.prod.yml`** or equivalent exists for production deployment configuration
- [ ] Celery worker and beat are **separate services** — not combined into one container
- [ ] **`restart: unless-stopped`** or `on-failure` is set on all production services
- [ ] Local development mounts **source code as a volume** — enabling hot reload without rebuilding the image
- [ ] `docker compose up` from a clean clone produces a **fully working local environment** — documented and tested

## 12.3 Environment Configuration

- [ ] **Environment parity** is maintained — dev, staging, and production use the same Docker image, different config
- [ ] Configuration differences between environments are **only via environment variables** — no code branches per environment
- [ ] **Secrets are never in `docker-compose.yml`** — injected via `.env` file or external secret manager
- [ ] Production secrets are managed via a **secret manager** — AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager
- [ ] Secrets are **rotated on a schedule** — not static forever since initial setup
- [ ] Secret rotation does not require a deployment — app reads secrets dynamically or gracefully restarts
- [ ] **Environment-specific configuration** is validated on startup — fail fast if misconfigured
- [ ] A **runbook exists** for each environment — how to access, deploy, debug, and rollback

## 12.4 Web Server & Reverse Proxy

- [ ] **Gunicorn** is used as the WSGI server — not Django's development server in any deployed environment
- [ ] **Gunicorn worker count** is tuned — `(2 x CPU cores) + 1` for sync, fewer for async workers
- [ ] **Gunicorn worker class** matches the workload — `sync` for CPU-bound, `gevent`/`uvicorn` for async
- [ ] **Gunicorn `--timeout`** is set — default 30s, adjusted for long-running requests
- [ ] **Gunicorn `--max-requests`** and **`--max-requests-jitter`** are set — recycling workers to prevent memory leaks
- [ ] **Gunicorn `--access-logfile`** and **`--error-logfile`** are configured — logs to stdout/stderr in containers
- [ ] **nginx** sits in front of Gunicorn — handling TLS termination, static files, and slow client buffering
- [ ] nginx **`client_max_body_size`** is set — limiting upload size at the proxy level
- [ ] nginx **`client_body_timeout`** and **`client_header_timeout`** are set — mitigating slow loris attacks
- [ ] nginx **`keepalive_timeout`** is tuned — balancing connection reuse vs resource consumption
- [ ] nginx **`gzip`** compression is enabled — for JSON, HTML, CSS, and JS responses
- [ ] nginx **`proxy_pass`** is correctly configured — forwarding to Gunicorn socket or TCP port
- [ ] nginx serves **static files directly** — not proxied through Django/Gunicorn
- [ ] **TLS termination** happens at nginx — Gunicorn speaks plain HTTP internally
- [ ] nginx configuration is **version-controlled** — not manually edited on the server
- [ ] nginx config is **validated in CI** — `nginx -t` runs against the config file

## 12.5 Health Checks & Readiness

- [ ] A **`/health/`** endpoint exists — returns `200 OK` if the app process is alive
- [ ] A **`/ready/`** endpoint exists — returns `200 OK` only if DB, Redis, and broker are all reachable
- [ ] Health check endpoints are **lightweight** — no heavy DB queries, just connectivity pings
- [ ] Health check endpoints are **unauthenticated** — load balancers and orchestrators can call them without credentials
- [ ] Health check endpoints are **excluded from rate limiting** — not throttled
- [ ] Health check endpoints are **excluded from access logs** — not polluting logs with noise
- [ ] Celery workers have a **health check mechanism** — `celery inspect ping` or a custom heartbeat task
- [ ] **Kubernetes liveness and readiness probes** are configured if deployed on k8s — using the health endpoints
- [ ] **Load balancer health checks** are configured — unhealthy instances removed from rotation automatically
- [ ] Health check response includes **version information** — `{"status": "ok", "version": "1.2.3", "git_sha": "abc123"}`

## 12.6 Logging Infrastructure

- [ ] All application logs go to **`stdout`/`stderr`** — not to files inside the container
- [ ] Logs are in **structured JSON format** — parseable by log aggregation systems
- [ ] Every log record includes — `timestamp`, `level`, `logger`, `message`, `request_id`, `environment`
- [ ] **Request ID** is generated per request and propagated through all log records and downstream calls
- [ ] **`django-request-id`** or custom middleware injects request ID into all logs for the request lifecycle
- [ ] Logs are **shipped to a centralized system** — ELK Stack, Datadog, CloudWatch, Loki
- [ ] **Log retention policy** is defined and enforced — 30 days for debug, 90 days for info, 1 year for audit logs
- [ ] **Log levels are correct per environment** — `DEBUG` locally, `INFO` in staging, `WARNING` in production
- [ ] **Sensitive data is filtered** from logs — passwords, tokens, PII stripped at the handler level
- [ ] **Slow query logging** is enabled in PostgreSQL — `log_min_duration_statement = 100` (ms)
- [ ] **Celery task logs** include task name, task ID, and execution time
- [ ] Log volume is **monitored** — sudden log spikes signal an error storm

## 12.7 Monitoring & Alerting

- [ ] **Sentry** or equivalent is integrated — capturing unhandled exceptions with full context
- [ ] Sentry **environment tags** are set correctly — `production`, `staging`, `development`
- [ ] Sentry **release tracking** is configured — errors linked to specific deployments
- [ ] Sentry **performance monitoring** is enabled — transaction traces for slow endpoints
- [ ] Sentry **scrubs sensitive data** — PII and tokens removed via `before_send` hook
- [ ] **Prometheus metrics** are exposed — via `django-prometheus` or custom metrics endpoint
- [ ] **Key application metrics** are tracked — request rate, error rate, response time (p50, p95, p99)
- [ ] **Business metrics** are tracked — orders created, users registered, payments processed
- [ ] **Celery queue depth** is monitored — growing queue signals worker capacity issues
- [ ] **Database connection pool** usage is monitored — approaching max connections triggers alert
- [ ] **Redis memory usage** is monitored — eviction events signal cache pressure
- [ ] **Alerting thresholds** are defined — not just dashboards, but paging alerts on critical signals
- [ ] **On-call rotation** is defined — alerts reach a human, not a shared inbox
- [ ] **Runbooks are linked from alerts** — responders know what to do when paged

## 12.8 Database Operations

- [ ] **Database backups** run automatically — daily full backup, hourly incremental
- [ ] Backups are **tested regularly** — restoration drill performed monthly
- [ ] Backups are **stored in a separate region** — not on the same server as the database
- [ ] Backup retention policy is defined — 7 daily, 4 weekly, 12 monthly
- [ ] **Point-in-time recovery (PITR)** is enabled — WAL archiving configured for PostgreSQL
- [ ] **Database connection pooling** is configured — pgBouncer in transaction mode for high concurrency
- [ ] **Read replica** is provisioned for read-heavy workloads and reporting queries
- [ ] Database **`max_connections`** limit is appropriate for the connection pool and worker count
- [ ] **`shared_buffers`** and **`work_mem`** are tuned — not left at PostgreSQL defaults
- [ ] **`autovacuum`** is monitored — not falling behind on table bloat
- [ ] **Table bloat and index bloat** are monitored — `pg_bloat` or equivalent queries run periodically
- [ ] **Long-running queries** are detected and killed — `statement_timeout` set appropriately
- [ ] Database **failover** is tested — promoting a replica does not require manual intervention in an emergency
- [ ] **`pg_stat_statements`** extension is enabled — tracking slow query patterns over time

## 12.9 Static & Media File Serving

- [ ] **`collectstatic`** runs as part of the deploy pipeline — not a manual step
- [ ] Static files are served from **S3, GCS, or equivalent** in production — not from the application server
- [ ] **CDN** sits in front of static and media file storage — reducing latency and origin load
- [ ] Static files are **fingerprinted** — content hash in filename enables aggressive CDN caching
- [ ] **`Cache-Control: max-age=31536000, immutable`** is set on fingerprinted static files
- [ ] **Media files** (user uploads) are stored in S3 — not on local disk
- [ ] **Private media files** use pre-signed URLs — not publicly accessible by default
- [ ] Pre-signed URL expiry is **short** — minutes for sensitive files, not days
- [ ] **CORS policy** on the S3 bucket is minimal — only allowing origins that need direct upload
- [ ] **Lifecycle policies** are set on S3 buckets — old temporary files cleaned up automatically

## 12.10 Deployment Process

- [ ] **Deployment is automated** — no manual SSH and `git pull` on the server
- [ ] Deployment uses a **blue-green or rolling strategy** — zero downtime deploys
- [ ] **Database migrations run automatically** as part of deploy — before new code is live
- [ ] Migration step runs **before** traffic is shifted to new containers — avoiding schema/code mismatch
- [ ] **Backwards-compatible migrations** are enforced — new code works with old schema during rollout
- [ ] Deploy pipeline includes — build, test, scan, push image, deploy, smoke test, rollback-if-failed
- [ ] **Smoke tests** run automatically after every deployment — basic endpoint checks before declaring success
- [ ] **Automatic rollback** is triggered if smoke tests fail — not manual intervention
- [ ] **Deploy notifications** are sent to the team — success and failure both communicated
- [ ] **Git SHA or version tag** is embedded in the running container — `GET /health/` returns the deployed version
- [ ] **Feature flags** allow decoupling deploy from release — code ships before it is turned on
- [ ] **Deployment history** is logged — who deployed what, when, with ability to audit

## 12.11 Scalability & Resilience

- [ ] Application is **stateless** — no in-memory state that prevents horizontal scaling
- [ ] **Session state** is stored in Redis — not in-process memory
- [ ] **File uploads** go directly to S3 — not through the application server
- [ ] **Horizontal scaling** is tested — running 2+ instances produces correct behavior with no race conditions
- [ ] **Auto-scaling policies** are defined — scale out on CPU > 70% or request queue depth > threshold
- [ ] **Celery workers scale independently** of web workers — separate auto-scaling group
- [ ] **Circuit breakers** are in place for external service dependencies — app degrades gracefully when a dependency fails
- [ ] **Retry logic with exponential backoff** is implemented for all external calls
- [ ] **Graceful shutdown** is implemented — SIGTERM drains in-flight requests before stopping
- [ ] Gunicorn **`--graceful-timeout`** is set — workers finish current requests before forced kill
- [ ] **Load testing** is conducted before major releases — capacity limits are known before production traffic hits them
- [ ] **Chaos engineering** is considered — failure of Redis, DB, or a downstream service is tested in staging

## 12.12 Infrastructure as Code

- [ ] Infrastructure is defined in **code** — Terraform, Pulumi, CDK, or CloudFormation — not manually provisioned
- [ ] IaC code is **version-controlled** — in the same repo or a dedicated infra repo
- [ ] IaC changes go through **code review** — same rigor as application code
- [ ] **`terraform plan`** or equivalent runs in CI — changes previewed before apply
- [ ] **`terraform apply`** is automated in CD — not run manually from a developer's laptop
- [ ] IaC state is stored **remotely** — S3 + DynamoDB locking for Terraform, not local `terraform.tfstate`
- [ ] **Environment parity** is enforced in IaC — staging is a smaller replica of production, not a completely different setup
- [ ] **Sensitive values in IaC** are referenced from secret manager — not hardcoded in `.tf` files
- [ ] **Drift detection** runs periodically — alerting when real infrastructure diverges from IaC definition
- [ ] **Destroy protection** is enabled on critical resources — databases and storage cannot be accidentally deleted

## 12.13 SSL/TLS & Certificate Management (Added)

- [ ] **TLS 1.2+** is enforced — TLS 1.0 and 1.1 are disabled
- [ ] Strong **cipher suites** are configured — ECDHE preferred, no RC4, no 3DES
- [ ] **HSTS** is enabled with appropriate max-age — at least 1 year, with includeSubDomains and preload
- [ ] Certificates are managed via **ACME/Let's Encrypt** or a cloud provider — not manually provisioned
- [ ] Certificate **auto-renewal** is configured — no manual renewal every 90 days
- [ ] Certificate expiry is **monitored** — alerting 30 days before expiration
- [ ] **OCSP stapling** is enabled in nginx — reducing TLS handshake latency
- [ ] SSL configuration is tested via **SSL Labs** or equivalent — target A+ rating

## 12.14 Container Registry & Image Management (Added)

- [ ] A **private container registry** is used — ECR, GCR, ACR, or self-hosted — not Docker Hub free tier for production
- [ ] Images are **tagged with version/SHA** — not just `:latest`
- [ ] **Image lifecycle policies** are configured — old images cleaned up automatically
- [ ] **Image signing** is considered — Docker Content Trust or cosign for supply chain security
- [ ] Registry access is **authenticated and authorized** — pull/push permissions controlled
- [ ] Images are **scanned on push** — registry-level vulnerability scanning enabled
- [ ] **Base image updates** are tracked — rebuilds triggered when upstream base image is patched
- [ ] Image **layers are optimized** — most frequently changing layers at the bottom of Dockerfile
