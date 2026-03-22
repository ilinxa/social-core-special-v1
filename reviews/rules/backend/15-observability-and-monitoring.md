# 15 — Observability & Monitoring Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 15.1 Observability Strategy & Architecture

| ID | Rule | Verdict |
|----|------|---------|
| 15.1.1 | WARN if only one or two of the three pillars (logs, metrics, traces) are implemented | PASS/WARN |
| 15.1.2 | INFO if observability was clearly bolted on after the fact rather than designed in | PASS/INFO |
| 15.1.3 | WARN if no central observability platform chosen or configured | PASS/WARN |
| 15.1.4 | INFO if staging and production have different observability tooling | PASS/INFO |
| 15.1.5 | INFO if no SLOs are defined | PASS/INFO |
| 15.1.6 | INFO if no SLIs are instrumented | PASS/INFO |
| 15.1.7 | INFO if no error budgets calculated | PASS/INFO |
| 15.1.8 | INFO if no retention policy documented | PASS/INFO |
| 15.1.9 | INFO if observability costs not considered | PASS/INFO |
| 15.1.10 | INFO if no on-call runbook exists | PASS/INFO |

## 15.2 Structured Logging

| ID | Rule | Verdict |
|----|------|---------|
| 15.2.1 | FAIL if logs are not structured JSON — free-form text logs are unqueryable | PASS/FAIL |
| 15.2.2 | WARN if bare `logging.getLogger()` used without structlog | PASS/WARN |
| 15.2.3 | WARN if log records missing standard fields (timestamp, level, logger, message, environment) | PASS/WARN |
| 15.2.4 | WARN if no `request_id` in log records | PASS/WARN |
| 15.2.5 | WARN if `request_id` not generated at request entry and propagated | PASS/WARN |
| 15.2.6 | WARN if Celery task logs missing task_id, task_name, queue, execution_time | PASS/WARN |
| 15.2.7 | WARN if log levels used inconsistently or incorrectly | PASS/WARN |
| 15.2.8 | FAIL if `print()` found in production code | PASS/FAIL |
| 15.2.9 | WARN if `logger.exception()` used without context | PASS/WARN |
| 15.2.10 | FAIL if passwords, tokens, or PII found in log output — even in development | PASS/FAIL |
| 15.2.11 | WARN if unbounded logging in tight loops or per-row operations | PASS/WARN |
| 15.2.12 | WARN if Django request logs not structured with method, path, status, response time, user ID | PASS/WARN |
| 15.2.13 | INFO if no SQL query logging available in development | PASS/INFO |
| 15.2.14 | INFO if logs from different services not shipped to same platform | PASS/INFO |

## 15.3 Log Aggregation & Search

| ID | Rule | Verdict |
|----|------|---------|
| 15.3.1 | WARN if no log aggregation platform configured or documented | PASS/WARN |
| 15.3.2 | INFO if log aggregation not real-time | PASS/INFO |
| 15.3.3 | INFO if no fast search by request_id, user_id, task_id | PASS/INFO |
| 15.3.4 | INFO if no saved searches for common patterns | PASS/INFO |
| 15.3.5 | INFO if no log-based alerts configured | PASS/INFO |
| 15.3.6 | INFO if logs not indexed on key fields | PASS/INFO |
| 15.3.7 | INFO if no log retention tiers defined | PASS/INFO |
| 15.3.8 | INFO if log access not access-controlled | PASS/INFO |
| 15.3.9 | INFO if no log parsing rules defined | PASS/INFO |
| 15.3.10 | INFO if no log anomaly detection | PASS/INFO |

## 15.4 Metrics Collection

