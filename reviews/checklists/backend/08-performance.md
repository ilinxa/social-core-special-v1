# 08 — Performance Checklist

## 8.1 Query Optimization Fundamentals

- [ ] **N+1 query problem** is eliminated across all endpoints — verified via `django-silk` or `nplusone` in development
- [ ] `select_related()` is used for all **ForeignKey and OneToOne** traversals in querysets
- [ ] `prefetch_related()` is used for all **ManyToMany and reverse FK** traversals in querysets
- [ ] `Prefetch()` object with custom querysets is used when prefetching needs **filtering or ordering**
- [ ] No ORM calls inside **serializer `to_representation()`** — all data fetched upfront in the view's queryset
- [ ] No ORM calls inside **`SerializerMethodField`** methods — preloaded via annotations or prefetch
- [ ] No ORM calls inside **model `__str__()`** — causes N+1 in admin list views and logging
- [ ] No ORM calls inside **template rendering** (if any templates exist) — data fully prepared in view
- [ ] Critical endpoints have **query count assertions** in tests — `assertNumQueries()` used to lock in expected counts
- [ ] Query count is verified to remain **constant regardless of result set size** — not O(n) with records returned

## 8.2 QuerySet Efficiency

- [ ] `.values()` or `.values_list()` is used when **full model instances are not needed** — e.g. for aggregations or ID lists
- [ ] `.only()` is used on **fat models** where only a subset of fields is needed in a given context
- [ ] `.defer()` is used for **large fields** (JSONField, TextField) not needed in list views
- [ ] `.count()` is used instead of `len(queryset)` — avoids loading all records into memory
- [ ] `.exists()` is used instead of `.count() > 0` or `bool(queryset)` for existence checks
- [ ] `.bulk_create()` is used for **batch inserts** — not looping `Model.objects.create()` per item
- [ ] `.bulk_update()` is used for **batch updates** — not looping `.save()` per item
- [ ] `.update()` is used for **mass field updates** — not fetching records, mutating, and saving individually
- [ ] `.delete()` at queryset level is used for **mass deletion** — not fetching and deleting one by one
- [ ] `.iterator()` is used for **large queryset iteration** — avoids loading entire result set into memory
- [ ] `.annotate()` is used to push **computed values into the DB** — not computed in Python after fetching
- [ ] `.aggregate()` is used for **summary statistics** — not fetching all records and summing in Python

## 8.3 Database Indexing Strategy

- [ ] All **filter fields** used in hot query paths have indexes — verified with `EXPLAIN ANALYZE`
- [ ] All **ordering fields** used in paginated endpoints have indexes
- [ ] All **FK fields** have indexes — Django adds these by default, verify none are accidentally disabled
- [ ] **Composite indexes** cover multi-column `filter()` + `order_by()` combinations on hot paths
- [ ] **Partial indexes** are used where filtering on a low-cardinality condition (e.g. `WHERE status = 'active'`)
- [ ] **GIN indexes** are present on `JSONField` columns that are queried by key or value
- [ ] **GIN or GiST indexes** are present on full-text search columns
- [ ] **`pg_trgm` indexes** are present on columns using `LIKE` or trigram similarity searches
- [ ] Index usage is verified with `EXPLAIN ANALYZE` — no sequential scans on large tables in hot paths
- [ ] **Over-indexing** is avoided on write-heavy tables — each index has a clear read-path justification
- [ ] Indexes are created with `CREATE INDEX CONCURRENTLY` on production tables — no table locks during migration

## 8.4 Caching Strategy

