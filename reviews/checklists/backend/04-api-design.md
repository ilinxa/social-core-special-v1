# 04 — API Design (DRF) Checklist

## 4.1 URL Structure & Versioning

- [ ] All API endpoints are prefixed with `/api/` — no bare resource URLs at root
- [ ] API versioning is implemented — `/api/v1/`, `/api/v2/` — not unversioned
- [ ] Versioning strategy is consistent — URL path versioning preferred over header versioning for clarity
- [ ] Root `urls.py` only includes app-level URL configs via `include()` — no inline endpoint definitions
- [ ] Each app has its own `urls.py` — not all routes defined in one global file
- [ ] URL patterns use **nouns not verbs** — `/api/v1/orders/` not `/api/v1/get-orders/`
- [ ] Resource names are **plural** — `/users/` not `/user/`
- [ ] Nested routes are shallow — max **one level of nesting** (`/orders/{id}/items/` is fine, `/orders/{id}/items/{id}/comments/` is not)
- [ ] Trailing slash policy is consistent across all endpoints — either always or never
- [ ] No endpoint names conflict or shadow each other across apps

## 4.2 ViewSet & View Design

- [ ] **`ModelViewSet`** is used only when all CRUD actions are genuinely needed — individual mixins otherwise
- [ ] **`GenericAPIView`** with mixins is used for partial CRUD — not `ModelViewSet` with half the actions disabled
- [ ] **`APIView`** is used only for non-resource endpoints (e.g. health check, token refresh)
- [ ] No business logic inside views — views only handle request/response orchestration
- [ ] No direct ORM calls inside views — all DB access goes through service layer or queryset methods
- [ ] `get_queryset()` is overridden instead of setting `queryset` as a class attribute when the queryset is dynamic
- [ ] `get_serializer_class()` is overridden when different serializers are needed per action
- [ ] `get_permissions()` is overridden when permission logic differs per action — not hardcoded on class
- [ ] Action-specific logic uses `@action` decorator with correct `detail`, `methods`, and `url_path`
- [ ] No `@action` used where a proper resource endpoint would be cleaner
- [ ] ViewSets are registered via **Router** — no manual URL pattern for ViewSet endpoints

## 4.3 Serializer Design

- [ ] Each serializer has a **single responsibility** — read serializers and write serializers are separated where complexity warrants
- [ ] **Input serializers** (write) and **output serializers** (read) are distinct for complex resources
- [ ] `Meta.fields` explicitly lists all fields — no `fields = '__all__'` in production serializers
- [ ] `Meta.read_only_fields` is set for auto-managed fields (`id`, `created_at`, `updated_at`)
- [ ] Sensitive fields (`password`, `token`, `secret_key`) are **never** in output serializers
- [ ] **Nested serializers** are read-only by default — writable nested serializers have explicit `create()`/`update()` overrides
- [ ] `SerializerMethodField` is used sparingly — not as a workaround for poor model design
- [ ] `validate_<field>()` is used for field-level validation
- [ ] `validate()` is used for cross-field validation — not duplicating logic across both
- [ ] No database queries inside `validate_<field>()` that could cause N+1 in list serialization
- [ ] `to_representation()` is overridden only when field-level customization isn't sufficient
- [ ] Serializer `source` argument is used to remap field names cleanly — not aliased via `to_representation()`
- [ ] Depth is never set via `Meta.depth` in production — always explicit nested serializers

## 4.4 Response Shape & Consistency

- [ ] All successful responses follow a **consistent envelope structure** across the entire API
- [ ] List responses always include pagination metadata (`count`, `next`, `previous`, `results`)
- [ ] Single resource responses return the resource directly — not wrapped in an unnecessary `data` key
- [ ] Empty list responses return `[]` — not `null` or `404`
- [ ] Created resources return **`201 Created`** with the full resource in the body — not just `200 OK`
- [ ] Delete endpoints return **`204 No Content`** — not `200 OK` with a message body
- [ ] No endpoint returns `200 OK` for an operation that partially failed
- [ ] Response field names use **`camelCase`** or **`snake_case`** consistently across all endpoints — never mixed
- [ ] Timestamps are returned in **ISO 8601 format** (`2024-01-15T10:30:00Z`) — not Unix timestamps or locale strings
- [ ] IDs are returned as **strings** if UUIDs — not mixed string/integer across endpoints