| ID | Rule | Verdict |
|----|------|---------|
| 15.4.1 | WARN if no metrics library integrated (django-prometheus or equivalent) | PASS/WARN |
| 15.4.2 | WARN if no `/metrics` endpoint exposed | PASS/WARN |
| 15.4.3 | WARN if `/metrics` endpoint publicly accessible without access control | PASS/WARN |
| 15.4.4 | WARN if no HTTP request metrics (count, duration, status) | PASS/WARN |
| 15.4.5 | INFO if no database metrics tracked | PASS/INFO |
| 15.4.6 | INFO if no cache metrics tracked | PASS/INFO |
| 15.4.7 | INFO if no Celery metrics tracked | PASS/INFO |
| 15.4.8 | INFO if no custom business metrics instrumented | PASS/INFO |
| 15.4.9 | WARN if high-cardinality labels used on metrics (user ID, raw URL) | PASS/WARN |
| 15.4.10 | INFO if metric types (gauge, counter, histogram) used incorrectly | PASS/INFO |
| 15.4.11 | INFO if no process/python metrics collected | PASS/INFO |
| 15.4.12 | INFO if metrics not labeled consistently (service, environment, version) | PASS/INFO |
| 15.4.13 | INFO if no infrastructure metrics collected | PASS/INFO |

## 15.5 Dashboards & Visualization

| ID | Rule | Verdict |
|----|------|---------|
| 15.5.1 | INFO if no service health dashboard exists | PASS/INFO |
| 15.5.2 | INFO if dashboard does not follow RED method | PASS/INFO |
| 15.5.3 | INFO if no USE method dashboard for infrastructure | PASS/INFO |
| 15.5.4 | INFO if no Celery worker dashboard | PASS/INFO |
| 15.5.5 | INFO if no database dashboard | PASS/INFO |
| 15.5.6 | INFO if no cache dashboard | PASS/INFO |
| 15.5.7 | INFO if no business metrics dashboard | PASS/INFO |
| 15.5.8 | INFO if dashboards not version-controlled | PASS/INFO |
| 15.5.9 | INFO if dashboards not deployed automatically | PASS/INFO |
| 15.5.10 | INFO if latency shown as averages only, no percentiles | PASS/INFO |
| 15.5.11 | INFO if no deployment annotations on dashboards | PASS/INFO |
| 15.5.12 | INFO if no time range controls on dashboards | PASS/INFO |
| 15.5.13 | INFO if dashboard links not in runbooks | PASS/INFO |

## 15.6 Distributed Tracing

| ID | Rule | Verdict |
|----|------|---------|
| 15.6.1 | WARN if no OpenTelemetry or equivalent tracing instrumentation | PASS/WARN |
| 15.6.2 | INFO if no auto-instrumentation for Django HTTP requests | PASS/INFO |
| 15.6.3 | INFO if no database query instrumentation in traces | PASS/INFO |
| 15.6.4 | INFO if no Redis instrumentation in traces | PASS/INFO |
| 15.6.5 | INFO if no Celery instrumentation in traces | PASS/INFO |
| 15.6.6 | WARN if trace context not propagated across service boundaries | PASS/WARN |
| 15.6.7 | INFO if trace context not propagated to Celery tasks | PASS/INFO |
| 15.6.8 | INFO if traces missing service.name, service.version, deployment.environment | PASS/INFO |
| 15.6.9 | INFO if no sampling rate configured | PASS/INFO |
| 15.6.10 | INFO if no tail-based sampling considered | PASS/INFO |
| 15.6.11 | INFO if slow traces not retained | PASS/INFO |
| 15.6.12 | INFO if traces not searchable by request ID | PASS/INFO |
| 15.6.13 | INFO if no trace-to-log correlation | PASS/INFO |
| 15.6.14 | INFO if no N+1 query detection via tracing | PASS/INFO |

## 15.7 Error Tracking

| ID | Rule | Verdict |
|----|------|---------|
| 15.7.1 | WARN if no error tracking service (Sentry or equivalent) integrated | PASS/WARN |
| 15.7.2 | WARN if Sentry environment tag not set | PASS/WARN |
| 15.7.3 | INFO if Sentry release not tied to Git SHA | PASS/INFO |
| 15.7.4 | WARN if Sentry `before_send` does not scrub PII | PASS/WARN |
| 15.7.5 | INFO if Sentry traces_sample_rate not configured | PASS/INFO |
| 15.7.6 | WARN if no custom error context (user.id, request.url) on errors | PASS/WARN |
| 15.7.7 | INFO if breadcrumbs not enriched | PASS/INFO |
| 15.7.8 | INFO if no Sentry alert rules configured | PASS/INFO |
| 15.7.9 | INFO if error grouping not tuned | PASS/INFO |
| 15.7.10 | INFO if no issue ownership rules | PASS/INFO |
| 15.7.11 | INFO if no error volume threshold alerts | PASS/INFO |
| 15.7.12 | INFO if ignored errors not documented | PASS/INFO |
| 15.7.13 | WARN if error tracking is the only error channel — errors must also appear in logs | PASS/WARN |

