# Core App

## Domain Rules
- Base models: TimeStampedModel (created_at/updated_at), UUIDModel (uuid primary key). Inherit these.
- Custom exceptions live here. Use them instead of raising generic Django exceptions.
- Observability middleware is in `observability/logging/middleware.py`. It must sit after AuthenticationMiddleware in the stack — it needs request.user to be populated.
- Pagination classes are in `pagination.py`. Use these, don't define new ones unless necessary.