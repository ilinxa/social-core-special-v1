# 15 — Observability & Monitoring Checklist

## 15.1 Observability Strategy & Architecture
- [ ] **Three pillars of observability** are all implemented — logs, metrics, and traces — not just one or two
- [ ] Observability is **designed in from the start** — not bolted on after incidents reveal blind spots
- [ ] A **central observability platform** is chosen — Datadog, Grafana stack, New Relic, AWS CloudWatch — not fragmented across disconnected tools
- [ ] Observability tooling is **consistent across all environments** — staging has the same visibility as production
- [ ] **Service Level Objectives (SLOs)** are defined — measurable targets for availability, latency, and error rate
- [ ] **Service Level Indicators (SLIs)** are instrumented — the metrics that measure SLO compliance
- [ ] **Error budgets** are calculated from SLOs — teams know how much reliability headroom remains
- [ ] Observability data is **retained long enough** — 30 days minimum for metrics, 90 days for logs, 1 year for audit trails
- [ ] **Observability costs are monitored** — log volume and metric cardinality controlled to avoid runaway costs
- [ ] A **documented on-call runbook** links observability signals to remediation steps

## 15.2 Structured Logging
- [ ] All logs are **structured JSON** — machine-parseable, not free-form text strings
- [ ] **`structlog`** is used — not bare `logging.getLogger()` with string interpolation
- [ ] Every log record includes — `timestamp`, `level`, `logger`, `message`, `environment`, `service`, `version`
- [ ] Every log record includes a **`request_id`** — correlating all logs from a single request
- [ ] **`request_id`** is generated at the request entry point and propagated through all downstream calls and tasks
- [ ] Every Celery task log includes — `task_id`, `task_name`, `queue`, `execution_time`
- [ ] Log levels are used **semantically and consistently**:
  - `DEBUG` — detailed diagnostic info, local dev only
  - `INFO` — normal operational events, deployments, user actions
  - `WARNING` — unexpected but handled situations, degraded behavior
  - `ERROR` — failures that need attention but did not crash the process
  - `CRITICAL` — failures requiring immediate intervention
- [ ] **No `print()` statements** anywhere in production code — always use the logging framework
- [ ] **No `logger.exception()` without context** — always include relevant identifiers in the log record
- [ ] **Sensitive data is scrubbed** from logs — passwords, tokens, PII stripped at the handler level
- [ ] **Log volume is controlled** — no unbounded logging in tight loops or per-row operations
- [ ] **Django request logs** are structured — including method, path, status, response time, user ID
- [ ] **SQL query logs** are available in development — `django-silk` or `LOGGING` config capturing DB queries
- [ ] Logs from all services (app, celery, nginx, postgres) are **shipped to the same platform** — unified search

## 15.3 Log Aggregation & Search
- [ ] Logs are **centrally aggregated** — ELK Stack, Datadog Logs, CloudWatch Logs, Grafana Loki
- [ ] Log aggregation is **real-time** — logs visible within seconds of being emitted
- [ ] **Log search is fast and functional** — searching by `request_id`, `user_id`, `task_id` returns results immediately
- [ ] **Saved searches** exist for common investigation patterns — failed auth events, 5xx errors, slow queries
- [ ] **Log-based alerts** are configured — patterns in logs trigger notifications before metrics catch them
- [ ] Logs are **indexed on key fields** — `request_id`, `user_id`, `level`, `logger` are searchable without full-text scan
- [ ] **Log retention tiers** are defined — hot storage for recent logs, cold storage for archive, automatic transition
- [ ] Log access is **access-controlled** — production logs not accessible to all developers by default
- [ ] **Log parsing rules** are defined — structured fields extracted correctly by the aggregation platform
- [ ] **Log anomaly detection** is configured — unusual log patterns surfaced automatically