## 15.8 Alerting & On-Call

| ID | Rule | Verdict |
|----|------|---------|
| 15.8.1 | WARN if no alerting rules defined for critical signals | PASS/WARN |
| 15.8.2 | INFO if alerts lack corresponding runbooks | PASS/INFO |
| 15.8.3 | INFO if alert fatigue not managed | PASS/INFO |
| 15.8.4 | INFO if no multi-window burn-rate SLO alerts | PASS/INFO |
| 15.8.5 | INFO if alerts have no severity levels | PASS/INFO |
| 15.8.6 | INFO if critical alerts not routed to on-call tool | PASS/INFO |
| 15.8.7 | INFO if warning alerts not creating tickets | PASS/INFO |
| 15.8.8 | INFO if no on-call rotation defined | PASS/INFO |
| 15.8.9 | INFO if no escalation policy | PASS/INFO |
| 15.8.10 | INFO if no alert routing by team | PASS/INFO |
| 15.8.11 | INFO if runbooks not linked from alerts | PASS/INFO |
| 15.8.12 | INFO if alert history not reviewed monthly | PASS/INFO |
| 15.8.13 | INFO if no post-incident alert review | PASS/INFO |
| 15.8.14 | INFO if no silence windows for maintenance | PASS/INFO |

## 15.9 Performance Monitoring

| ID | Rule | Verdict |
|----|------|---------|
| 15.9.1 | WARN if no endpoint-level latency tracking in production | PASS/WARN |
| 15.9.2 | INFO if no latency SLOs defined per endpoint | PASS/INFO |
| 15.9.3 | INFO if latency regressions not detected automatically | PASS/INFO |
| 15.9.4 | INFO if no Apdex score tracked | PASS/INFO |
| 15.9.5 | INFO if database query performance not monitored | PASS/INFO |
| 15.9.6 | INFO if cache performance not monitored | PASS/INFO |
| 15.9.7 | INFO if Celery task execution time not tracked per type | PASS/INFO |
| 15.9.8 | INFO if memory usage per worker not tracked | PASS/INFO |
| 15.9.9 | INFO if CPU usage per service not tracked | PASS/INFO |
| 15.9.10 | INFO if GC metrics not tracked | PASS/INFO |
| 15.9.11 | INFO if external service latency not tracked | PASS/INFO |
| 15.9.12 | INFO if no RUM considered | PASS/INFO |

## 15.10 Health Checks & Synthetic Monitoring

| ID | Rule | Verdict |
|----|------|---------|
| 15.10.1 | WARN if no `/health/` liveness endpoint | PASS/WARN |
| 15.10.2 | WARN if no `/ready/` readiness endpoint checking DB, Redis, broker | PASS/WARN |
| 15.10.3 | WARN if health endpoints do not return structured JSON | PASS/WARN |
| 15.10.4 | INFO if health endpoints do not include version information | PASS/INFO |
| 15.10.5 | INFO if health endpoints not monitored externally | PASS/INFO |
| 15.10.6 | INFO if no synthetic monitoring for critical user journeys | PASS/INFO |
| 15.10.7 | INFO if synthetic monitors run less frequently than every 5 minutes | PASS/INFO |
| 15.10.8 | INFO if synthetic monitor failures do not alert immediately | PASS/INFO |
| 15.10.9 | INFO if no multi-region synthetic monitoring | PASS/INFO |
| 15.10.10 | INFO if health check history not retained | PASS/INFO |
| 15.10.11 | INFO if SSL certificate expiry not monitored | PASS/INFO |
| 15.10.12 | INFO if domain expiry not monitored | PASS/INFO |

