# 08 — Performance Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 8.1 Query Optimization Fundamentals

| ID | Rule | Verdict |
|----|------|---------|
| 8.1.1 | WARN if no N+1 detection tooling is installed in development settings | PASS/WARN |
| 8.1.2 | FAIL if ForeignKey/OneToOne traversals in querysets lack `select_related()` on hot paths | PASS/FAIL |
| 8.1.3 | FAIL if ManyToMany/reverse FK traversals in querysets lack `prefetch_related()` on hot paths | PASS/FAIL |
| 8.1.4 | WARN if `Prefetch()` objects are not used when prefetching needs custom filtering | PASS/WARN |
| 8.1.5 | FAIL if ORM queries are made inside serializer `to_representation()` methods | PASS/FAIL |
| 8.1.6 | FAIL if ORM queries are made inside `SerializerMethodField` methods without prefetch | PASS/FAIL |
| 8.1.7 | WARN if model `__str__()` accesses related objects via FK without select_related | PASS/WARN |
| 8.1.8 | PASS if no template rendering exists — API-only application | PASS |
| 8.1.9 | WARN if no `assertNumQueries()` tests exist for critical endpoints | PASS/WARN |
| 8.1.10 | WARN if query count is O(n) with result set size — verified by lack of prefetch on list endpoints | PASS/WARN |

## 8.2 QuerySet Efficiency

| ID | Rule | Verdict |
|----|------|---------|
| 8.2.1 | WARN if `.values()` / `.values_list()` is not used when only IDs or specific fields are needed | PASS/WARN |
| 8.2.2 | INFO if `.only()` is not used on large models — depends on field sizes | PASS/INFO |
| 8.2.3 | WARN if large TextField/JSONField is loaded in list views where it's not displayed | PASS/WARN |
| 8.2.4 | FAIL if `len(queryset)` is used instead of `.count()` to count records | PASS/FAIL |
| 8.2.5 | WARN if `.count() > 0` or `bool(qs)` is used instead of `.exists()` for existence checks | PASS/WARN |
| 8.2.6 | WARN if batch inserts loop `Model.objects.create()` instead of using `.bulk_create()` | PASS/WARN |
| 8.2.7 | WARN if batch updates loop `.save()` instead of using `.bulk_update()` or `.update()` | PASS/WARN |
| 8.2.8 | PASS if `.update()` is used for mass field updates | PASS |
| 8.2.9 | PASS if queryset `.delete()` is used for mass deletion | PASS |
| 8.2.10 | WARN if large queryset iteration in tasks/commands doesn't use `.iterator()` | PASS/WARN |
| 8.2.11 | PASS if `.annotate()` is used to push computations into the database | PASS |
| 8.2.12 | PASS if `.aggregate()` is used for summary statistics | PASS |

## 8.3 Database Indexing Strategy

| ID | Rule | Verdict |
|----|------|---------|
| 8.3.1 | WARN if hot-path filter fields lack indexes — not verified with EXPLAIN | PASS/WARN |
| 8.3.2 | WARN if ordering fields in paginated endpoints lack indexes | PASS/WARN |
| 8.3.3 | PASS if all FK fields have default Django indexes | PASS |
| 8.3.4 | WARN if multi-column filter+order_by patterns on hot paths lack composite indexes | PASS/WARN |
| 8.3.5 | INFO if partial indexes are not used — optimization for later | PASS/INFO |
| 8.3.6 | WARN if queried JSONField columns lack GIN indexes | PASS/WARN |
| 8.3.7 | WARN if full-text search columns lack GIN/GiST indexes | PASS/WARN |
| 8.3.8 | WARN if trigram search columns lack `pg_trgm` indexes | PASS/WARN |
| 8.3.9 | WARN if EXPLAIN ANALYZE is not run on hot-path queries during development | PASS/WARN |
| 8.3.10 | WARN if write-heavy tables have excessive indexes without justification | PASS/WARN |
| 8.3.11 | WARN if production index creation doesn't use CONCURRENTLY | PASS/WARN |

## 8.4 Caching Strategy

| ID | Rule | Verdict |
|----|------|---------|
| 8.4.1 | PASS if Redis is configured as cache backend in production settings | PASS |
| 8.4.2 | WARN if cache keys don't follow a consistent naming convention | PASS/WARN |
| 8.4.3 | WARN if cache keys lack versioning for safe deploy invalidation | PASS/WARN |
| 8.4.4 | WARN if cached values lack explicit TTL | PASS/WARN |
| 8.4.5 | WARN if caching granularity is too coarse (whole pages vs. partial data) | PASS/WARN |
| 8.4.6 | WARN if cache invalidation is not triggered on writes | PASS/WARN |
| 8.4.7 | INFO if cache stampede protection is not implemented — optimization for high traffic | PASS/INFO |
| 8.4.8 | INFO if ORM-level caching (`django-cacheops`) is not used — manual caching is acceptable | PASS/INFO |
| 8.4.9 | INFO if expensive aggregations are not cached — depends on query frequency | PASS/INFO |
| 8.4.10 | WARN if cache hit/miss rates are not monitored | PASS/WARN |
| 8.4.11 | FAIL if PII or tokens are cached in shared Redis without encryption or scoping | PASS/FAIL |
| 8.4.12 | FAIL if per-user cache keys are not scoped — returning wrong user's data | PASS/FAIL |