- [ ] Redis is used as the **cache backend** in production — not in-memory cache (doesn't scale across workers)
- [ ] **Cache keys** follow a consistent naming convention — `<app>:<resource>:<identifier>:<version>`
- [ ] Cache keys include a **version or hash** to allow safe invalidation on deploy
- [ ] **TTL is set on every cached value** — no infinite TTL unless explicitly justified
- [ ] Cached values are the **right granularity** — not caching entire pages when only part of the data changes
- [ ] **Cache invalidation** is triggered on write — not relying solely on TTL expiry for consistency
- [ ] **Cache stampede** (thundering herd) is prevented — use probabilistic expiry, locking, or background refresh
- [ ] **`django-cacheops`** or equivalent is used for ORM-level caching where appropriate
- [ ] Expensive aggregations and report queries are **cached with longer TTLs** and refreshed asynchronously
- [ ] Cache **hit/miss rates** are monitored — low hit rate signals a broken caching strategy
- [ ] Sensitive data (PII, tokens) is **never cached** in shared cache backends
- [ ] Per-user caches use **user-scoped keys** — no shared cache returning wrong user's data

## 8.5 Pagination & Result Set Control

- [ ] **All list endpoints are paginated** — no endpoint returns an unbounded queryset
- [ ] Default page size is **sensible for the use case** — `20` for UI lists, smaller for mobile, larger for bulk exports
- [ ] **`max_page_size`** is set — clients cannot request `?limit=1000000`
- [ ] **Cursor pagination** is used for large, append-heavy datasets — not offset pagination (degrades at high offsets)
- [ ] Offset pagination beyond a **safe threshold** (e.g. page 1000+) is blocked or warned against
- [ ] **Count queries** in offset pagination are cached or skipped for large tables — `COUNT(*)` on millions of rows is slow
- [ ] Bulk export endpoints use **streaming responses** or async job pattern — not loading millions of records into memory
- [ ] API consumers are **not expected to paginate through all results** to find one item — filtering is available

## 8.6 Async & Background Task Offloading

- [ ] All **slow operations** (>200ms) are offloaded to Celery — emails, PDF generation, external API calls, reports
- [ ] **Request cycle is kept under 200ms** for interactive endpoints — long-running work is async
- [ ] Celery tasks are **idempotent** — safe to retry without duplicate side effects
- [ ] Celery **task queues are segregated** by priority — high-priority tasks don't queue behind bulk jobs
- [ ] **Task time limits** (`soft_time_limit`, `time_limit`) are set on all tasks — no runaway tasks
- [ ] **Task retry strategy** uses exponential backoff — not fixed interval retries
- [ ] **Dead letter queue** or failure handling exists — failed tasks are logged and alertable
- [ ] Long-running tasks report **progress** via Redis or DB — not a black box to the caller
- [ ] Tasks that fan out to many sub-tasks use **Celery chord or group** — not spawning tasks inside tasks naively
- [ ] **Celery worker concurrency** is tuned per task type — CPU-bound vs I/O-bound workers configured separately

## 8.7 Connection Pooling & Database Connections

- [ ] **`CONN_MAX_AGE`** is set to a non-zero value in production — persistent connections reused across requests
- [ ] **pgBouncer** is used in transaction pooling mode for high-concurrency deployments
- [ ] Database **max connections** limit is not exceeded under peak load — verified via monitoring
- [ ] Connection pool size is **tuned to worker count** — `(workers × threads) < max_db_connections`
- [ ] No **long-held connections** from background tasks blocking connection pool
- [ ] **Connection leaks** are monitored — connection count doesn't grow unboundedly over time
- [ ] Read-heavy endpoints use a **read replica** where available — reducing load on the primary
- [ ] **`ATOMIC_REQUESTS`** setting is understood — if enabled, every request holds a DB connection for its full duration

## 8.8 Response Payload Optimization

- [ ] Response payloads include **only fields the client needs** — no over-fetching of unused data
- [ ] Large nested objects are **not included by default** — provided via a separate endpoint or opt-in parameter
- [ ] **`gzip` or `brotli` compression** is enabled on the web server for API responses
- [ ] Binary data (images, files) is **not base64-encoded in JSON responses** — served via direct URL to storage
- [ ] Response payloads for list endpoints are **not duplicating parent data** on every child item
- [ ] **Sparse fieldsets** (`?fields=id,name,email`) are supported for clients that need only a subset
- [ ] `ETag` or `Last-Modified` headers are set on cacheable responses — enabling client-side conditional requests
- [ ] `Cache-Control` headers are correctly set — public responses cached at CDN, private responses not

## 8.9 Profiling & Performance Measurement

- [ ] **`django-silk`** or **`django-debug-toolbar`** is installed in development for query profiling
- [ ] Slow query logging is **enabled in PostgreSQL** — `log_min_duration_statement` set to a threshold (e.g. 100ms)
- [ ] **`EXPLAIN ANALYZE`** is run on all queries in hot code paths during development
- [ ] **`py-spy`** or **`cProfile`** is used to profile CPU-bound bottlenecks when needed
- [ ] A **benchmarking baseline** exists for critical endpoints — response times tracked across releases
- [ ] **Load testing** (Locust, k6, or Artillery) is run against staging before major releases
- [ ] **Apdex score** or p95/p99 latency targets are defined and monitored in production
- [ ] Performance regressions in CI are caught — automated benchmarks fail if latency degrades beyond threshold

## 8.10 Static Files & Media Performance

- [ ] Static files are served via **CDN** in production — not via Django's development server
- [ ] **WhiteNoise** is used if serving static files directly from the app — with compression and caching headers
- [ ] Static files are **fingerprinted** (content hash in filename) — enabling aggressive CDN caching with instant invalidation
- [ ] Media files are stored in **S3 or equivalent** — not on the application server's local disk
- [ ] Media file URLs are **pre-signed** for private files — not publicly accessible by default
- [ ] Image uploads are **resized and optimized** server-side — not serving 10MB originals to clients
- [ ] `collectstatic` runs as part of the **CI/CD deploy pipeline** — not a manual step

## 8.11 Memory Management

- [ ] No **large objects held in memory** across requests — no module-level mutable state growing unboundedly
- [ ] **Large file processing** uses streaming — not loading entire file into memory with `file.read()`
- [ ] **QuerySet evaluation** is deferred until needed — not evaluated prematurely and stored in variables
- [ ] **`iterator()`** is used when processing large querysets in management commands or Celery tasks
- [ ] Memory usage is **monitored per worker** — workers are recycled after a configurable number of requests (`--max-requests` in gunicorn)
- [ ] **Memory leaks** are detected via monitoring — RSS memory per worker not growing indefinitely
- [ ] Large **in-memory data structures** (dicts, lists) are bounded — not growing proportionally to total DB records

## 8.12 Infrastructure-Level Performance

- [ ] **Gunicorn worker count** is tuned — `(2 × CPU cores) + 1` for sync workers
- [ ] **Gunicorn worker class** is appropriate — `gevent` or `uvicorn` for async/I/O-heavy workloads
- [ ] **nginx** sits in front of gunicorn — handling slow clients, buffering, and static files
- [ ] **Keepalive** is configured on nginx — reducing TCP handshake overhead for repeated requests
- [ ] **Horizontal scaling** is possible — no server-local state, no sticky sessions required
- [ ] **Auto-scaling** triggers are defined — CPU and request queue depth used as scaling signals
- [ ] **Redis connection pooling** is configured — not opening a new Redis connection per request

## 8.13 Serialization Performance

- [ ] Serializers do not **re-query the database** for data already available on the instance
- [ ] Deeply nested serializers have a **depth limit** — not serializing 5+ levels of related objects
- [ ] List serializers use `.many=True` with **optimized querysets** — not N+1 serialization
- [ ] `SerializerMethodField` computations are **O(1)** — not looping over querysets per instance
- [ ] Heavy read-only serializers are **separate from write serializers** — read path has no write validation overhead
- [ ] `to_representation()` overrides do **not perform I/O** — only data transformation
- [ ] For very high-throughput endpoints, `orjson` or equivalent **fast JSON serializer** is considered
- [ ] Serializer field count per endpoint is **reasonable** — not returning 50+ fields when 10 would suffice

## 8.14 Migration & Schema Change Performance

- [ ] Data migrations on large tables use **batched processing** — not loading all rows at once
- [ ] Column additions use `null=True` first — **not locking the table** with a default value on millions of rows
- [ ] Renaming or removing columns uses a **multi-step deploy** — not breaking active queries during rollout
- [ ] Index creation uses **`CONCURRENTLY`** in PostgreSQL — declared via `AddIndex` with `opclasses` or raw SQL
- [ ] Long-running migrations have an **estimated time** documented — DBA-approved for production
- [ ] Backward-incompatible schema changes are **behind a feature flag** or multi-phase migration
- [ ] Test migrations run against a **representative data volume** — not just on empty tables