## 15.11 Incident Management

| ID | Rule | Verdict |
|----|------|---------|
| 15.11.1 | INFO if no incident response process documented | PASS/INFO |
| 15.11.2 | INFO if no severity levels defined | PASS/INFO |
| 15.11.3 | INFO if no incident commander role defined | PASS/INFO |
| 15.11.4 | INFO if no incident communication channel established | PASS/INFO |
| 15.11.5 | INFO if no status page | PASS/INFO |
| 15.11.6 | INFO if MTTD not tracked | PASS/INFO |
| 15.11.7 | INFO if MTTR not tracked | PASS/INFO |
| 15.11.8 | INFO if post-mortems not blameless | PASS/INFO |
| 15.11.9 | INFO if no post-mortem template | PASS/INFO |
| 15.11.10 | INFO if post-mortems not completed within 5 business days | PASS/INFO |
| 15.11.11 | INFO if action items from post-mortems not tracked | PASS/INFO |
| 15.11.12 | INFO if no incident history maintained | PASS/INFO |

## 15.12 Observability as Code

| ID | Rule | Verdict |
|----|------|---------|
| 15.12.1 | INFO if dashboards not defined as code | PASS/INFO |
| 15.12.2 | INFO if alert rules not defined as code | PASS/INFO |
| 15.12.3 | INFO if SLO definitions not in code | PASS/INFO |
| 15.12.4 | INFO if observability config not in version control | PASS/INFO |
| 15.12.5 | INFO if observability changes not code-reviewed | PASS/INFO |
| 15.12.6 | INFO if observability not deployed via CI/CD | PASS/INFO |
| 15.12.7 | INFO if observability changes not tested | PASS/INFO |
| 15.12.8 | INFO if dashboards not environment-aware | PASS/INFO |
| 15.12.9 | INFO if runbooks not linked from alert code | PASS/INFO |
| 15.12.10 | INFO if observability config drifts from version control | PASS/INFO |

## 15.13 Audit Logging & Compliance

| ID | Rule | Verdict |
|----|------|---------|
| 15.13.1 | WARN if no AuditLog model capturing user and system actions | PASS/WARN |
| 15.13.2 | WARN if audit logs missing key fields (actor, action, resource_type, resource_id, timestamp) | PASS/WARN |
| 15.13.3 | WARN if audit logs not immutable (UPDATE/DELETE allowed) | PASS/WARN |
| 15.13.4 | INFO if audit logs not separate from application logs | PASS/INFO |
| 15.13.5 | INFO if admin actions not audit-logged | PASS/INFO |
| 15.13.6 | WARN if authentication events not audit-logged | PASS/WARN |
| 15.13.7 | INFO if authorization failures not audit-logged | PASS/INFO |
| 15.13.8 | INFO if data export/access events not logged | PASS/INFO |
| 15.13.9 | INFO if audit log retention not meeting regulatory requirements | PASS/INFO |
| 15.13.10 | INFO if audit logs not searchable by actor, action, resource, time | PASS/INFO |

## 15.14 Request Correlation & Context Propagation

| ID | Rule | Verdict |
|----|------|---------|
| 15.14.1 | WARN if no request ID generated for incoming HTTP requests | PASS/WARN |
| 15.14.2 | WARN if request ID not returned in response headers (X-Request-ID) | PASS/WARN |
| 15.14.3 | WARN if request ID not included in every log entry | PASS/WARN |
| 15.14.4 | INFO if request ID not propagated to Celery tasks | PASS/INFO |
| 15.14.5 | INFO if request ID not propagated to downstream HTTP calls | PASS/INFO |
| 15.14.6 | WARN if user context not bound to logs for authenticated requests | PASS/WARN |
| 15.14.7 | PASS if ActorContext or equivalent available throughout request | PASS |
| 15.14.8 | WARN if context not cleaned up after each request (leaking between requests) | PASS/WARN |
| 15.14.9 | INFO if correlation IDs do not support multi-hop tracing | PASS/INFO |
| 15.14.10 | INFO if context propagation not tested | PASS/INFO |