## 15.4 Metrics Collection
- [ ] **`django-prometheus`** or equivalent exports application metrics — request count, latency, error rate
- [ ] A **`/metrics`** endpoint is exposed — scraped by Prometheus or equivalent
- [ ] **`/metrics`** endpoint is access-controlled — not publicly accessible
- [ ] **Standard HTTP metrics** are tracked — `http_requests_total`, `http_request_duration_seconds` with labels for method, endpoint, status code
- [ ] **Database metrics** are tracked — query count per request, slow query count, connection pool usage
- [ ] **Cache metrics** are tracked — hit rate, miss rate, eviction rate per cache key prefix
- [ ] **Celery metrics** are tracked — task enqueue rate, execution time, failure rate, queue depth per queue
- [ ] **Custom business metrics** are instrumented — orders created, payments processed, users registered
- [ ] Metric **cardinality is controlled** — no high-cardinality labels like user ID or raw URL paths on metrics
- [ ] **Gauge, counter, and histogram** types are used correctly — not everything is a counter
- [ ] **`process_` and `python_` metrics** are collected — GC pauses, open file descriptors, memory usage
- [ ] Metrics are **labeled consistently** — `service`, `environment`, `version` labels on all metrics
- [ ] **Infrastructure metrics** are collected — CPU, memory, disk, network per host and container

## 15.5 Dashboards & Visualization
- [ ] A **service health dashboard** exists — single pane of glass for request rate, error rate, latency
- [ ] Dashboard follows **RED method** for services — Rate, Errors, Duration per endpoint
- [ ] Dashboard follows **USE method** for infrastructure — Utilization, Saturation, Errors per resource
- [ ] **Celery worker dashboard** exists — queue depth, task throughput, failure rate, worker count
- [ ] **Database dashboard** exists — query rate, slow queries, connection pool usage, replication lag
- [ ] **Cache dashboard** exists — hit/miss rate, memory usage, eviction rate, connection count
- [ ] **Business metrics dashboard** exists — key product KPIs visible to non-technical stakeholders
- [ ] Dashboards are **version-controlled** — Grafana JSON, Terraform, or equivalent — not manually created and undocumented
- [ ] Dashboards are **deployed automatically** — not manually imported per environment
- [ ] **Latency percentiles** are shown — p50, p95, p99 — not just averages which hide tail latency
- [ ] Dashboards have **annotations** — deployment events marked on time series, correlating changes with behavior
- [ ] Dashboards have **time range controls** — easy to zoom into incidents and compare with previous periods
- [ ] Dashboard **links are shared** in runbooks and incident channels — not requiring platform navigation to find

## 15.6 Distributed Tracing
- [ ] **OpenTelemetry** is used for instrumentation — vendor-neutral, portable across tracing backends
- [ ] **`opentelemetry-django`** auto-instrumentation is enabled — tracing all incoming HTTP requests automatically
- [ ] **`opentelemetry-psycopg2`** instrumentation is enabled — database queries appear in traces
- [ ] **`opentelemetry-redis`** instrumentation is enabled — Redis calls appear in traces
- [ ] **`opentelemetry-celery`** instrumentation is enabled — task execution appears in traces
- [ ] **Trace context is propagated** across service boundaries — `traceparent` header forwarded to downstream services
- [ ] **Trace context is propagated** to Celery tasks — tasks linked to the originating request trace
- [ ] Every trace includes — `service.name`, `service.version`, `deployment.environment` resource attributes
- [ ] **Sampling rate is configured** — 100% in development, lower in production for cost control
- [ ] **Tail-based sampling** is considered — keeping 100% of error traces, sampling successful ones
- [ ] **Slow traces are retained** — traces above a latency threshold kept regardless of sampling rate
- [ ] Traces are **searchable by request ID** — correlating with log entries from the same request
- [ ] **Trace-to-log correlation** is configured — clicking a trace span navigates to the relevant log entries
- [ ] **N+1 query detection** uses tracing — excessive DB spans visible in the trace waterfall

## 15.7 Error Tracking
- [ ] **Sentry** or equivalent is integrated — capturing all unhandled exceptions automatically
- [ ] Sentry **`environment`** tag is set correctly — `production`, `staging`, `development`
- [ ] Sentry **`release`** is set — tied to the Git SHA or version tag of the deployed code
- [ ] Sentry **`before_send`** hook scrubs PII — passwords, tokens, personal data removed before transmission
- [ ] Sentry **`traces_sample_rate`** is configured — performance monitoring enabled alongside error tracking
- [ ] **Custom error context** is attached — `user.id`, `request.url`, `request.method` on every error
- [ ] **Breadcrumbs** are enriched — meaningful events logged before an error provide investigation context
- [ ] Sentry **alert rules** are configured — new issues and regression alerts route to the right team
- [ ] **Error grouping** is tuned — Sentry's fingerprinting customized to group related errors correctly
- [ ] **Issue ownership rules** are defined — errors automatically assigned to the responsible team
- [ ] **Error volume thresholds** trigger alerts — sudden spike in a known error type pages the on-call
- [ ] **Ignored errors** are documented — intentionally suppressed exceptions have a comment explaining why
- [ ] Sentry is **not the only error channel** — critical errors also appear in metrics and logs