## 4.5 Error Response Design

- [ ] All error responses follow a **single consistent error schema** across the entire API
- [ ] Error schema includes at minimum: `code`, `message`, and `detail` (or `errors` for field-level)
- [ ] **Field-level validation errors** return the field name as key with error messages as value
- [ ] **Non-field errors** are returned under a consistent key (`non_field_errors` or `detail`)
- [ ] Error `code` is a **machine-readable string** (`INVALID_EMAIL`, `INSUFFICIENT_FUNDS`) — not just an HTTP status
- [ ] `400 Bad Request` is used for **validation failures** — not `422` (unless explicitly adopted)
- [ ] `401 Unauthorized` is used for **unauthenticated** requests — not `403`
- [ ] `403 Forbidden` is used for **authenticated but unauthorized** requests — not `401`
- [ ] `404 Not Found` is returned for missing resources — not `400` with a "not found" message
- [ ] `409 Conflict` is used for **duplicate resource** or **state conflict** errors
- [ ] `429 Too Many Requests` is returned with a `Retry-After` header for rate-limited requests
- [ ] `500 Internal Server Error` never leaks stack traces or internal details to the client
- [ ] A **custom exception handler** is registered in DRF settings to normalize all error shapes

## 4.6 Authentication

- [ ] Authentication classes are set **globally** in `DEFAULT_AUTHENTICATION_CLASSES` — not per-view unless overriding
- [ ] JWT tokens have a **short expiry** for access tokens (`15min`–`1hr`) and longer for refresh (`7–30 days`)
- [ ] Token refresh endpoint is present and documented
- [ ] Token blacklisting on logout is implemented — not just discarding the token client-side
- [ ] Authentication errors return the correct `WWW-Authenticate` header
- [ ] Multiple authentication schemes (JWT + session) are not mixed without a clear documented reason
- [ ] API key authentication (if used) validates keys in constant time — no timing attack vulnerability
- [ ] Unauthenticated access to protected endpoints returns `401` — not `403` or `404`

## 4.7 Permissions

- [ ] Permission classes are set **globally** in `DEFAULT_PERMISSION_CLASSES` — defaulting to `IsAuthenticated`
- [ ] No endpoint is accidentally public due to missing permission class
- [ ] Custom permission classes are used — no `if request.user.role == 'admin':` logic inside views
- [ ] **Object-level permissions** are enforced via `check_object_permissions()` — not manual `if obj.owner != request.user`
- [ ] `get_queryset()` scopes results to the requesting user — no relying solely on object-level permission for data isolation
- [ ] Permission classes have meaningful `message` attributes for clear error responses
- [ ] Admin-only endpoints use `IsAdminUser` or a custom equivalent — not ad-hoc checks
- [ ] Permission logic is **unit tested** independently from views

## 4.8 Pagination

- [ ] Pagination is set **globally** in `DEFAULT_PAGINATION_CLASS` — not applied per-view inconsistently
- [ ] `PageNumberPagination` or `CursorPagination` is used — `LimitOffsetPagination` only where client-controlled page size is required
- [ ] `PAGE_SIZE` is set to a **sensible default** (e.g. `20`) — not `100` or `1000`
- [ ] `max_page_size` is set when client can control page size — no unbounded `?limit=99999`
- [ ] **Cursor pagination** is used for large, frequently updated datasets (feeds, event logs)
- [ ] Pagination metadata (`count`, `next`, `previous`) is always present in list responses
- [ ] No endpoint returns an **unbounded queryset** without pagination
- [ ] Pagination class is explicitly disabled only for endpoints where returning all records is intentional and safe

## 4.9 Filtering, Search & Ordering

