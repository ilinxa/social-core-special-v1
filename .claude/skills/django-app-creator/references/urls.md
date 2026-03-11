# URLs

Read this when designing URL routing — namespaces, versioning, endpoint design, trailing slashes, and the me/ pattern.

## Quick Reference

```python
from django.urls import path, include
from apps.users.api.views import CurrentUserView, UserCreateView

app_name = "users"

urlpatterns = [
    path("me/", CurrentUserView.as_view(), name="me"),
    path("register/", UserCreateView.as_view(), name="register"),
]
```

---

## 1. Role of URLs

URLs are responsible for **routing only**: map paths to views, define stable route names, define namespaces.

URLs SHOULD NOT: enforce authentication/permissions, contain business logic, perform imports with side effects.

> **URLs route. Views enforce.**

---

## 2. Namespaces & Route Names (MANDATORY)

Every app MUST declare `app_name`:
```python
app_name = "users"
```

Every route MUST have a stable `name=`:
```python
path("me/", CurrentUserView.as_view(), name="me")
```

Reverse usage: `users:me`, `users:profile`

---

## 3. Versioning & Prefix

API prefix at project-level:
```python
path("api/v1/users/", include(("apps.users.urls", "users"), namespace="users"))
```

Rules: versioning belongs at project-level, app URLs should not repeat the version prefix.

---

## 4. Trailing Slash Policy

Use trailing slashes for DRF endpoints. Be consistent everywhere. Ensure `APPEND_SLASH` matches.

---

## 5. "me" Endpoint Design

Prefer "me" patterns for user-owned resources:

```
GET    /users/me/
PATCH  /users/me/
GET    /users/me/profile/
PATCH  /users/me/profile/
POST   /users/me/avatar/
DELETE /users/me/avatar/
```

Benefits: simplifies authorization, reduces privilege escalation risk, clean client usage.

---

## 6. CRUD vs Action Routes

Prefer **action-based** endpoints for user-owned resources. Avoid mixing styles inside one app.

---

## 7. Router Usage (Optional)

Routers allowed for entity CRUD ViewSets. Keep `basename` stable. Still use namespaces.
For action-style endpoints (like `me/`), explicit `path()` is preferred.

---

## 8. Folder Structure

Small apps: `apps/<app>/urls.py`
Large apps with separation:
```
apps/<app>/api/urls/
├── me.py
├── admin.py
```

---

## 9. Anti-Patterns

❌ Authentication/permissions logic in URLs
❌ Database access
❌ Complex configuration
❌ Runtime branching
❌ Business logic