## 15.8 Alerting & On-Call
- [ ] **Alerting rules are defined** for all critical signals — error rate, latency, queue depth, disk space
- [ ] Alerts are **actionable** — every alert has a corresponding runbook, not just a notification
- [ ] **Alert fatigue is managed** — low-signal alerts are tuned or removed, not silently ignored
- [ ] **Multi-window, multi-burn-rate alerts** are used for SLO-based alerting — not simple threshold alerts
- [ ] Alerts have **severity levels** — `critical` pages immediately, `warning` creates a ticket
- [ ] **`critical` alerts** wake someone up — routed to PagerDuty, OpsGenie, or equivalent on-call tool
- [ ] **`warning` alerts** create tickets — actionable during business hours, not ignored
- [ ] **On-call rotation** is defined — responsibility is shared, not falling on one person permanently
- [ ] **Escalation policy** is defined — if primary on-call does not acknowledge, secondary is paged
- [ ] **Alert routing** is configured — database alerts go to infra team, application errors go to dev team
- [ ] **Runbooks are linked from every alert** — responders immediately know what to do
- [ ] **Alert history is reviewed** monthly — noisy or useless alerts are removed or tuned
- [ ] **Post-incident alert review** — after every incident, missing alerts are added, false ones removed
- [ ] **Silence windows** are used during maintenance — not disabling alerts permanently

## 15.9 Performance Monitoring
- [ ] **Endpoint-level latency** is tracked — p50, p95, p99 per endpoint in production
- [ ] **Latency SLOs** are defined per endpoint category — e.g. interactive endpoints under 200ms p95
- [ ] **Latency regressions** are detected automatically — alert fires when p95 increases beyond threshold
- [ ] **Apdex score** is tracked — satisfaction metric combining latency and error rate
- [ ] **Database query performance** is monitored — slow query log analyzed, `pg_stat_statements` queried regularly
- [ ] **Cache performance** is monitored — hit rate drop signals a broken invalidation or cold cache issue
- [ ] **Celery task execution time** is tracked per task type — slow tasks are identified and optimized
- [ ] **Memory usage per worker** is tracked — growing RSS signals a memory leak
- [ ] **CPU usage per service** is tracked — sustained high CPU triggers scaling or optimization
- [ ] **Garbage collection metrics** are tracked — GC pauses correlate with latency spikes
- [ ] **External service latency** is tracked — time spent waiting on third-party APIs is measured
- [ ] **Real User Monitoring (RUM)** is considered — measuring latency from the user's perspective, not just the server

## 15.10 Health Checks & Synthetic Monitoring
- [ ] **`/health/`** endpoint returns liveness — app process is alive and responding
- [ ] **`/ready/`** endpoint returns readiness — DB, Redis, and broker are all reachable
- [ ] Health endpoints return **structured JSON** — `{"status": "ok", "checks": {"db": "ok", "redis": "ok"}}`
- [ ] Health endpoints include **version information** — `{"version": "1.2.3", "git_sha": "abc1234"}`
- [ ] Health endpoints are **monitored externally** — uptime monitoring from outside the infrastructure (Pingdom, Better Uptime, UptimeRobot)
- [ ] **Synthetic monitoring** runs critical user journeys — automated checks simulating login, key actions
- [ ] Synthetic monitors run **every 1–5 minutes** — not just once per hour
- [ ] Synthetic monitor failures **alert immediately** — not waiting for a user to report an outage
- [ ] **Multi-region synthetic monitoring** is used — detecting regional outages, not just global ones
- [ ] Health check history is **retained** — downtime incidents reconstructable from check history
- [ ] **SSL certificate expiry** is monitored — alerts 30 days before expiry, not on the day it expires
- [ ] **Domain expiry** is monitored — alerts 60 days before domain registration expires

