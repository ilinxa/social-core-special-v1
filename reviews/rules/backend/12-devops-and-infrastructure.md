# 12 — DevOps & Infrastructure Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 12.1 Docker & Containerization

| ID | Rule | Verdict |
|----|------|---------|
| 12.1.1 | FAIL if no Dockerfile exists | PASS/FAIL |
| 12.1.2 | WARN if no multi-stage build — single-stage includes build tools in final image | PASS/WARN |
| 12.1.3 | WARN if base image uses mutable tag without digest | PASS/WARN |
| 12.1.4 | PASS if slim or Alpine base image used | PASS |
| 12.1.5 | FAIL if application runs as root user in container | PASS/FAIL |
| 12.1.6 | PASS if non-root user created with explicit UID/GID | PASS |
| 12.1.7 | PASS if WORKDIR is set explicitly | PASS |
| 12.1.8 | WARN if no .dockerignore or it's missing key exclusions | PASS/WARN |
| 12.1.9 | PASS if COPY uses .dockerignore to exclude unnecessary files | PASS |
| 12.1.10 | PASS if dependency layer is separate from code layer for caching | PASS |
| 12.1.11 | PASS if --no-cache-dir used with pip install | PASS |
| 12.1.12 | PASS if apt-get cache cleaned in same RUN layer (or no apt-get needed) | PASS |
| 12.1.13 | WARN if CMD uses shell form instead of exec form | PASS/WARN |
| 12.1.14 | PASS if EXPOSE documents the listening port | PASS |
| 12.1.15 | INFO if no HEALTHCHECK instruction — acceptable if orchestrator handles it | PASS/INFO |
| 12.1.16 | WARN if no image vulnerability scanning configured | PASS/WARN |
| 12.1.17 | INFO if image size not actively monitored | PASS/INFO |

## 12.2 Docker Compose

| ID | Rule | Verdict |
|----|------|---------|
| 12.2.1 | PASS if docker-compose.yml exists for local development | PASS |
| 12.2.2 | PASS if all required services are defined (app, db, redis, celery) | PASS |
| 12.2.3 | PASS if depends_on uses service_healthy condition | PASS |
| 12.2.4 | PASS if health checks defined on all stateful services | PASS |
| 12.2.5 | PASS if named volumes used for persistent data | PASS |
| 12.2.6 | WARN if credentials hardcoded in docker-compose.yml (not .env) | PASS/WARN |
| 12.2.7 | PASS if port mappings are explicit ("5432:5432" not just 5432) | PASS |
| 12.2.8 | INFO if no docker-compose.override.yml — acceptable for small teams | PASS/INFO |
| 12.2.9 | PASS if production docker-compose or equivalent exists | PASS |
| 12.2.10 | PASS if Celery worker and beat are separate services | PASS |
| 12.2.11 | PASS if restart policy set on production services | PASS |
| 12.2.12 | INFO if no source volume mount for hot reload — acceptable if using local dev server | PASS/INFO |
| 12.2.13 | PASS if docker compose up from clean clone works with documentation | PASS |

## 12.3 Environment Configuration

| ID | Rule | Verdict |
|----|------|---------|
| 12.3.1 | PASS if same Docker image used across environments with different config | PASS |
| 12.3.2 | PASS if config differences are only via environment variables | PASS |
| 12.3.3 | FAIL if secrets hardcoded in docker-compose.yml or Dockerfile | PASS/FAIL |
| 12.3.4 | INFO if no external secret manager — .env acceptable for early stage | PASS/INFO |
| 12.3.5 | INFO if secret rotation not implemented — acceptable for early stage | PASS/INFO |
| 12.3.6 | INFO if dynamic secret reading not implemented | PASS/INFO |
| 12.3.7 | WARN if no startup validation for required environment variables | PASS/WARN |
| 12.3.8 | INFO if no runbook per environment | PASS/INFO |

## 12.4 Web Server & Reverse Proxy