## 8.5 Pagination & Result Set Control

| ID | Rule | Verdict |
|----|------|---------|
| 8.5.1 | FAIL if any list endpoint returns unbounded querysets — no pagination applied | PASS/FAIL |
| 8.5.2 | WARN if default page size is unreasonable (>100 for UI endpoints) | PASS/WARN |
| 8.5.3 | FAIL if `max_page_size` is not set — clients can request unlimited results | PASS/FAIL |
| 8.5.4 | INFO if cursor pagination is not used — offset is acceptable for moderate datasets | PASS/INFO |
| 8.5.5 | INFO if high-offset pagination is not blocked — only a concern for very large tables | PASS/INFO |
| 8.5.6 | INFO if count queries are not optimized — only a concern at scale | PASS/INFO |
| 8.5.7 | WARN if bulk export endpoints load all records into memory | PASS/WARN |
| 8.5.8 | PASS if filtering is available on list endpoints | PASS |

## 8.6 Async & Background Task Offloading

| ID | Rule | Verdict |
|----|------|---------|
| 8.6.1 | PASS if slow operations (email, external APIs) are offloaded to Celery | PASS |
| 8.6.2 | WARN if any interactive endpoint takes >200ms due to synchronous slow operations | PASS/WARN |
| 8.6.3 | PASS if Celery tasks are idempotent | PASS |
| 8.6.4 | WARN if all tasks use a single default queue — no priority segregation | PASS/WARN |
| 8.6.5 | WARN if tasks lack time limits (soft_time_limit, time_limit) | PASS/WARN |
| 8.6.6 | PASS if retry strategy uses exponential backoff | PASS |
| 8.6.7 | WARN if failed tasks have no logging or alerting | PASS/WARN |
| 8.6.8 | INFO if long-running tasks don't report progress — depends on use case | PASS/INFO |
| 8.6.9 | WARN if tasks spawn sub-tasks naively without chord/group | PASS/WARN |
| 8.6.10 | INFO if worker concurrency is not tuned per task type — default is acceptable for early stage | PASS/INFO |

## 8.7 Connection Pooling & Database Connections

| ID | Rule | Verdict |
|----|------|---------|
| 8.7.1 | WARN if CONN_MAX_AGE is 0 (default) in production — new connection per request | PASS/WARN |
| 8.7.2 | INFO if pgBouncer is not used — acceptable for moderate concurrency | PASS/INFO |
| 8.7.3 | INFO if max connections monitoring is not configured — early stage acceptable | PASS/INFO |
| 8.7.4 | INFO if connection pool size is not explicitly tuned — auto-managed is acceptable | PASS/INFO |
| 8.7.5 | WARN if background tasks hold long-lived DB connections | PASS/WARN |
| 8.7.6 | INFO if connection leak monitoring is not configured | PASS/INFO |
| 8.7.7 | INFO if read replicas are not used — acceptable for current scale | PASS/INFO |
| 8.7.8 | WARN if ATOMIC_REQUESTS impact is not understood — holds connection for full request | PASS/WARN |

## 8.8 Response Payload Optimization

| ID | Rule | Verdict |
|----|------|---------|
| 8.8.1 | WARN if response payloads include unnecessary fields the client doesn't use | PASS/WARN |
| 8.8.2 | WARN if large nested objects are always included instead of opt-in | PASS/WARN |
| 8.8.3 | WARN if gzip/brotli compression is not configured on the web server | PASS/WARN |
| 8.8.4 | FAIL if binary data is base64-encoded inline in JSON responses | PASS/FAIL |
| 8.8.5 | WARN if list responses duplicate parent data on every child item | PASS/WARN |
| 8.8.6 | INFO if sparse fieldsets are not supported — only needed for large APIs | PASS/INFO |
| 8.8.7 | INFO if ETag/Last-Modified headers are not set — depends on caching needs | PASS/INFO |
| 8.8.8 | WARN if Cache-Control headers are not set on any responses | PASS/WARN |

## 8.9 Profiling & Performance Measurement