## 15.11 Incident Management
- [ ] **Incident response process** is documented — defined severity levels, escalation steps, communication plan
- [ ] **Severity levels** are defined — SEV1 (total outage), SEV2 (major degradation), SEV3 (minor impact)
- [ ] **Incident commander role** is defined — one person coordinates response, prevents chaos
- [ ] **Incident communication channel** is established — a dedicated Slack channel per incident
- [ ] **Status page** is updated during incidents — users informed, not left guessing
- [ ] **Mean Time to Detect (MTTD)** is tracked — how quickly monitoring catches incidents
- [ ] **Mean Time to Resolve (MTTR)** is tracked — how quickly incidents are resolved after detection
- [ ] **Post-mortems are blameless** — focus on systems and processes, not individuals
- [ ] **Post-mortem template** exists — timeline, impact, root cause, contributing factors, action items
- [ ] **Post-mortems are completed within 5 business days** of the incident — not forgotten after recovery
- [ ] **Action items from post-mortems are tracked** — not recommendations that disappear into a document
- [ ] **Incident history is maintained** — searchable log of past incidents with linked post-mortems

## 15.12 Observability as Code
- [ ] **Dashboards are defined as code** — Grafana JSON, Terraform `grafana_dashboard` resources, or Jsonnet
- [ ] **Alert rules are defined as code** — Prometheus alerting rules YAML, Terraform alert policies
- [ ] **SLO definitions are defined as code** — not manually configured in a UI
- [ ] Observability code lives in **version control** — same repo or dedicated observability repo
- [ ] Observability configuration goes through **code review** — dashboard and alert changes reviewed like application code
- [ ] Observability is **deployed via CI/CD** — not manually applied by one person with UI access
- [ ] **Observability changes are tested** — new alert rules validated against historical data before deployment
- [ ] **Dashboards are environment-aware** — same code deploys to staging and production with environment variables
- [ ] **Runbooks are linked from alert code** — `runbook_url` annotation on every alert rule
- [ ] Observability as code **prevents drift** — real configuration always matches what is in version control

## 15.13 Audit Logging & Compliance (Added)
- [ ] **AuditLog model** captures all significant user and system actions — who did what, when, on what resource
- [ ] Audit logs record — `actor`, `action`, `resource_type`, `resource_id`, `timestamp`, `ip_address`, `changes`
- [ ] Audit logs are **immutable** — no UPDATE or DELETE operations permitted, append-only
- [ ] Audit logs are **separate from application logs** — different storage/retention, queryable by compliance team
- [ ] **Admin actions** are audit-logged — Django admin creates audit entries, not just application code
- [ ] **Authentication events** are audit-logged — login, logout, failed login, password change, token refresh
- [ ] **Authorization failures** are audit-logged — permission denied events capture who tried to access what
- [ ] **Data export/access events** are logged — PII access tracked for privacy compliance (GDPR, SOC2)
- [ ] Audit log **retention meets regulatory requirements** — 1 year minimum, configurable per regulation
- [ ] Audit logs are **searchable** — by actor, action, resource, and time range

## 15.14 Request Correlation & Context Propagation (Added)
- [ ] **Request ID** is generated for every incoming HTTP request — UUID or similar unique identifier
- [ ] Request ID is **returned in response headers** — `X-Request-ID` header on every response
- [ ] Request ID is **included in every log entry** — via structlog context binding or logging filter
- [ ] Request ID is **propagated to Celery tasks** — tasks carry the originating request's ID
- [ ] Request ID is **propagated to downstream HTTP calls** — forwarded as header to internal services
- [ ] **User context** is bound to all logs for authenticated requests — `user_id` on every log entry
- [ ] **Actor context** is available throughout the request — `ActorContext` or equivalent accessible in service layer
- [ ] Context is **cleaned up after each request** — no context leaking between requests in the same thread/worker
- [ ] **Correlation IDs** support multi-hop tracing — a request through API → Celery → API creates a trace chain
- [ ] Context propagation is **tested** — tests verify that request_id appears in logs and response headers