| ID | Rule | Verdict |
|----|------|---------|
| 12.4.1 | FAIL if Django dev server used in any deployed environment | PASS/FAIL |
| 12.4.2 | WARN if Gunicorn worker count is hardcoded — should be configurable | PASS/WARN |
| 12.4.3 | PASS if worker class matches workload (uvicorn for async) | PASS |
| 12.4.4 | WARN if Gunicorn --timeout not explicitly set | PASS/WARN |
| 12.4.5 | WARN if --max-requests not set — risk of memory leaks over time | PASS/WARN |
| 12.4.6 | WARN if Gunicorn logging not configured for stdout/stderr | PASS/WARN |
| 12.4.7 | PASS if nginx sits in front of Gunicorn | PASS |
| 12.4.8 | PASS if nginx client_max_body_size is set | PASS |
| 12.4.9 | WARN if nginx timeout settings not configured (slow loris mitigation) | PASS/WARN |
| 12.4.10 | PASS if nginx keepalive_timeout is set | PASS |
| 12.4.11 | PASS if nginx gzip compression enabled | PASS |
| 12.4.12 | PASS if nginx proxy_pass correctly configured | PASS |
| 12.4.13 | PASS if nginx serves static files directly | PASS |
| 12.4.14 | PASS if TLS termination at nginx level | PASS |
| 12.4.15 | PASS if nginx config is version-controlled | PASS |
| 12.4.16 | INFO if nginx config not validated in CI — no CI exists | PASS/INFO |

## 12.5 Health Checks & Readiness

| ID | Rule | Verdict |
|----|------|---------|
| 12.5.1 | WARN if no /health/ endpoint exists | PASS/WARN |
| 12.5.2 | WARN if no /ready/ endpoint with dependency checks | PASS/WARN |
| 12.5.3 | PASS if health check is lightweight (no heavy queries) | PASS |
| 12.5.4 | PASS if health check is unauthenticated | PASS |
| 12.5.5 | PASS if health check excluded from rate limiting | PASS |
| 12.5.6 | INFO if health check not excluded from access logs | PASS/INFO |
| 12.5.7 | INFO if no Celery health check mechanism | PASS/INFO |
| 12.5.8 | INFO if no Kubernetes probes — N/A if not on k8s | PASS/INFO |
| 12.5.9 | INFO if no load balancer health check — acceptable for early stage | PASS/INFO |
| 12.5.10 | INFO if health check doesn't include version info | PASS/INFO |

## 12.6 Logging Infrastructure

| ID | Rule | Verdict |
|----|------|---------|
| 12.6.1 | PASS if logs go to stdout/stderr | PASS |
| 12.6.2 | PASS if structured JSON logging is configured | PASS |
| 12.6.3 | PASS if log records include timestamp, level, logger, message | PASS |
| 12.6.4 | WARN if no request ID generated and propagated through logs | PASS/WARN |
| 12.6.5 | WARN if no request ID middleware | PASS/WARN |
| 12.6.6 | INFO if logs not shipped to centralized system — acceptable for early stage | PASS/INFO |
| 12.6.7 | INFO if no log retention policy defined | PASS/INFO |
| 12.6.8 | PASS if log levels differ per environment | PASS |
| 12.6.9 | PASS if sensitive data filtered from logs | PASS |
| 12.6.10 | INFO if no PostgreSQL slow query logging — acceptable for early stage | PASS/INFO |
| 12.6.11 | INFO if Celery task logs don't include execution time | PASS/INFO |
| 12.6.12 | INFO if log volume not monitored | PASS/INFO |

## 12.7 Monitoring & Alerting