- [ ] `django-filter` is used for structured filtering — no manual `request.query_params.get()` chains in views
- [ ] `FilterSet` classes are defined per resource — not inline filter definitions
- [ ] Filterable fields are **explicitly whitelisted** in `FilterSet.Meta.fields` — no `fields = '__all__'`
- [ ] Search is implemented via `SearchFilter` with explicit `search_fields` defined
- [ ] Ordering is implemented via `OrderingFilter` with explicit `ordering_fields` defined
- [ ] Default ordering is set via `ordering` attribute — not relying on DB-level `Meta.ordering`
- [ ] Filtering on **related fields** uses `__` traversal correctly and is indexed
- [ ] No filtering that triggers unbounded table scans on large tables without indexes
- [ ] Filter parameters are **documented** in the OpenAPI schema

## 4.10 Throttling & Rate Limiting

- [ ] Throttling is configured globally in `DEFAULT_THROTTLE_CLASSES`
- [ ] **Anonymous** and **authenticated** users have separate throttle rates
- [ ] Auth endpoints (`/login/`, `/token/`, `/register/`) have **stricter throttle rates**
- [ ] Custom throttle classes exist for sensitive operations (password reset, OTP, etc.)
- [ ] `Retry-After` header is returned when a request is throttled
- [ ] Throttle rates are stored in configuration — not hardcoded in throttle classes
- [ ] Redis-backed throttling is used in production — not in-memory (doesn't work across multiple workers)

## 4.11 OpenAPI Schema & Documentation

- [ ] `drf-spectacular` or `drf-yasg` is integrated and auto-generates the OpenAPI schema
- [ ] Schema is served at `/api/schema/` and UI at `/api/docs/` in non-production environments
- [ ] All endpoints have `@extend_schema` decorators with **summary**, **description**, and **response types**
- [ ] Request body schemas are accurate — no generic `object` types
- [ ] All possible **error responses** are documented with their status codes
- [ ] Authentication requirements are documented per endpoint
- [ ] Enum fields show allowed values in the schema — not just `string`
- [ ] Schema is **validated in CI** — schema drift fails the build
- [ ] Deprecated endpoints are marked with `deprecated=True` — not silently removed

## 4.12 API Versioning Strategy

- [ ] A documented policy exists for when and how new versions are introduced
- [ ] **Breaking changes** always bump the version — never silently breaking existing clients
- [ ] Old versions have a documented **sunset date** and return a `Deprecation` header
- [ ] Version routing is handled at the URL level — not inside view logic with `if version == 'v1':`
- [ ] Shared business logic between versions lives in the service layer — not duplicated per version
- [ ] At least one **version of the API is stable** and not subject to breaking changes

## 4.13 Content Negotiation & Renderers

- [ ] `DEFAULT_RENDERER_CLASSES` is set explicitly — `JSONRenderer` for production, `BrowsableAPIRenderer` only in dev
- [ ] `BrowsableAPIRenderer` is **disabled** in production — no HTML API browser exposed
- [ ] JSON is the default response format — no XML/YAML unless explicitly required
- [ ] Content-Type header is set correctly on all responses — `application/json`
- [ ] `DEFAULT_PARSER_CLASSES` includes `JSONParser` and `MultiPartParser`/`FormParser` only where file uploads exist

## 4.14 File Upload & Multipart Handling

- [ ] File upload endpoints use `MultiPartParser` — not expecting base64-encoded files in JSON
- [ ] Uploaded file **size limits** are enforced — `DATA_UPLOAD_MAX_MEMORY_SIZE` or per-view limits
- [ ] Uploaded file **type validation** exists — MIME type and/or extension whitelisting
- [ ] Uploaded files are stored via a **storage backend** (S3, local) — not saved to the DB as binary
- [ ] Upload progress is trackable for large files if applicable
- [ ] File names are **sanitized** — no path traversal via crafted filenames

## 4.15 HATEOAS & Discoverability

- [ ] Detail responses include a **self URL** (`url` field) for the resource
- [ ] Related resources include **hyperlinks** where appropriate — not just bare IDs
- [ ] API root endpoint (`/api/v1/`) returns a directory of available resources (if desired)
- [ ] Pagination `next` / `previous` links are full URLs — not relative paths or page numbers only
