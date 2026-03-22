# 04 — API Design (DRF) Rules

Pass/fail criteria for each checklist item. Apply these when auditing the codebase.

---

## 4.1 URL Structure & Versioning

| ID | Rule | Verdict |
|----|------|---------|
| 4.1.1 | FAIL if any API endpoint is served at a bare path without `/api/` prefix | PASS/FAIL |
| 4.1.2 | FAIL if API endpoints are unversioned — no `/v1/` or equivalent prefix | PASS/FAIL |
| 4.1.3 | WARN if versioning mixes URL path and header strategies | PASS/WARN |
| 4.1.4 | FAIL if root `urls.py` contains view function/class definitions | PASS/FAIL |
| 4.1.5 | FAIL if all routes are defined in a single global `urls.py` — no per-app split | PASS/FAIL |
| 4.1.6 | WARN if URL patterns use verbs (`/get-users/`, `/create-order/`) instead of nouns | PASS/WARN |
| 4.1.7 | WARN if resource names are inconsistently singular/plural | PASS/WARN |
| 4.1.8 | WARN if nesting exceeds 2 levels (resource/id/sub-resource/id/sub-sub-resource) | PASS/WARN |
| 4.1.9 | WARN if trailing slash policy is inconsistent across endpoints | PASS/WARN |
| 4.1.10 | FAIL if endpoint names conflict or shadow each other causing routing errors | PASS/FAIL |

## 4.2 ViewSet & View Design

| ID | Rule | Verdict |
|----|------|---------|
| 4.2.1 | WARN if `ModelViewSet` is used but half its actions are disabled via `http_method_names` | PASS/WARN |
| 4.2.2 | WARN if `GenericAPIView` with 4+ mixins is used instead of `ModelViewSet` | PASS/WARN |
| 4.2.3 | WARN if `APIView` is used for standard CRUD endpoints that should use generics | PASS/WARN |
| 4.2.4 | FAIL if business logic (calculations, state transitions, validation beyond serializer) is inside a view | PASS/FAIL |
| 4.2.5 | FAIL if views contain direct ORM queries (`Model.objects.filter()`) instead of using service/selector layer | PASS/FAIL |
| 4.2.6 | WARN if `queryset = Model.objects.all()` is used where queryset should be dynamic | PASS/WARN |
| 4.2.7 | WARN if multiple serializer classes per view are handled via `if` instead of `get_serializer_class()` | PASS/WARN |
| 4.2.8 | WARN if per-action permissions are handled via `if` instead of `get_permissions()` | PASS/WARN |
| 4.2.9 | INFO if `@action` is used — only notable if it replaces what should be a separate view | PASS/INFO |
| 4.2.10 | INFO if ViewSets without Routers — only problematic if URL patterns are messy | PASS/INFO |

## 4.3 Serializer Design

| ID | Rule | Verdict |
|----|------|---------|
| 4.3.1 | WARN if a single serializer handles both complex read and write — separate serializers preferred | PASS/WARN |
| 4.3.2 | WARN if no distinction exists between input and output serializers for resources with >10 fields | PASS/WARN |
| 4.3.3 | FAIL if `fields = '__all__'` is used in any production serializer | PASS/FAIL |
| 4.3.4 | WARN if auto-managed fields (`id`, `created_at`, `updated_at`) are not in `read_only_fields` | PASS/WARN |
| 4.3.5 | FAIL if sensitive fields (passwords, tokens, secrets) appear in output serializers | PASS/FAIL |
| 4.3.6 | WARN if nested writable serializers lack explicit `create()`/`update()` methods | PASS/WARN |
| 4.3.7 | WARN if `SerializerMethodField` is used for data that could be a model property or annotation | PASS/WARN |
| 4.3.8 | PASS if `validate_<field>()` is used for field-level validation | PASS |
| 4.3.9 | PASS if `validate()` is used for cross-field validation | PASS |
| 4.3.10 | FAIL if `validate_<field>()` contains DB queries in a serializer used in list views | PASS/FAIL |
| 4.3.11 | WARN if `to_representation()` is overridden for simple field renaming (use `source` instead) | PASS/WARN |
| 4.3.12 | PASS if `source` argument is used correctly for field remapping | PASS |
| 4.3.13 | FAIL if `Meta.depth` is set on any production serializer | PASS/FAIL |

## 4.4 Response Shape & Consistency

| ID | Rule | Verdict |
|----|------|---------|
| 4.4.1 | WARN if successful response structures differ between apps without documented reason | PASS/WARN |
| 4.4.2 | FAIL if list endpoints return data without pagination metadata | PASS/FAIL |
| 4.4.3 | WARN if detail responses are unnecessarily wrapped in a `data` key | PASS/WARN |
| 4.4.4 | FAIL if empty list responses return `null` or `404` instead of `[]` | PASS/FAIL |
| 4.4.5 | WARN if POST/create endpoints return `200` instead of `201` | PASS/WARN |
| 4.4.6 | WARN if DELETE endpoints return `200` with body instead of `204 No Content` | PASS/WARN |
| 4.4.7 | FAIL if any endpoint returns `200 OK` for a partially failed operation | PASS/FAIL |
| 4.4.8 | FAIL if response field naming mixes `camelCase` and `snake_case` across endpoints | PASS/FAIL |
| 4.4.9 | FAIL if timestamps are returned in non-ISO 8601 format | PASS/FAIL |
| 4.4.10 | WARN if UUID IDs are returned as integers in some places and strings in others | PASS/WARN |