| ID | Rule | Verdict |
|----|------|---------|
| 12.7.1 | WARN if no Sentry or error tracking integrated | PASS/WARN |
| 12.7.2 | INFO if Sentry environment tags not set — N/A if no Sentry | PASS/INFO |
| 12.7.3 | INFO if Sentry release tracking not configured | PASS/INFO |
| 12.7.4 | INFO if Sentry performance monitoring not enabled | PASS/INFO |
| 12.7.5 | INFO if Sentry sensitive data scrubbing not configured | PASS/INFO |
| 12.7.6 | INFO if no Prometheus metrics — acceptable for early stage | PASS/INFO |
| 12.7.7 | INFO if no application metrics tracking | PASS/INFO |
| 12.7.8 | INFO if no business metrics tracking | PASS/INFO |
| 12.7.9 | INFO if Celery queue depth not monitored | PASS/INFO |
| 12.7.10 | INFO if DB connection pool not monitored | PASS/INFO |
| 12.7.11 | INFO if Redis memory not monitored | PASS/INFO |
| 12.7.12 | INFO if no alerting thresholds defined | PASS/INFO |
| 12.7.13 | INFO if no on-call rotation — acceptable for early stage | PASS/INFO |
| 12.7.14 | INFO if no runbooks linked from alerts | PASS/INFO |

## 12.8 Database Operations

| ID | Rule | Verdict |
|----|------|---------|
| 12.8.1 | INFO if no automated backups — acceptable for early stage / managed DB handles this | PASS/INFO |
| 12.8.2 | INFO if backups not tested regularly | PASS/INFO |
| 12.8.3 | INFO if backups not in separate region | PASS/INFO |
| 12.8.4 | INFO if no backup retention policy | PASS/INFO |
| 12.8.5 | INFO if no PITR configured | PASS/INFO |
| 12.8.6 | INFO if no connection pooling — acceptable for early stage | PASS/INFO |
| 12.8.7 | INFO if no read replica — acceptable for early stage | PASS/INFO |
| 12.8.8 | WARN if max_connections not considered for connection pool | PASS/WARN |
| 12.8.9 | INFO if shared_buffers and work_mem at defaults | PASS/INFO |
| 12.8.10 | INFO if autovacuum not monitored | PASS/INFO |
| 12.8.11 | INFO if bloat not monitored | PASS/INFO |
| 12.8.12 | WARN if no statement_timeout configured | PASS/WARN |
| 12.8.13 | INFO if failover not tested | PASS/INFO |
| 12.8.14 | INFO if pg_stat_statements not enabled | PASS/INFO |

## 12.9 Static & Media File Serving

| ID | Rule | Verdict |
|----|------|---------|
| 12.9.1 | PASS if collectstatic runs in deploy pipeline (entrypoint/Dockerfile) | PASS |
| 12.9.2 | PASS if S3 or equivalent configured for production static files | PASS |
| 12.9.3 | INFO if no CDN — acceptable for early stage | PASS/INFO |
| 12.9.4 | WARN if static files not fingerprinted | PASS/WARN |
| 12.9.5 | INFO if no aggressive cache headers on static files | PASS/INFO |
| 12.9.6 | PASS if media files stored in S3 or configured for S3 | PASS |
| 12.9.7 | WARN if private media files publicly accessible (no pre-signed URLs) | PASS/WARN |
| 12.9.8 | INFO if pre-signed URL expiry not configured | PASS/INFO |
| 12.9.9 | INFO if S3 CORS not minimized | PASS/INFO |
| 12.9.10 | INFO if no S3 lifecycle policies | PASS/INFO |

## 12.10 Deployment Process

| ID | Rule | Verdict |
|----|------|---------|
| 12.10.1 | INFO if deployment not fully automated — acceptable for early stage | PASS/INFO |
| 12.10.2 | INFO if no blue-green or rolling deploy | PASS/INFO |
| 12.10.3 | PASS if migrations run as part of deploy (entrypoint) | PASS |
| 12.10.4 | PASS if migrations run before traffic shift | PASS |
| 12.10.5 | INFO if backwards-compatible migrations not enforced — no formal process | PASS/INFO |
| 12.10.6 | INFO if no full CI/CD pipeline | PASS/INFO |
| 12.10.7 | INFO if no smoke tests after deploy | PASS/INFO |
| 12.10.8 | INFO if no automatic rollback | PASS/INFO |
| 12.10.9 | INFO if no deploy notifications | PASS/INFO |
| 12.10.10 | INFO if no version/SHA in running container | PASS/INFO |
| 12.10.11 | INFO if no feature flags | PASS/INFO |
| 12.10.12 | INFO if no deployment history logging | PASS/INFO |