| ID | Rule | Verdict |
|----|------|---------|
| 8.9.1 | WARN if no query profiling tool is installed in development | PASS/WARN |
| 8.9.2 | INFO if slow query logging is not enabled in PostgreSQL | PASS/INFO |
| 8.9.3 | WARN if EXPLAIN ANALYZE is not run on hot-path queries | PASS/WARN |
| 8.9.4 | INFO if CPU profiling tools are not available | PASS/INFO |
| 8.9.5 | INFO if no benchmarking baseline exists for critical endpoints | PASS/INFO |
| 8.9.6 | INFO if load testing is not performed before releases | PASS/INFO |
| 8.9.7 | INFO if latency targets are not defined | PASS/INFO |
| 8.9.8 | INFO if performance regression detection is not in CI | PASS/INFO |

## 8.10 Static Files & Media Performance

| ID | Rule | Verdict |
|----|------|---------|
| 8.10.1 | WARN if static files configuration doesn't support CDN in production | PASS/WARN |
| 8.10.2 | WARN if WhiteNoise or equivalent is not configured for static file serving | PASS/WARN |
| 8.10.3 | WARN if static files are not fingerprinted for cache busting | PASS/WARN |
| 8.10.4 | WARN if media storage is not configured for S3/cloud storage in production settings | PASS/WARN |
| 8.10.5 | WARN if private media files don't use pre-signed URLs | PASS/WARN |
| 8.10.6 | WARN if image upload processing (resize/optimize) is not implemented | PASS/WARN |
| 8.10.7 | WARN if collectstatic is not automated in deployment | PASS/WARN |

## 8.11 Memory Management

| ID | Rule | Verdict |
|----|------|---------|
| 8.11.1 | FAIL if module-level mutable state grows unboundedly across requests | PASS/FAIL |
| 8.11.2 | WARN if large files are loaded entirely into memory instead of streaming | PASS/WARN |
| 8.11.3 | WARN if querysets are evaluated prematurely and stored in variables unnecessarily | PASS/WARN |
| 8.11.4 | WARN if large queryset processing in tasks/commands doesn't use iterator() | PASS/WARN |
| 8.11.5 | INFO if worker memory recycling (--max-requests) is not configured | PASS/INFO |
| 8.11.6 | INFO if memory leak monitoring is not in place | PASS/INFO |
| 8.11.7 | WARN if in-memory data structures grow proportionally to total DB records | PASS/WARN |

## 8.12 Infrastructure-Level Performance

| ID | Rule | Verdict |
|----|------|---------|
| 8.12.1 | INFO if gunicorn worker count is not explicitly tuned | PASS/INFO |
| 8.12.2 | INFO if gunicorn worker class is default sync — acceptable for API workloads | PASS/INFO |
| 8.12.3 | PASS if nginx is configured as reverse proxy | PASS |
| 8.12.4 | INFO if nginx keepalive is not configured | PASS/INFO |
| 8.12.5 | WARN if application requires server-local state — prevents horizontal scaling | PASS/WARN |
| 8.12.6 | INFO if auto-scaling is not configured — early stage acceptable | PASS/INFO |
| 8.12.7 | WARN if Redis connection pooling is not configured | PASS/WARN |

## 8.13 Serialization Performance

| ID | Rule | Verdict |
|----|------|---------|
| 8.13.1 | FAIL if serializers re-query the database for data available on the instance | PASS/FAIL |
| 8.13.2 | WARN if nested serializers exceed 3 levels of depth | PASS/WARN |
| 8.13.3 | WARN if list serializers with `.many=True` trigger N+1 queries | PASS/WARN |
| 8.13.4 | FAIL if SerializerMethodField loops over querysets per instance | PASS/FAIL |
| 8.13.5 | PASS if read and write serializers are separated where needed | PASS |
| 8.13.6 | FAIL if `to_representation()` overrides perform database I/O | PASS/FAIL |
| 8.13.7 | INFO if fast JSON serializer (orjson) is not used — DRF default is acceptable | PASS/INFO |
| 8.13.8 | WARN if endpoints return 50+ fields when fewer would suffice | PASS/WARN |

## 8.14 Migration & Schema Change Performance

| ID | Rule | Verdict |
|----|------|---------|
| 8.14.1 | WARN if data migrations on large tables don't use batched processing | PASS/WARN |
| 8.14.2 | WARN if column additions with defaults don't use null=True first on large tables | PASS/WARN |
| 8.14.3 | INFO if multi-step deploy strategy for breaking changes is not documented | PASS/INFO |
| 8.14.4 | WARN if index creation doesn't use CONCURRENTLY for production tables | PASS/WARN |
| 8.14.5 | INFO if long-running migration estimates are not documented | PASS/INFO |
| 8.14.6 | INFO if backward-incompatible schema changes lack feature flag strategy | PASS/INFO |
| 8.14.7 | INFO if test migrations only run against empty tables | PASS/INFO |