## 4.5 Error Response Design

| ID | Rule | Verdict |
|----|------|---------|
| 4.5.1 | FAIL if error response structures differ between apps | PASS/FAIL |
| 4.5.2 | WARN if error responses lack a machine-readable `code` field | PASS/WARN |
| 4.5.3 | PASS if field-level errors use field name as key | PASS |
| 4.5.4 | PASS if non-field errors use a consistent key (`non_field_errors` or `detail`) | PASS |
| 4.5.5 | WARN if error codes are HTTP status numbers instead of semantic strings | PASS/WARN |
| 4.5.6 | WARN if `422` is used for validation errors instead of `400` (unless deliberately chosen) | PASS/WARN |
| 4.5.7 | FAIL if `403` is returned for unauthenticated requests (should be `401`) | PASS/FAIL |
| 4.5.8 | FAIL if `401` is returned for authenticated-but-unauthorized requests (should be `403`) | PASS/FAIL |
| 4.5.9 | WARN if `400` is returned for "not found" scenarios instead of `404` | PASS/WARN |
| 4.5.10 | PASS if `409` is used for conflict/duplicate errors | PASS |
| 4.5.11 | WARN if throttled responses lack `Retry-After` header | PASS/WARN |
| 4.5.12 | FAIL if `500` responses leak stack traces, file paths, or internal details | PASS/FAIL |
| 4.5.13 | FAIL if no custom exception handler is registered in DRF settings | PASS/FAIL |

## 4.6 Authentication

| ID | Rule | Verdict |
|----|------|---------|
| 4.6.1 | WARN if authentication classes are set per-view instead of globally with overrides | PASS/WARN |
| 4.6.2 | WARN if JWT access token expiry exceeds 1 hour | PASS/WARN |
| 4.6.3 | FAIL if no token refresh mechanism exists | PASS/FAIL |
| 4.6.4 | FAIL if logout only discards the token client-side without server-side invalidation | PASS/FAIL |
| 4.6.5 | WARN if `WWW-Authenticate` header is missing from `401` responses | PASS/WARN |
| 4.6.6 | WARN if JWT and session auth are both active without documented reason | PASS/WARN |
| 4.6.7 | FAIL if API key validation is vulnerable to timing attacks (non-constant-time comparison) | PASS/FAIL |
| 4.6.8 | FAIL if protected endpoints return `403` or `404` for unauthenticated requests | PASS/FAIL |

## 4.7 Permissions

| ID | Rule | Verdict |
|----|------|---------|
| 4.7.1 | FAIL if `DEFAULT_PERMISSION_CLASSES` is not set or defaults to `AllowAny` | PASS/FAIL |
| 4.7.2 | FAIL if any endpoint is accidentally public with no permission class | PASS/FAIL |
| 4.7.3 | FAIL if permission logic is inline in views (`if request.user.role == 'admin':`) | PASS/FAIL |
| 4.7.4 | WARN if object-level permissions use manual ownership checks instead of `check_object_permissions()` | PASS/WARN |
| 4.7.5 | WARN if `get_queryset()` does not scope results to the requesting user where needed | PASS/WARN |
| 4.7.6 | WARN if permission classes lack custom `message` attributes | PASS/WARN |
| 4.7.7 | WARN if admin-only endpoints use ad-hoc checks instead of `IsAdminUser` or custom class | PASS/WARN |
| 4.7.8 | WARN if permission logic has no dedicated unit tests | PASS/WARN |

## 4.8 Pagination

| ID | Rule | Verdict |
|----|------|---------|
| 4.8.1 | WARN if pagination is applied per-view instead of globally | PASS/WARN |
| 4.8.2 | WARN if `LimitOffsetPagination` is used without explicit `max_limit` | PASS/WARN |
| 4.8.3 | WARN if default `PAGE_SIZE` exceeds 50 for general endpoints | PASS/WARN |
| 4.8.4 | FAIL if client-controlled page size has no `max_page_size` cap | PASS/FAIL |
| 4.8.5 | INFO if cursor pagination is not used for feeds/event logs — only relevant for high-volume streams | PASS/INFO |
| 4.8.6 | FAIL if list responses lack `count`, `next`, `previous` fields | PASS/FAIL |
| 4.8.7 | FAIL if any list endpoint returns unbounded results without pagination | PASS/FAIL |
| 4.8.8 | PASS if pagination is explicitly disabled with documented reason | PASS |

## 4.9 Filtering, Search & Ordering

