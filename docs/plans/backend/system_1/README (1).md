# Foundation Platform

A production-ready Django REST Framework backend providing multi-tenant organization management, role-based access control, workflow transactions, and dynamic form building.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Django](https://img.shields.io/badge/Django-5.0+-green.svg)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14+-red.svg)](https://www.django-rest-framework.org/)
[![Tests](https://img.shields.io/badge/Tests-2426%20passed-brightgreen.svg)](#testing)
[![License](https://img.shields.io/badge/License-Proprietary-lightgrey.svg)](#license)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Systems](#systems)
  - [RBAC System](#rbac-system)
  - [Organization System](#organization-system)
  - [Transaction System](#transaction-system)
  - [Form Builder System](#form-builder-system)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Database Schema](#database-schema)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Overview

Foundation Platform provides four integrated systems that serve as the backbone for multi-tenant SaaS applications:

| System | Purpose | Key Features |
|--------|---------|--------------|
| **RBAC** | Authorization & Access Control | Two-plane authority, 28 permissions, role hierarchy, permission caching |
| **Organization** | Account & Profile Management | Platform singleton, multi-tenant businesses, slug routing, verification |
| **Transaction** | Workflow & Approval Engine | 10+ transaction types, state machine, pluggable outcomes, audit trail |
| **Form Builder** | Dynamic Form Management | 22 field types, versioning, typed indexing, system forms |

### Key Capabilities

- **Multi-Tenant Architecture** — Platform-level governance with isolated business accounts
- **Fine-Grained Authorization** — Role-based permissions with scope control (business, platform, global)
- **Workflow Automation** — Configurable approval flows with notifications and outcome handlers
- **Dynamic Forms** — Runtime form creation with versioning and efficient querying
- **Full Audit Trail** — Immutable logs for compliance and debugging
- **Production Ready** — 2,426 tests, soft-delete, caching, background tasks

---

## Architecture

### System Dependencies

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         FOUNDATION PLATFORM                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│    ┌──────────────────────────────────────────────────────────────┐    │
│    │                         RBAC                                  │    │
│    │                   (Authorization Core)                        │    │
│    │                                                               │    │
│    │  • Permissions (28)    • Roles (per-account)                 │    │
│    │  • Memberships         • ActorContext                        │    │
│    └──────────────────────────────────────────────────────────────┘    │
│                    │                       │                            │
│         ┌─────────┴─────────┐    ┌────────┴────────┐                   │
│         ▼                   ▼    ▼                 ▼                   │
│    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐               │
│    │Organization │    │ Transaction │    │Form Builder │               │
│    │             │    │             │    │             │               │
│    │• Platform   │◄──►│• Workflows  │◄──►│• Templates  │               │
│    │• Businesses │    │• Approvals  │    │• Responses  │               │
│    │• Profiles   │    │• Outcomes   │    │• Indexing   │               │
│    └─────────────┘    └─────────────┘    └─────────────┘               │
│                              │                  │                       │
│                              └────────┬─────────┘                       │
│                                       ▼                                 │
│                         ┌─────────────────────────┐                     │
│                         │  Form-Transaction       │                     │
│                         │  Integration            │                     │
│                         │                         │                     │
│                         │  • Form-backed requests │                     │
│                         │  • INFO_REQUESTED flow  │                     │
│                         │  • System forms         │                     │
│                         └─────────────────────────┘                     │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  CORE INFRASTRUCTURE                                                    │
│  • AuditService    • UUIDModel/AuditModel    • Exceptions              │
│  • Notifications   • Celery Tasks            • Caching (Redis)         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Layered Architecture

Each system follows a consistent layered architecture:

```
┌─────────────────────────────────────────┐
│  API Layer (views.py, urls.py)          │  ← HTTP endpoints, authentication
├─────────────────────────────────────────┤
│  Serializers (serializers.py)           │  ← Input validation, output formatting
├─────────────────────────────────────────┤
│  Policies (policies.py)                 │  ← Authorization decisions
├─────────────────────────────────────────┤
│  Services (services.py)                 │  ← Business logic, transactions
├─────────────────────────────────────────┤
│  Selectors (selectors.py)               │  ← Read queries, caching
├─────────────────────────────────────────┤
│  Managers (managers.py)                 │  ← QuerySet methods, filtering
├─────────────────────────────────────────┤
│  Models (models.py)                     │  ← Data structures, constraints
└─────────────────────────────────────────┘
```

---

## Systems

### RBAC System

Role-Based Access Control with two-plane authority model.

#### Key Concepts

| Concept | Description |
|---------|-------------|
| **Two-Plane Authority** | Business plane (within account) + Platform plane (cross-account) |
| **Role Levels** | 0 (Owner) to 10 (Base Member) — lower number = higher authority |
| **Permission Scopes** | `BUSINESS`, `PLATFORM_ONLY`, `GLOBAL_ONLY`, `PLATFORM_AND_GLOBAL` |
| **Owner Invincibility** | Account owner cannot be demoted by same-account members |
| **ActorContext** | Immutable snapshot of user's authority at request time |

#### Permission Categories (28 total)

| Category | Permissions |
|----------|-------------|
| Membership (7) | `can_invite_member`, `can_remove_member`, `can_change_member_role`, `can_suspend_member`, `can_ban_member`, `can_approve_membership_request`, `can_view_members` |
| Roles (3) | `can_create_role`, `can_edit_role`, `can_delete_role` |
| Settings (3) | `can_edit_business`, `can_edit_profile`, `can_view_settings` |
| Platform (6) | `can_suspend_business`, `can_remove_business_owner`, `can_transfer_business_ownership`, `can_view_businesses`, `can_approve_verification_request`, `can_approve_business_creation` |
| Transaction (2) | `can_view_transactions`, `can_view_all_transactions` |
| Audit (1) | `can_view_audit_logs` |
| Forms (6) | `can_create_form`, `can_edit_form`, `can_delete_form`, `can_view_responses`, `can_export_responses`, `can_process_response` |

#### Models

```python
# Permission — Immutable, seeded via migrations
Permission(code, name, description, category, applicable_scopes)

# Role — Per-account, with level hierarchy
Role(name, account_type, account_id, level, is_system_role)

# RolePermission — Links roles to permissions with scope
RolePermission(role, permission, scope)

# Membership — User-account relationship
Membership(user, account_type, account_id, role, is_owner, status)
```

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/rbac/permissions/` | GET | List all permissions |
| `/api/v1/business/<slug>/roles/` | GET, POST | List/create business roles |
| `/api/v1/business/<slug>/roles/<id>/` | GET, PATCH, DELETE | Role detail/update/delete |
| `/api/v1/business/<slug>/members/` | GET | List business members |
| `/api/v1/business/<slug>/members/<id>/` | GET, PATCH, DELETE | Member detail/update/remove |
| `/api/v1/users/me/memberships/` | GET | List user's memberships |

---

### Organization System

Platform and business account management with profile separation.

#### Key Concepts

| Concept | Description |
|---------|-------------|
| **Platform Singleton** | Single platform account enforced by database constraint |
| **Multi-Tenant Businesses** | Unlimited business accounts with isolated data |
| **Account/Profile Separation** | Legal data (Account) vs. public data (Profile) |
| **Slug Routing** | SEO-friendly URLs with history tracking and 301 redirects |
| **Verification Workflow** | Integration with Transaction system for business verification |

#### Business Status Flow

```
PENDING → ACTIVE (setup complete)
ACTIVE → SUSPENDED (platform enforcement)
ACTIVE → ARCHIVED (owner voluntary)
ACTIVE → DELETED (soft-delete)
SUSPENDED → ACTIVE (platform reactivation)
ARCHIVED → ACTIVE (owner reactivation)
```

#### Verification Status Flow

```
UNVERIFIED → PENDING (submit request)
PENDING → VERIFIED (platform approval)
PENDING → REJECTED (platform denial)
REJECTED → PENDING (resubmit)
VERIFIED → EXPIRED (time-based)
```

#### Models

```python
# Platform (Singleton)
PlatformAccount(is_configured, settings)
PlatformProfile(name, tagline, logo, colors, contact_info)

# Business (Multi-tenant)
BusinessAccount(slug, legal_name, country, business_type, status, verification_status)
BusinessProfile(display_name, description, logo, website, social_links, is_public)
BusinessSlugHistory(business, old_slug, changed_at)  # For 301 redirects
```

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/platform/account/` | GET, POST | Platform account (POST = configure) |
| `/api/v1/platform/profile/` | GET, PATCH | Platform profile |
| `/api/v1/platform/settings/` | PATCH | Platform settings |
| `/api/v1/business/` | GET, POST | List/create businesses |
| `/api/v1/business/my/` | GET | Current user's businesses |
| `/api/v1/business/<slug>/` | GET, PATCH, DELETE | Business detail |
| `/api/v1/business/<slug>/profile/` | GET, PATCH | Business profile |
| `/api/v1/business/<slug>/suspend/` | POST | Suspend (staff only) |
| `/api/v1/business/<slug>/archive/` | POST | Archive (owner only) |

---

### Transaction System

Configurable workflow engine for approvals, invitations, and requests.

#### Key Concepts

| Concept | Description |
|---------|-------------|
| **Unified State Machine** | Single model handles all transaction types |
| **Config-Driven Types** | Business rules declared in `TransactionTypeConfig` |
| **Pluggable Outcomes** | Registry of handlers executed on acceptance |
| **Dual Authority Validation** | Creator permissions re-checked at acceptance |
| **Immutable Audit Log** | `TransactionLog` cannot be modified or deleted |

#### Transaction Types (10)

| Type | Mode | Description |
|------|------|-------------|
| `platform_membership_invitation` | Invitation | Invite user to platform |
| `business_membership_invitation` | Invitation | Invite user to business |
| `platform_membership_request` | Request | Request to join platform |
| `business_membership_request` | Request | Request to join business |
| `business_verification_request` | Request | Request business verification |
| `business_creation_request` | Request | Request to create business |
| `platform_ownership_transfer` | Request | Transfer platform ownership |
| `business_ownership_transfer` | Request | Transfer business ownership |
| `user_connection_request` | Request | Connect with another user |
| `business_follow_request` | Request | Follow a business |

#### State Machine

```
CREATED → SENT → PENDING ──→ ACCEPTED
                    │    ──→ DENIED
                    │    ──→ DISMISSED
                    │    ──→ CANCELLED
                    │    ──→ EXPIRED
                    │    ──→ INVALIDATED
                    │
                    ↓
              INFO_REQUESTED ──→ PENDING (resubmit)
```

#### Models

```python
# Transaction — Main workflow record
Transaction(
    transaction_type, mode, status,
    initiator_type, initiator_id, initiator_context,
    target_type, target_id,
    context_type, context_id,
    payload, form_response_id,
    expires_at, resolved_at, resolved_by,
    outcome_executed, outcome_error
)

# TransactionLog — Immutable audit trail
TransactionLog(
    transaction, event_type, timestamp,
    actor_context, previous_status, new_status, metadata
)
```

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/transactions/` | GET | List user's transactions |
| `/api/v1/transactions/invitation/` | POST | Create invitation |
| `/api/v1/transactions/request/` | POST | Create request |
| `/api/v1/transactions/<id>/` | GET | Transaction detail |
| `/api/v1/transactions/<id>/accept/` | POST | Accept transaction |
| `/api/v1/transactions/<id>/deny/` | POST | Deny transaction |
| `/api/v1/transactions/<id>/cancel/` | POST | Cancel (initiator only) |
| `/api/v1/transactions/<id>/request-info/` | POST | Request more info |
| `/api/v1/transactions/<id>/resubmit/` | POST | Resubmit after update |
| `/api/v1/transactions/types/<type>/form/` | GET | Get form schema for type |

#### Celery Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `expire_transactions` | Every hour | Expire overdue transactions |
| `retry_failed_outcomes` | Every 15 min | Retry failed outcome handlers |
| `cleanup_old_logs` | Daily | Archive old transaction logs |
| `send_expiration_reminders` | Daily | Notify about expiring transactions |

---

### Form Builder System

Dynamic form creation with versioning, typed indexing, and transaction integration.

#### Key Concepts

| Concept | Description |
|---------|-------------|
| **Two-Tier Storage** | JSONB for flexibility + typed index tables for querying |
| **Form Versioning** | Editing active forms creates new versions |
| **System Forms** | Platform-managed forms (verification, applications) |
| **Selective Indexing** | Up to 5 indexed fields per form for efficient queries |
| **Transaction Integration** | Forms linked to transactions with INFO_REQUESTED flow |

#### Field Types (22)

| Category | Types |
|----------|-------|
| Text | `text`, `textarea`, `email`, `url`, `phone`, `password` |
| Numeric | `integer`, `decimal`, `currency`, `rating` |
| Selection | `select`, `radio`, `checkbox`, `multiselect` |
| Date/Time | `date`, `time`, `datetime` |
| Media | `file`, `image` |
| Special | `boolean`, `location`, `signature`, `repeatable` |

#### Storage Types & Indexing

| Storage Type | Indexable | Index Table |
|--------------|-----------|-------------|
| TEXT | ✅ | TextFieldIndex |
| INTEGER | ✅ | IntegerFieldIndex |
| DECIMAL | ✅ | DecimalFieldIndex |
| BOOLEAN | ✅ | BooleanFieldIndex |
| DATE | ✅ | DateFieldIndex |
| DATETIME | ✅ | DateTimeFieldIndex |
| JSON | ❌ | — (multiselect, file, location, repeatable) |

#### Form Status Flow

```
DRAFT → ACTIVE (publish)
ACTIVE → ARCHIVED (archive)
ACTIVE → DELETED (soft-delete)
ACTIVE → ACTIVE (edit creates new version)
```

#### Response Status Flow

```
DRAFT → SUBMITTED (submit)
SUBMITTED → PROCESSED (staff review)
SUBMITTED → VOID (void)
DRAFT → VOID (void)
```

#### System Forms (Seeded)

| Form | Slug | Purpose |
|------|------|---------|
| Business Verification | `system-business-verification` | Verification request workflow |
| Business Creation | `system-business-creation` | Business creation request |
| Platform Staff Application | `system-platform-staff-application` | Staff applications |

#### Models

```python
# FormTemplate — Form schema with versioning
FormTemplate(
    name, slug, description,
    owner_type, owner_id, scope,
    status, version, is_current, parent_version,
    is_template_public, forked_from, settings
)

# FormField — Field definitions
FormField(
    form_template, field_key, field_type, label,
    order, step_tag, section_tag,
    options, validation_rules, ui_config,
    is_required, is_indexed, is_hidden, is_readonly
)

# FormResponse — Submitted data
FormResponse(
    form_template, form_version,
    data, status, revision, revision_history,
    transaction_id, submitted_at, processed_at
)

# Typed Index Tables
TextFieldIndex(response, field_key, value)
IntegerFieldIndex(response, field_key, value)
# ... etc.
```

#### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/<account_type>/<id>/templates/` | GET, POST | List/create form templates |
| `/templates/<id>/` | GET, PATCH, DELETE | Template detail |
| `/templates/<id>/publish/` | POST | Publish draft |
| `/templates/<id>/archive/` | POST | Archive form |
| `/templates/<id>/fork/` | POST | Fork public template |
| `/templates/<id>/fields/` | POST | Add field |
| `/templates/<id>/responses/` | GET, POST | List/create responses |
| `/responses/<id>/` | GET, PATCH | Response detail |
| `/responses/<id>/submit/` | POST | Submit response |
| `/responses/<id>/process/` | POST | Process (staff) |
| `/responses/my/` | GET | User's responses |

---

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (production) or SQLite (development)
- Redis 6+ (caching, Celery)
- Node.js 18+ (optional, for frontend)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd foundation-platform

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Seed permissions (automatic via migrations)
python manage.py shell -c "from apps.rbac.models import Permission; print(f'{Permission.objects.count()} permissions seeded')"

# Start development server
python manage.py runserver
```

### Initialize Platform

```bash
# Via Django admin or API
python manage.py shell << EOF
from apps.organization.platform.services import PlatformAccountService
from apps.users.models import User

superuser = User.objects.get(is_superuser=True)
PlatformAccountService.configure(
    name="My Platform",
    actor=superuser
)
print("Platform configured!")
EOF
```

### Start Background Workers

```bash
# Celery worker
celery -A backend_core worker -l info

# Celery beat (scheduler)
celery -A backend_core beat -l info
```

---

## Configuration

### Environment Variables

```bash
# Django
SECRET_KEY=your-secret-key
DEBUG=False
ALLOWED_HOSTS=example.com,api.example.com

# Database
DATABASE_URL=postgres://user:pass@localhost:5432/foundation

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Storage (S3)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_REGION_NAME=us-east-1

# Email
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=noreply@example.com

# Security
CORS_ALLOWED_ORIGINS=https://app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com
```

### Django Settings

```python
# settings/production.py

INSTALLED_APPS = [
    # ...
    'apps.core',
    'apps.users',
    'apps.rbac',
    'apps.organization',
    'apps.transaction',
    'apps.forms',
    'apps.notifications',
]

# RBAC Settings
RBAC_PERMISSION_CACHE_TTL = 300  # 5 minutes

# Transaction Settings
TRANSACTION_DEFAULT_EXPIRATION_DAYS = 7
TRANSACTION_RATE_LIMIT_WINDOW = 3600  # 1 hour

# Form Builder Settings
FORM_MAX_INDEXED_FIELDS = 5
FORM_MAX_FILE_SIZE_MB = 10
```

---

## API Reference

### Authentication

All endpoints require authentication via JWT tokens:

```bash
# Obtain token
curl -X POST /api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secret"}'

# Use token
curl /api/v1/business/my/ \
  -H "Authorization: Bearer <access_token>"
```

### Common Response Formats

```json
// Success
{
  "id": "uuid",
  "...": "..."
}

// Paginated List
{
  "count": 100,
  "next": "https://api.example.com/resource/?page=2",
  "previous": null,
  "results": [...]
}

// Error
{
  "type": "validation_error",
  "errors": [
    {"field": "email", "message": "This field is required."}
  ]
}
```

### API Documentation

Interactive API documentation available at:

- Swagger UI: `/api/docs/`
- ReDoc: `/api/redoc/`
- OpenAPI Schema: `/api/schema/`

---

## Database Schema

### Table Overview

| App | Tables | Description |
|-----|--------|-------------|
| **rbac** | 4 | Permission, Role, RolePermission, Membership |
| **organization** | 5 | PlatformAccount, PlatformProfile, BusinessAccount, BusinessProfile, BusinessSlugHistory |
| **transaction** | 2 | Transaction, TransactionLog |
| **forms** | 9 | FormTemplate, FormField, FormResponse, + 6 index tables |
| **Total** | **20** | |

### Key Indexes

```sql
-- RBAC
CREATE INDEX idx_membership_account ON rbac_membership(account_type, account_id, status);
CREATE INDEX idx_membership_user ON rbac_membership(user_id, status);
CREATE UNIQUE INDEX idx_unique_owner ON rbac_membership(account_type, account_id) 
  WHERE is_owner = TRUE AND is_deleted = FALSE;

-- Organization
CREATE INDEX idx_business_status ON organization_business_account(status, is_deleted);
CREATE INDEX idx_business_verification ON organization_business_account(verification_status);
CREATE UNIQUE INDEX idx_business_slug ON organization_business_account(slug);

-- Transaction
CREATE INDEX idx_transaction_type_status ON transaction_transaction(transaction_type, status);
CREATE INDEX idx_transaction_context ON transaction_transaction(context_type, context_id, status);
CREATE INDEX idx_transaction_expires ON transaction_transaction(expires_at);

-- Forms
CREATE INDEX idx_form_owner ON forms_form_template(owner_type, owner_id, status);
CREATE INDEX idx_response_transaction ON forms_form_response(transaction_id);
CREATE INDEX idx_text_field_value ON forms_text_field_index(field_key, value);
```

### Entity Relationships

```
User ─────────────────┬──────────────────────────────────────┐
  │                   │                                      │
  │ created_by        │ user                                 │ submitted_by
  ▼                   ▼                                      ▼
BusinessAccount ←── Membership ──→ Role ──→ RolePermission → Permission
  │                   │
  │ business          │ context
  ▼                   ▼
BusinessProfile    Transaction ←────────────────────┐
                      │                              │
                      │ form_response_id             │ transaction_id
                      ▼                              │
                   FormResponse ─────────────────────┘
                      │
                      │ form_template
                      ▼
                   FormTemplate
                      │
                      │ form_template
                      ▼
                   FormField
```

---

## Testing

### Test Suite

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific app tests
pytest apps/rbac/
pytest apps/organization/
pytest apps/transaction/
pytest apps/forms/

# Run with verbose output
pytest -v

# Run specific test file
pytest apps/rbac/tests/test_policies.py

# Run tests matching pattern
pytest -k "test_owner"
```

### Test Statistics

| App | Tests | Coverage |
|-----|-------|----------|
| RBAC | 223 | ~95% |
| Organization | ~136 | ~94% |
| Transaction | ~400 | 95.8% |
| Form Builder | ~200 | ~93% |
| Core/Users/Other | ~1,467 | — |
| **Total** | **2,426** | **~95%** |

*Note: Test counts include integration tests added during Form-Transaction integration and RBAC wiring.*

### Test Fixtures

```python
# conftest.py provides common fixtures
@pytest.fixture
def owner_user(db):
    """User who owns a business."""
    return UserFactory()

@pytest.fixture
def business_with_rbac(db, owner_user):
    """Business with RBAC initialized."""
    business = BusinessAccountFactory(created_by=owner_user)
    RBACService.initialize_business_account(
        business_id=business.id,
        owner=owner_user
    )
    return business

@pytest.fixture
def actor_context(db, owner_user, business_with_rbac):
    """ActorContext for testing authorization."""
    membership = MembershipSelector.get_active_membership_for_user_account(
        user=owner_user,
        account_type=AccountType.BUSINESS,
        account_id=business_with_rbac.id
    )
    return RBACService.build_actor_context(membership=membership)
```

---

## Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Configure `SECRET_KEY` (use secure random value)
- [ ] Set up PostgreSQL database
- [ ] Configure Redis for caching and Celery
- [ ] Set up S3 or equivalent for file storage
- [ ] Configure email service
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS and CSRF settings
- [ ] Set up monitoring (Sentry, etc.)
- [ ] Configure log aggregation
- [ ] Run database migrations
- [ ] Verify permission seeding (28 permissions)
- [ ] Configure Celery workers and beat scheduler
- [ ] Set up health checks

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py collectstatic --noinput

EXPOSE 8000

CMD ["gunicorn", "backend_core.wsgi:application", "--bind", "0.0.0.0:8000"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgres://postgres:postgres@db:5432/foundation
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis

  celery:
    build: .
    command: celery -A backend_core worker -l info
    depends_on:
      - db
      - redis

  celery-beat:
    build: .
    command: celery -A backend_core beat -l info
    depends_on:
      - db
      - redis

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=foundation
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Health Checks

```python
# Health check endpoint
# GET /api/health/

{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "celery": "connected",
  "permissions_count": 28,
  "platform_configured": true
}
```

---

## Contributing

### Development Setup

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run linting
ruff check apps/
black --check apps/

# Run type checking
mypy apps/
```

### Code Style

- Follow PEP 8
- Use Black for formatting (line length: 88)
- Use Ruff for linting
- Type hints required for all public functions
- Docstrings required for all classes and public methods

### Commit Messages

```
feat(rbac): add permission caching with TTL
fix(transaction): handle expired transactions correctly
docs(readme): update API reference
test(forms): add versioning tests
refactor(organization): extract selector methods
```

### Pull Request Process

1. Create feature branch from `main`
2. Write tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit PR with clear description
6. Address review feedback
7. Squash and merge

---

## License

Proprietary. All rights reserved.

---

## Support

- **Documentation**: `/docs/`
- **API Reference**: `/api/docs/`
- **Issues**: GitHub Issues
- **Email**: support@example.com

---

*Built with Django REST Framework*