## 12.11 Scalability & Resilience

| ID | Rule | Verdict |
|----|------|---------|
| 12.11.1 | PASS if application is stateless (no in-memory sessions) | PASS |
| 12.11.2 | PASS if session state in Redis | PASS |
| 12.11.3 | PASS if file uploads configured for S3 (not local disk in production) | PASS |
| 12.11.4 | INFO if horizontal scaling not tested | PASS/INFO |
| 12.11.5 | INFO if no auto-scaling policies | PASS/INFO |
| 12.11.6 | PASS if Celery workers separate from web workers | PASS |
| 12.11.7 | INFO if no circuit breakers — acceptable for early stage | PASS/INFO |
| 12.11.8 | PASS if retry logic with backoff exists for external calls | PASS |
| 12.11.9 | WARN if no graceful shutdown handling (SIGTERM) | PASS/WARN |
| 12.11.10 | WARN if Gunicorn --graceful-timeout not set | PASS/WARN |
| 12.11.11 | INFO if no load testing conducted | PASS/INFO |
| 12.11.12 | INFO if no chaos engineering | PASS/INFO |

## 12.12 Infrastructure as Code

| ID | Rule | Verdict |
|----|------|---------|
| 12.12.1 | INFO if no IaC — acceptable for early stage | PASS/INFO |
| 12.12.2 | INFO if IaC not version-controlled — N/A | PASS/INFO |
| 12.12.3 | INFO if IaC not reviewed — N/A | PASS/INFO |
| 12.12.4 | INFO if no terraform plan in CI — N/A | PASS/INFO |
| 12.12.5 | INFO if no terraform apply automation — N/A | PASS/INFO |
| 12.12.6 | INFO if no remote state — N/A | PASS/INFO |
| 12.12.7 | INFO if no env parity in IaC — N/A | PASS/INFO |
| 12.12.8 | INFO if sensitive values not in secret manager — N/A | PASS/INFO |
| 12.12.9 | INFO if no drift detection — N/A | PASS/INFO |
| 12.12.10 | INFO if no destroy protection — N/A | PASS/INFO |

## 12.13 SSL/TLS & Certificate Management (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 12.13.1 | PASS if TLS 1.2+ enforced in nginx config | PASS |
| 12.13.2 | PASS if strong cipher suites configured | PASS |
| 12.13.3 | PASS if HSTS enabled with appropriate max-age | PASS |
| 12.13.4 | INFO if no automated certificate management — acceptable for early stage | PASS/INFO |
| 12.13.5 | INFO if no certificate auto-renewal | PASS/INFO |
| 12.13.6 | INFO if no certificate expiry monitoring | PASS/INFO |
| 12.13.7 | INFO if no OCSP stapling | PASS/INFO |
| 12.13.8 | INFO if SSL config not tested via SSL Labs | PASS/INFO |

## 12.14 Container Registry & Image Management (Added)

| ID | Rule | Verdict |
|----|------|---------|
| 12.14.1 | INFO if no private container registry — acceptable for early stage | PASS/INFO |
| 12.14.2 | WARN if images only tagged with :latest — no version/SHA tags | PASS/WARN |
| 12.14.3 | INFO if no image lifecycle policies | PASS/INFO |
| 12.14.4 | INFO if no image signing | PASS/INFO |
| 12.14.5 | INFO if no registry access controls | PASS/INFO |
| 12.14.6 | WARN if no image scanning on push | PASS/WARN |
| 12.14.7 | INFO if base image updates not tracked | PASS/INFO |
| 12.14.8 | PASS if Dockerfile layer ordering optimized (deps before code) | PASS |