| ID | Rule | Verdict |
|----|------|---------|
| 4.9.1 | WARN if manual `request.query_params.get()` chains exist where `django-filter` would be cleaner | PASS/WARN |
| 4.9.2 | WARN if filter logic is defined inline in views instead of `FilterSet` classes | PASS/WARN |
| 4.9.3 | FAIL if `fields = '__all__'` is used in any FilterSet | PASS/FAIL |
| 4.9.4 | WARN if search functionality exists but `search_fields` is not explicitly defined | PASS/WARN |
| 4.9.5 | WARN if ordering is implemented but `ordering_fields` is not explicitly whitelisted | PASS/WARN |
| 4.9.6 | WARN if views rely on model `Meta.ordering` without explicit view-level default | PASS/WARN |
| 4.9.7 | WARN if related-field filtering is not indexed in the database | PASS/WARN |
| 4.9.8 | FAIL if filtering triggers full table scans on large tables | PASS/FAIL |
| 4.9.9 | WARN if filter parameters are not documented in OpenAPI schema | PASS/WARN |

## 4.10 Throttling & Rate Limiting

| ID | Rule | Verdict |
|----|------|---------|
| 4.10.1 | WARN if no throttling is configured at all | PASS/WARN |
| 4.10.2 | WARN if anonymous and authenticated users share the same throttle rate | PASS/WARN |
| 4.10.3 | WARN if auth endpoints have no stricter throttle rate than general endpoints | PASS/WARN |
| 4.10.4 | WARN if sensitive operations lack custom throttle classes | PASS/WARN |
| 4.10.5 | WARN if throttled responses lack `Retry-After` header | PASS/WARN |
| 4.10.6 | WARN if throttle rates are hardcoded in classes instead of settings | PASS/WARN |
| 4.10.7 | WARN if in-memory throttle cache is used in production (doesn't scale across workers) | PASS/WARN |

## 4.11 OpenAPI Schema & Documentation

| ID | Rule | Verdict |
|----|------|---------|
| 4.11.1 | WARN if no OpenAPI schema generator is installed | PASS/WARN |
| 4.11.2 | WARN if schema/docs endpoint is not available in development | PASS/WARN |
| 4.11.3 | WARN if endpoints lack `@extend_schema` with summary and response types | PASS/WARN |
| 4.11.4 | WARN if request body schemas show generic `object` types | PASS/WARN |
| 4.11.5 | WARN if error responses are not documented in the schema | PASS/WARN |
| 4.11.6 | WARN if authentication requirements are not in the schema | PASS/WARN |
| 4.11.7 | WARN if enum fields don't show allowed values in schema | PASS/WARN |
| 4.11.8 | INFO if schema is not validated in CI — recommended but not required | PASS/INFO |
| 4.11.9 | WARN if deprecated endpoints are not marked in schema | PASS/WARN |

## 4.12 API Versioning Strategy

| ID | Rule | Verdict |
|----|------|---------|
| 4.12.1 | WARN if no documented API versioning policy exists | PASS/WARN |
| 4.12.2 | FAIL if breaking changes are deployed without a version bump | PASS/FAIL |
| 4.12.3 | WARN if deprecated versions lack sunset dates or Deprecation headers | PASS/WARN |
| 4.12.4 | FAIL if version routing uses `if version == 'v1':` inside view methods | PASS/FAIL |
| 4.12.5 | WARN if business logic is duplicated across versions instead of shared via service layer | PASS/WARN |
| 4.12.6 | PASS if at least one stable API version exists | PASS |

## 4.13 Content Negotiation & Renderers

| ID | Rule | Verdict |
|----|------|---------|
| 4.13.1 | WARN if `DEFAULT_RENDERER_CLASSES` is not explicitly set | PASS/WARN |
| 4.13.2 | FAIL if `BrowsableAPIRenderer` is enabled in production settings | PASS/FAIL |
| 4.13.3 | PASS if JSON is the default response format | PASS |
| 4.13.4 | WARN if Content-Type header is missing or incorrect on responses | PASS/WARN |
| 4.13.5 | WARN if `MultiPartParser` is included globally when only specific endpoints need it | PASS/WARN |

## 4.14 File Upload & Multipart Handling

| ID | Rule | Verdict |
|----|------|---------|
| 4.14.1 | WARN if file upload endpoints accept base64 in JSON instead of multipart | PASS/WARN |
| 4.14.2 | FAIL if no upload file size limit is enforced | PASS/FAIL |
| 4.14.3 | WARN if uploaded files lack MIME type or extension validation | PASS/WARN |
| 4.14.4 | FAIL if uploaded files are stored as binary in the database | PASS/FAIL |
| 4.14.5 | WARN if file names are not sanitized (path traversal risk) | PASS/WARN |

## 4.15 HATEOAS & Discoverability

| ID | Rule | Verdict |
|----|------|---------|
| 4.15.1 | INFO if detail responses lack a `url` / self-link field — optional but recommended | PASS/INFO |
| 4.15.2 | INFO if related resources only include bare IDs without hyperlinks — optional | PASS/INFO |
| 4.15.3 | INFO if API root endpoint has no directory of available resources — optional | PASS/INFO |
| 4.15.4 | PASS if pagination `next`/`previous` are full URLs | PASS |
