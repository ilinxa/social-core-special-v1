---

# Form Builder System Implementation Plan

## Multi-Tenant Platform - System 4 of 4

**Version:** 1.0
**Date:** February 8, 2026
**Status:** Ready for Implementation

> **V-notes**:
> - v1.0: Initial plan based on Form_Builder_System_Spec_v2.md and coherence with Organization (v1.2), Transaction (v1.1), and RBAC (v1.2) systems.

---

## Critical Invariants

> **These rules are non-negotiable and enforced at the database and service level.**

### 1. Maximum 5 Indexed Fields Per Form (Service-Enforced)
Each form template can have at most 5 fields with `is_indexed=True`. This is validated at form creation/update time by the service layer.

### 2. Immutable Contexts (DB-Enforced)
Once a `creator_context` or `submitter_context` is captured, it cannot be modified. These are JSON snapshots of ActorContext at action time.

### 3. Form Versioning on Active Edit
Editing an active form MUST create a new version. Draft forms can be edited in place.

### 4. System Forms Are Immutable
Forms with `owner_type='system'` cannot be modified, deleted, or archived by any user.

### 5. Scope Is Orthogonal to Owner
`owner_type` (who owns) and `scope` (where used) are independent concepts. A platform-owned form can have business scope.

---

## 1. Overview & Dependencies

### 1.1 System Purpose

The Form Builder System provides:
- Dynamic form schema creation without code changes
- Multi-step form support via tagging
- Type-safe response storage with selective indexing
- Integration with Transaction & Approval system
- Template library for reusable forms

### 1.2 Dependencies

| Dependency | System | Purpose |
|------------|--------|---------|
| `UUIDModel`, `AuditModel` | Core | Base models |
| `ActorContext` | Core Types | Context capture and permission checks |
| `RBACService.build_actor_context()` | RBAC | Build ActorContext from membership |
| `MembershipSelector.get_active_membership_for_user_account()` | RBAC | Resolve membership for RBAC context |
| `AuditService`, `AuditLog` | Core Observability | Audit logging |
| `get_logger()` | Core Observability | Structured logging |
| Exceptions | Core Exceptions | Domain exceptions |

### 1.3 Files to Create

```
backend/apps/forms/
    __init__.py
    apps.py
    models.py               # FormTemplate, FormField, FormResponse, Index Tables
    managers.py             # FormTemplateManager, FormResponseManager
    selectors.py            # FormTemplateSelector, FormFieldSelector, FormResponseSelector
    services.py             # FormBuilderService, FormResponseService
    policies.py             # FormTemplatePolicy, FormResponsePolicy
    serializers.py          # Input/Output serializers
    views.py                # FormTemplate and FormResponse API views
    urls.py                 # URL routing
    admin.py                # Django Admin configuration
    validators.py           # Field validation helpers
    indexing.py             # Index extraction and management

    tests/
        __init__.py
        conftest.py         # Shared test fixtures
        factories.py        # Factory-boy factories
        test_models.py
        test_selectors.py
        test_services.py
        test_policies.py
        test_views.py
        test_indexing.py
```

---

## 2. Enums & Constants

### 2.1 New Enums (Add to `apps/core/constants.py`)

```python
# backend/apps/core/constants.py

class FormStatus(models.TextChoices):
    """Form template lifecycle states."""
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"
    DELETED = "deleted", "Deleted"


class ResponseStatus(models.TextChoices):
    """Form response lifecycle states."""
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    PROCESSED = "processed", "Processed"
    VOID = "void", "Void"
    EXPIRED = "expired", "Expired"


class FieldType(models.TextChoices):
    """Form field types."""
    # Text types
    TEXT = "text", "Text"
    TEXTAREA = "textarea", "Text Area"
    EMAIL = "email", "Email"
    URL = "url", "URL"
    PHONE = "phone", "Phone"
    
    # Numeric types
    INTEGER = "integer", "Integer"
    DECIMAL = "decimal", "Decimal"
    CURRENCY = "currency", "Currency"
    RATING = "rating", "Rating"
    
    # Boolean
    BOOLEAN = "boolean", "Boolean"
    CHECKBOX = "checkbox", "Checkbox"
    
    # Date/Time
    DATE = "date", "Date"
    DATETIME = "datetime", "Date & Time"
    TIME = "time", "Time"
    
    # Selection
    SELECT = "select", "Select"
    RADIO = "radio", "Radio"
    MULTISELECT = "multiselect", "Multi-Select"
    CHECKBOX_GROUP = "checkbox_group", "Checkbox Group"
    
    # File types
    FILE = "file", "File"
    IMAGE = "image", "Image"
    
    # Complex types
    LOCATION = "location", "Location"
    REPEATABLE = "repeatable", "Repeatable Group"


class StorageType(models.TextChoices):
    """Internal storage type for field values."""
    TEXT = "text", "Text"
    INTEGER = "integer", "Integer"
    DECIMAL = "decimal", "Decimal"
    BOOLEAN = "boolean", "Boolean"
    DATE = "date", "Date"
    DATETIME = "datetime", "DateTime"
    JSON = "json", "JSON"
```

### 2.2 Field Type to Storage Type Mapping

```python
# backend/apps/forms/constants.py

FIELD_STORAGE_MAP = {
    # Text storage
    FieldType.TEXT: StorageType.TEXT,
    FieldType.TEXTAREA: StorageType.TEXT,
    FieldType.EMAIL: StorageType.TEXT,
    FieldType.URL: StorageType.TEXT,
    FieldType.PHONE: StorageType.TEXT,
    FieldType.SELECT: StorageType.TEXT,
    FieldType.RADIO: StorageType.TEXT,
    FieldType.TIME: StorageType.TEXT,
    
    # Integer storage
    FieldType.INTEGER: StorageType.INTEGER,
    FieldType.RATING: StorageType.INTEGER,
    
    # Decimal storage
    FieldType.DECIMAL: StorageType.DECIMAL,
    FieldType.CURRENCY: StorageType.DECIMAL,
    
    # Boolean storage
    FieldType.BOOLEAN: StorageType.BOOLEAN,
    FieldType.CHECKBOX: StorageType.BOOLEAN,
    
    # Date/DateTime storage
    FieldType.DATE: StorageType.DATE,
    FieldType.DATETIME: StorageType.DATETIME,
    
    # JSON storage (not indexable)
    FieldType.MULTISELECT: StorageType.JSON,
    FieldType.CHECKBOX_GROUP: StorageType.JSON,
    FieldType.FILE: StorageType.JSON,
    FieldType.IMAGE: StorageType.JSON,
    FieldType.LOCATION: StorageType.JSON,
    FieldType.REPEATABLE: StorageType.JSON,
}

INDEXABLE_STORAGE_TYPES = frozenset([
    StorageType.TEXT,
    StorageType.INTEGER,
    StorageType.DECIMAL,
    StorageType.BOOLEAN,
    StorageType.DATE,
    StorageType.DATETIME,
])

MAX_INDEXED_FIELDS = 5
```

### 2.3 New AuditLog Actions

Add to `apps/core/observability/audit/models.py` - `AuditLog.Action` enum:

```python
# Forms - Templates
FORM_TEMPLATE_CREATED = "forms.template.created", "Form Template Created"
FORM_TEMPLATE_UPDATED = "forms.template.updated", "Form Template Updated"
FORM_TEMPLATE_PUBLISHED = "forms.template.published", "Form Template Published"
FORM_TEMPLATE_ARCHIVED = "forms.template.archived", "Form Template Archived"
FORM_TEMPLATE_DELETED = "forms.template.deleted", "Form Template Deleted"
FORM_TEMPLATE_VERSIONED = "forms.template.versioned", "Form Template Versioned"
FORM_TEMPLATE_FORKED = "forms.template.forked", "Form Template Forked"

# Forms - Fields
FORM_FIELD_ADDED = "forms.field.added", "Form Field Added"
FORM_FIELD_UPDATED = "forms.field.updated", "Form Field Updated"
FORM_FIELD_REMOVED = "forms.field.removed", "Form Field Removed"

# Forms - Responses
FORM_RESPONSE_CREATED = "forms.response.created", "Form Response Created"
FORM_RESPONSE_UPDATED = "forms.response.updated", "Form Response Updated"
FORM_RESPONSE_SUBMITTED = "forms.response.submitted", "Form Response Submitted"
FORM_RESPONSE_PROCESSED = "forms.response.processed", "Form Response Processed"
FORM_RESPONSE_VOIDED = "forms.response.voided", "Form Response Voided"
FORM_RESPONSE_EXPORTED = "forms.response.exported", "Form Responses Exported"
```

---

## 3. Core Models

### 3.1 FormTemplate Model (`apps/forms/models.py`)

```python
"""
Form Builder Models
===================
FormTemplate, FormField, FormResponse, and Index Tables.
"""

import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator
from apps.core.models import UUIDModel, AuditModel
from apps.core.constants import (
    OwnerType, FormScope, FormStatus, ResponseStatus, FieldType
)
from apps.forms.managers import FormTemplateManager, FormResponseManager


class FormTemplate(UUIDModel, AuditModel):
    """
    Form schema definition with versioning support.
    
    INVARIANT: System forms (owner_type='system') cannot be modified.
    INVARIANT: Maximum 5 indexed fields per form.
    INVARIANT: Editing active form creates new version.
    """
    
    # Identity
    name = models.CharField(max_length=255, help_text="Form display name")
    slug = models.SlugField(max_length=100, help_text="URL-friendly identifier")
    description = models.TextField(blank=True, default="", help_text="Form description")
    
    # Ownership (who owns this form)
    owner_type = models.CharField(
        max_length=20,
        choices=OwnerType.choices,
        db_index=True,
        help_text="Who owns this form template"
    )
    owner_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of owner account (null for system forms)"
    )
    
    # Scope (where this form can be used)
    scope = models.CharField(
        max_length=20,
        choices=FormScope.choices,
        db_index=True,
        help_text="Where this form can be used"
    )
    
    # Creator context (captured at creation time)
    creator_context = models.JSONField(
        help_text="ActorContext snapshot at creation time"
    )
    
    # Status and versioning
    status = models.CharField(
        max_length=20,
        choices=FormStatus.choices,
        default=FormStatus.DRAFT,
        db_index=True
    )
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(
        default=True,
        db_index=True,
        help_text="True if this is the current version"
    )
    parent_version = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='child_versions',
        help_text="Previous version this was created from"
    )
    
    # Template library
    is_template_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text="If true, visible in public template library"
    )
    forked_from = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='forks',
        help_text="Template this was forked from"
    )
    
    # Settings
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Form-level settings (expiry, notifications, etc.)"
    )

    # Managers — override AuditModel's SoftDeleteManager with custom manager
    objects = FormTemplateManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "form_template"
        verbose_name = "Form Template"
        verbose_name_plural = "Form Templates"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner_type", "owner_id", "slug", "version"],
                name="unique_form_slug_per_owner_version"
            ),
        ]
        indexes = [
            models.Index(fields=["owner_type", "owner_id"]),
            models.Index(fields=["scope", "status"]),
            models.Index(fields=["is_template_public", "status"]),
            models.Index(fields=["owner_type", "owner_id", "is_current"]),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version}"
    
    @property
    def is_system_form(self) -> bool:
        """Check if this is an immutable system form."""
        return self.owner_type == OwnerType.SYSTEM
    
    @property
    def is_editable(self) -> bool:
        """Check if form can be edited."""
        if self.is_system_form:
            return False
        return self.status in [FormStatus.DRAFT, FormStatus.ACTIVE]
    
    @property
    def accepts_responses(self) -> bool:
        """Check if form accepts new responses."""
        return self.status == FormStatus.ACTIVE and self.is_current
```

### 3.2 FormField Model

```python
class FormField(UUIDModel):
    """
    Field definition within a form template.
    
    INVARIANT: field_key must be unique within a form template.
    INVARIANT: Only indexable storage types can have is_indexed=True.
    """
    
    form_template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    
    # Identity
    field_key = models.CharField(
        max_length=100,
        help_text="Machine-readable field identifier"
    )
    field_type = models.CharField(
        max_length=50,
        choices=FieldType.choices,
        help_text="Field type determining input and validation"
    )
    
    # Display
    label = models.CharField(max_length=255, help_text="Field label")
    description = models.TextField(
        blank=True,
        default="",
        help_text="Help text for the field"
    )
    placeholder = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Placeholder text"
    )
    
    # Structure
    order = models.PositiveIntegerField(
        help_text="Display order (lower first)"
    )
    step_tag = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="Groups fields into wizard steps"
    )
    section_tag = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Visual grouping within a step"
    )
    
    # Configuration
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="Options for select, radio, etc."
    )
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Validation rules (min_length, max_value, etc.)"
    )
    ui_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="UI configuration (width, layout_hint)"
    )
    default_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Default value or dynamic token"
    )
    
    # Behavior flags
    is_required = models.BooleanField(
        default=False,
        help_text="Field must have a value"
    )
    is_indexed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Value goes to typed index table (max 5 per form)"
    )
    is_hidden = models.BooleanField(
        default=False,
        help_text="System/internal field, not shown in UI"
    )
    is_readonly = models.BooleanField(
        default=False,
        help_text="Displayed but not editable"
    )
    
    class Meta:
        db_table = "form_field"
        verbose_name = "Form Field"
        verbose_name_plural = "Form Fields"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["form_template", "field_key"],
                name="unique_field_key_per_form"
            ),
        ]
        indexes = [
            models.Index(fields=["form_template", "order"]),
            models.Index(fields=["form_template", "step_tag"]),
            models.Index(fields=["form_template", "is_indexed"]),
        ]
    
    def __str__(self):
        return self.field_key
```

### 3.3 FormResponse Model

```python
class FormResponse(UUIDModel, AuditModel):
    """
    User submission of a filled form.
    
    INVARIANT: form_version captures version at submission time.
    INVARIANT: submitter_context is immutable after submission.
    INVARIANT: Cannot edit after status=processed.
    """
    
    form_template = models.ForeignKey(
        FormTemplate,
        on_delete=models.PROTECT,
        related_name='responses'
    )
    form_version = models.PositiveIntegerField(
        help_text="Form version at submission time"
    )
    
    # Submitter
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='form_responses'
    )
    submitter_context = models.JSONField(
        help_text="ActorContext snapshot at submission time"
    )
    
    # Data
    data = models.JSONField(
        help_text="Complete response data as JSON"
    )
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=ResponseStatus.choices,
        default=ResponseStatus.DRAFT,
        db_index=True
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When response was submitted"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When response was processed"
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='processed_form_responses'
    )
    
    # Processing notes
    processor_notes = models.TextField(
        blank=True,
        default="",
        help_text="Notes from processor"
    )

    # Managers — override AuditModel's SoftDeleteManager with custom manager
    objects = FormResponseManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "form_response"
        verbose_name = "Form Response"
        verbose_name_plural = "Form Responses"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["form_template", "status"]),
            models.Index(fields=["submitted_by", "status"]),
            models.Index(fields=["form_template", "submitted_at"]),
            models.Index(fields=["status", "-submitted_at"]),
        ]
    
    def __str__(self):
        return f"Response {self.id} ({self.status})"
    
    @property
    def is_editable(self) -> bool:
        """Check if response can be edited."""
        return self.status in [ResponseStatus.DRAFT, ResponseStatus.SUBMITTED]
```

### 3.4 Index Tables

```python
class BaseFieldIndex(UUIDModel):
    """
    Abstract base for typed field index tables.
    
    Each concrete index table stores extracted values from indexed form fields
    for efficient querying.
    """
    
    response = models.ForeignKey(
        FormResponse,
        on_delete=models.CASCADE,
        related_name="%(class)s_indexes"
    )
    field_key = models.CharField(
        max_length=100,
        db_index=True,
        help_text="The field key this value is for"
    )
    
    class Meta:
        abstract = True


class TextFieldIndex(BaseFieldIndex):
    """Index table for text-type fields."""
    
    value = models.TextField(help_text="Indexed text value")
    
    class Meta:
        db_table = "form_text_field_index"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class IntegerFieldIndex(BaseFieldIndex):
    """Index table for integer-type fields."""
    
    value = models.BigIntegerField(help_text="Indexed integer value")
    
    class Meta:
        db_table = "form_integer_field_index"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class DecimalFieldIndex(BaseFieldIndex):
    """Index table for decimal-type fields."""
    
    value = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        help_text="Indexed decimal value"
    )
    
    class Meta:
        db_table = "form_decimal_field_index"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class BooleanFieldIndex(BaseFieldIndex):
    """Index table for boolean-type fields."""
    
    value = models.BooleanField(help_text="Indexed boolean value")
    
    class Meta:
        db_table = "form_boolean_field_index"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class DateFieldIndex(BaseFieldIndex):
    """Index table for date-type fields."""
    
    value = models.DateField(help_text="Indexed date value")
    
    class Meta:
        db_table = "form_date_field_index"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class DateTimeFieldIndex(BaseFieldIndex):
    """Index table for datetime-type fields."""
    
    value = models.DateTimeField(help_text="Indexed datetime value")
    
    class Meta:
        db_table = "form_datetime_field_index"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]
```

---

## 4. Core Types (ActorContext Reference)

### 4.1 ActorContext Usage Pattern

> **CRITICAL**: Never construct ActorContext directly from RBAC models. Always use `RBACService.build_actor_context()`.

```python
# apps/forms/views.py (context built in view, passed to service)

membership = MembershipSelector.get_active_membership_for_user_account(
    user=request.user, account_type=account_type, account_id=account_id,
)
actor_context = RBACService.build_actor_context(
    membership=membership, request=request,
)

# apps/forms/services.py (receives pre-built context)

class FormBuilderService:
    @staticmethod
    def create_form_template(
        *,
        actor_context: ActorContext,  # Pre-built by view
        actor,                        # membership.user for audit
        request=None,
        name: str,
        **kwargs
    ) -> FormTemplate:
        # Store context as JSON — NEVER build ActorContext inside services
        form = FormTemplate.objects.create(
            name=name,
            creator_context=actor_context.to_dict(),
            created_by=actor,
            **kwargs
        )
        return form
```

### 4.2 Context Reconstruction

```python
# Reading stored context
from apps.core.types import ActorContext

def get_creator_info(form_template: FormTemplate) -> ActorContext:
    """Reconstruct ActorContext from stored JSON."""
    return ActorContext.from_dict(form_template.creator_context)
```

---

## 5. Managers & QuerySets

### 5.1 FormTemplateManager (`apps/forms/managers.py`)

```python
from django.db import models
from apps.core.models import SoftDeleteManager
from apps.core.constants import FormStatus, OwnerType, ResponseStatus


class FormTemplateQuerySet(models.QuerySet):
    """Chainable query helpers for FormTemplate."""
    
    def active(self):
        """Only active forms."""
        return self.filter(status=FormStatus.ACTIVE)
    
    def current_versions(self):
        """Only current versions."""
        return self.filter(is_current=True)
    
    def by_owner(self, *, owner_type: str, owner_id):
        """Filter by owner."""
        return self.filter(owner_type=owner_type, owner_id=owner_id)
    
    def by_scope(self, *, scope: str):
        """Filter by scope."""
        return self.filter(scope=scope)
    
    def public_templates(self):
        """Only public templates for library."""
        return self.filter(
            is_template_public=True,
            status=FormStatus.ACTIVE,
            is_current=True
        )
    
    def system_forms(self):
        """Only system-defined forms."""
        return self.filter(owner_type=OwnerType.SYSTEM)
    
    def with_fields(self):
        """Prefetch related fields."""
        return self.prefetch_related('fields')


class FormTemplateManager(SoftDeleteManager):
    """Manager for FormTemplate with soft-delete support."""
    
    def get_queryset(self):
        return FormTemplateQuerySet(self.model, using=self._db).filter(is_deleted=False)
    
    def active(self):
        return self.get_queryset().active()
    
    def current_versions(self):
        return self.get_queryset().current_versions()


class FormResponseQuerySet(models.QuerySet):
    """Chainable query helpers for FormResponse."""
    
    def by_form(self, *, form_template_id):
        """Filter by form template."""
        return self.filter(form_template_id=form_template_id)
    
    def by_submitter(self, *, user_id):
        """Filter by submitter."""
        return self.filter(submitted_by_id=user_id)
    
    def submitted(self):
        """Only submitted responses."""
        return self.filter(status=ResponseStatus.SUBMITTED)
    
    def pending_processing(self):
        """Submitted but not yet processed."""
        return self.filter(status=ResponseStatus.SUBMITTED, processed_at__isnull=True)
    
    def with_form(self):
        """Select related form template."""
        return self.select_related('form_template')


class FormResponseManager(SoftDeleteManager):
    """Manager for FormResponse with soft-delete support."""
    
    def get_queryset(self):
        return FormResponseQuerySet(self.model, using=self._db).filter(is_deleted=False)
```

---

## 6. Selectors (Read Operations)

### 6.1 FormTemplateSelector (`apps/forms/selectors.py`)

```python
from typing import Optional, List
from uuid import UUID
from django.db.models import QuerySet

from apps.core.exceptions import NotFound
from apps.forms.models import FormTemplate, FormField, FormResponse
from apps.core.constants import FormStatus, OwnerType


class FormTemplateSelector:
    """Read-only queries for FormTemplate."""
    
    @staticmethod
    def get_by_id(*, form_template_id: UUID) -> FormTemplate:
        """Get form template by ID, raise NotFound if missing."""
        form = FormTemplate.objects.filter(id=form_template_id).first()
        if not form:
            raise NotFound(resource="FormTemplate", resource_id=form_template_id)
        return form
    
    @staticmethod
    def get_by_id_or_none(*, form_template_id: UUID) -> Optional[FormTemplate]:
        """Get form template by ID, return None if missing."""
        return FormTemplate.objects.filter(id=form_template_id).first()
    
    @staticmethod
    def get_by_slug(
        *,
        owner_type: str,
        owner_id: Optional[UUID],
        slug: str,
        current_only: bool = True
    ) -> FormTemplate:
        """Get form by slug within owner context."""
        qs = FormTemplate.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            slug=slug
        )
        if current_only:
            qs = qs.filter(is_current=True)
        form = qs.first()
        if not form:
            raise NotFound(
                message=f"Form '{slug}' not found",
                resource="FormTemplate",
                resource_id=slug
            )
        return form
    
    @staticmethod
    def get_current_version(*, form_template_id: UUID) -> FormTemplate:
        """Get the current version of a form template."""
        # First get any version to find the slug and owner
        form = FormTemplateSelector.get_by_id(form_template_id=form_template_id)
        
        if form.is_current:
            return form
        
        # Find the current version
        current = FormTemplate.objects.filter(
            owner_type=form.owner_type,
            owner_id=form.owner_id,
            slug=form.slug,
            is_current=True
        ).first()
        
        if not current:
            raise NotFound(
                message="No current version found",
                resource="FormTemplate",
                resource_id=form_template_id
            )
        return current
    
    @staticmethod
    def list_by_owner(
        *,
        owner_type: str,
        owner_id: Optional[UUID],
        status: Optional[str] = None,
        current_only: bool = True
    ) -> QuerySet[FormTemplate]:
        """List forms by owner."""
        qs = FormTemplate.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id
        )
        if status:
            qs = qs.filter(status=status)
        if current_only:
            qs = qs.filter(is_current=True)
        return qs
    
    @staticmethod
    def list_public_templates(*, scope: Optional[str] = None) -> QuerySet[FormTemplate]:
        """List public templates for library."""
        qs = FormTemplate.objects.public_templates()
        if scope:
            qs = qs.filter(scope=scope)
        return qs
    
    @staticmethod
    def list_system_forms(*, scope: Optional[str] = None) -> QuerySet[FormTemplate]:
        """List system-defined forms."""
        qs = FormTemplate.objects.filter(
            owner_type=OwnerType.SYSTEM,
            is_current=True
        )
        if scope:
            qs = qs.filter(scope=scope)
        return qs
    
    @staticmethod
    def get_with_fields(*, form_template_id: UUID) -> FormTemplate:
        """Get form template with prefetched fields."""
        form = FormTemplate.objects.prefetch_related(
            'fields'
        ).filter(id=form_template_id).first()
        if not form:
            raise NotFound(resource="FormTemplate", resource_id=form_template_id)
        return form
    
    @staticmethod
    def count_indexed_fields(*, form_template_id: UUID) -> int:
        """Count indexed fields for a form."""
        return FormField.objects.filter(
            form_template_id=form_template_id,
            is_indexed=True
        ).count()


class FormFieldSelector:
    """Read-only queries for FormField."""
    
    @staticmethod
    def get_by_id(*, field_id: UUID) -> FormField:
        """Get field by ID."""
        field = FormField.objects.select_related('form_template').filter(id=field_id).first()
        if not field:
            raise NotFound(resource="FormField", resource_id=field_id)
        return field
    
    @staticmethod
    def list_by_form(
        *,
        form_template_id: UUID,
        step_tag: Optional[str] = None
    ) -> QuerySet[FormField]:
        """List fields for a form."""
        qs = FormField.objects.filter(form_template_id=form_template_id)
        if step_tag:
            qs = qs.filter(step_tag=step_tag)
        return qs.order_by('order')
    
    @staticmethod
    def list_indexed_fields(*, form_template_id: UUID) -> QuerySet[FormField]:
        """List only indexed fields."""
        return FormField.objects.filter(
            form_template_id=form_template_id,
            is_indexed=True
        ).order_by('order')
    
    @staticmethod
    def get_step_tags(*, form_template_id: UUID) -> List[str]:
        """Get unique step tags in order."""
        return list(
            FormField.objects.filter(
                form_template_id=form_template_id
            ).exclude(
                step_tag=""
            ).values_list(
                'step_tag', flat=True
            ).distinct().order_by('order')
        )


class FormResponseSelector:
    """Read-only queries for FormResponse."""
    
    @staticmethod
    def get_by_id(*, response_id: UUID) -> FormResponse:
        """Get response by ID."""
        response = FormResponse.objects.select_related(
            'form_template', 'submitted_by'
        ).filter(id=response_id).first()
        if not response:
            raise NotFound(resource="FormResponse", resource_id=response_id)
        return response
    
    @staticmethod
    def get_by_id_or_none(*, response_id: UUID) -> Optional[FormResponse]:
        """Get response by ID, return None if missing."""
        return FormResponse.objects.filter(id=response_id).first()
    
    @staticmethod
    def list_by_form(
        *,
        form_template_id: UUID,
        status: Optional[str] = None
    ) -> QuerySet[FormResponse]:
        """List responses for a form."""
        qs = FormResponse.objects.filter(form_template_id=form_template_id)
        if status:
            qs = qs.filter(status=status)
        return qs
    
    @staticmethod
    def list_by_submitter(
        *,
        user_id: UUID,
        form_template_id: Optional[UUID] = None
    ) -> QuerySet[FormResponse]:
        """List responses by submitter."""
        qs = FormResponse.objects.filter(submitted_by_id=user_id)
        if form_template_id:
            qs = qs.filter(form_template_id=form_template_id)
        return qs.select_related('form_template')
    
    @staticmethod
    def exists_for_user_and_form(
        *,
        user_id: UUID,
        form_template_id: UUID,
        status: Optional[str] = None
    ) -> bool:
        """Check if user has response for form."""
        qs = FormResponse.objects.filter(
            submitted_by_id=user_id,
            form_template_id=form_template_id
        )
        if status:
            qs = qs.filter(status=status)
        return qs.exists()
```

---

## 7. Services (Write Operations)

### 7.1 FormBuilderService (`apps/forms/services.py`)

```python
from typing import Optional, List, Dict, Any
from uuid import UUID
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.text import slugify

from apps.core.observability import get_logger, AuditService, AuditLog
from apps.core.exceptions import (
    NotFound, ValidationError, ConflictError, PermissionDenied, BusinessRuleViolation
)
from apps.core.constants import FormStatus, ResponseStatus, OwnerType, StorageType
from apps.core.types import ActorContext
from apps.forms.models import FormTemplate, FormField, FormResponse
from apps.forms.selectors import FormTemplateSelector, FormFieldSelector
from apps.forms.policies import FormTemplatePolicy
from apps.forms.indexing import IndexService
from apps.forms.constants import (
    FIELD_STORAGE_MAP, INDEXABLE_STORAGE_TYPES, MAX_INDEXED_FIELDS,
)

logger = get_logger(__name__)


class FormBuilderService:
    """
    Service for form template creation and management.
    
    All write operations go through this service.
    """
    
    @staticmethod
    @transaction.atomic
    def create_form_template(
        *,
        actor_context: "ActorContext",
        actor,
        request: Optional[HttpRequest] = None,
        name: str,
        slug: Optional[str] = None,
        description: str = "",
        owner_type: str,
        owner_id: Optional[UUID],
        scope: str,
        settings: Optional[Dict] = None
    ) -> FormTemplate:
        """
        Create a new form template.

        Args:
            actor_context: Pre-built ActorContext from view (for context storage)
            actor: User object for audit logging (membership.user)
            request: HTTP request for audit context
            name: Form display name
            slug: URL slug (auto-generated if not provided)
            description: Form description
            owner_type: Who owns this form (system, platform, business)
            owner_id: Owner account UUID
            scope: Where form can be used (platform, business)
            settings: Form-level settings

        Returns:
            Created FormTemplate

        Raises:
            ValidationError: If owner_type is 'system' (only via migration)
            ConflictError: If slug already exists for owner
        """
        # System forms cannot be created via service
        if owner_type == OwnerType.SYSTEM:
            raise ValidationError(
                message="System forms can only be created via migration",
                field="owner_type"
            )

        # Generate slug if not provided
        if not slug:
            slug = slugify(name)[:100]
        
        # Check slug uniqueness for owner
        existing = FormTemplate.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            slug=slug,
            is_current=True
        ).exists()
        if existing:
            raise ConflictError(
                message=f"Form with slug '{slug}' already exists",
                resource="FormTemplate",
                conflict_type="duplicate"
            )
        
        form = FormTemplate.objects.create(
            name=name,
            slug=slug,
            description=description,
            owner_type=owner_type,
            owner_id=owner_id,
            scope=scope,
            creator_context=actor_context.to_dict(),
            created_by=actor,
            status=FormStatus.DRAFT,
            version=1,
            is_current=True,
            settings=settings or {},
        )

        logger.info(
            "forms.template.created",
            form_id=str(form.id),
            name=name,
            owner_type=owner_type,
        )

        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_CREATED,
            actor=actor,
            resource=form,
            request=request,
            details={
                "owner_type": owner_type,
                "scope": scope,
            }
        )
        
        return form
    
    @staticmethod
    @transaction.atomic
    def update_form_template(
        *,
        form_template: FormTemplate,
        updated_by,
        request: Optional[HttpRequest] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> FormTemplate:
        """
        Update a form template. If active, creates new version.
        
        Returns:
            Updated FormTemplate (may be new version if was active)
        """
        # Check if editable
        if not form_template.is_editable:
            raise BusinessRuleViolation(
                message="This form cannot be edited",
                rule="form_immutability"
            )
        
        # If active, create new version
        if form_template.status == FormStatus.ACTIVE:
            return FormBuilderService._create_new_version(
                form_template=form_template,
                updated_by=updated_by,
                request=request,
                name=name,
                description=description,
                settings=settings
            )
        
        # Draft: update in place
        changes = {}
        if name is not None and form_template.name != name:
            changes['name'] = {'old': form_template.name, 'new': name}
            form_template.name = name
        
        if description is not None and form_template.description != description:
            changes['description'] = {'old': form_template.description, 'new': description}
            form_template.description = description
        
        if settings is not None:
            changes['settings'] = {'old': form_template.settings, 'new': settings}
            form_template.settings = settings
        
        if changes:
            form_template.updated_by = updated_by
            form_template.save(update_fields=list(changes.keys()) + ['updated_by', 'updated_at'])
            
            logger.info(
                "forms.template.updated",
                form_id=str(form_template.id),
                fields=list(changes.keys()),
            )
            
            AuditService.log(
                action=AuditLog.Action.FORM_TEMPLATE_UPDATED,
                actor=updated_by,
                resource=form_template,
                request=request,
                changes=changes,
            )
        
        return form_template
    
    @staticmethod
    @transaction.atomic
    def _create_new_version(
        *,
        form_template: FormTemplate,
        updated_by,
        request: Optional[HttpRequest] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> FormTemplate:
        """Create a new version of an active form template."""
        
        # Mark current as not current
        form_template.is_current = False
        form_template.updated_by = updated_by
        form_template.save(update_fields=['is_current', 'updated_by', 'updated_at'])

        # Create new version
        new_version = FormTemplate.objects.create(
            name=name if name is not None else form_template.name,
            slug=form_template.slug,
            description=description if description is not None else form_template.description,
            owner_type=form_template.owner_type,
            owner_id=form_template.owner_id,
            scope=form_template.scope,
            creator_context=form_template.creator_context,  # Keep original creator
            created_by=updated_by,
            status=FormStatus.ACTIVE,
            version=form_template.version + 1,
            is_current=True,
            parent_version=form_template,
            is_template_public=form_template.is_template_public,
            forked_from=form_template.forked_from,
            settings=settings if settings is not None else form_template.settings,
        )
        
        # Copy fields to new version
        for field in form_template.fields.all():
            FormField.objects.create(
                form_template=new_version,
                field_key=field.field_key,
                field_type=field.field_type,
                label=field.label,
                description=field.description,
                placeholder=field.placeholder,
                order=field.order,
                step_tag=field.step_tag,
                section_tag=field.section_tag,
                options=field.options,
                validation_rules=field.validation_rules,
                ui_config=field.ui_config,
                default_value=field.default_value,
                is_required=field.is_required,
                is_indexed=field.is_indexed,
                is_hidden=field.is_hidden,
                is_readonly=field.is_readonly,
            )
        
        logger.info(
            "forms.template.versioned",
            form_id=str(new_version.id),
            old_version=form_template.version,
            new_version=new_version.version,
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_VERSIONED,
            actor=updated_by,
            resource=new_version,
            request=request,
            details={
                "old_version": form_template.version,
                "new_version": new_version.version,
                "parent_id": str(form_template.id),
            }
        )
        
        return new_version
    
    @staticmethod
    @transaction.atomic
    def publish_form(
        *,
        form_template: FormTemplate,
        published_by,
        request: Optional[HttpRequest] = None
    ) -> FormTemplate:
        """Publish a draft form to active status."""
        if form_template.status != FormStatus.DRAFT:
            raise BusinessRuleViolation(
                message="Only draft forms can be published",
                rule="form_publish_from_draft"
            )
        
        form_template.status = FormStatus.ACTIVE
        form_template.updated_by = published_by
        form_template.save(update_fields=['status', 'updated_by', 'updated_at'])

        logger.info(
            "forms.template.published",
            form_id=str(form_template.id),
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_PUBLISHED,
            actor=published_by,
            resource=form_template,
            request=request,
        )
        
        return form_template
    
    @staticmethod
    @transaction.atomic
    def archive_form(
        *,
        form_template: FormTemplate,
        archived_by,
        request: Optional[HttpRequest] = None
    ) -> FormTemplate:
        """Archive an active form."""
        if form_template.status != FormStatus.ACTIVE:
            raise BusinessRuleViolation(
                message="Only active forms can be archived",
                rule="form_archive_from_active"
            )
        
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be archived",
                action="archive",
                resource="FormTemplate"
            )
        
        form_template.status = FormStatus.ARCHIVED
        form_template.updated_by = archived_by
        form_template.save(update_fields=['status', 'updated_by', 'updated_at'])

        logger.info(
            "forms.template.archived",
            form_id=str(form_template.id),
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_ARCHIVED,
            actor=archived_by,
            resource=form_template,
            request=request,
        )
        
        return form_template
    
    @staticmethod
    @transaction.atomic
    def delete_form(
        *,
        form_template: FormTemplate,
        deleted_by,
        request: Optional[HttpRequest] = None
    ) -> FormTemplate:
        """Soft delete a form template."""
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be deleted",
                action="delete",
                resource="FormTemplate"
            )
        
        form_template.status = FormStatus.DELETED
        form_template.soft_delete(user=deleted_by)
        
        logger.info(
            "forms.template.deleted",
            form_id=str(form_template.id),
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_DELETED,
            actor=deleted_by,
            resource=form_template,
            request=request,
        )
        
        return form_template
    
    @staticmethod
    @transaction.atomic
    def fork_template(
        *,
        source_template: FormTemplate,
        actor_context: "ActorContext",
        actor,
        request: Optional[HttpRequest] = None,
        new_owner_type: str,
        new_owner_id: UUID,
        new_name: Optional[str] = None,
        new_slug: Optional[str] = None
    ) -> FormTemplate:
        """
        Fork a public template to create a new owned copy.

        Args:
            source_template: Template to fork
            actor_context: Pre-built ActorContext from view
            actor: User object for audit logging (membership.user)
            new_owner_type: Owner type for new form
            new_owner_id: Owner ID for new form
            new_name: Override name (optional)
            new_slug: Override slug (optional)

        Returns:
            New forked FormTemplate
        """
        # Validate source can be forked
        if not source_template.is_template_public:
            raise PermissionDenied(
                message="Only public templates can be forked",
                action="fork",
                resource="FormTemplate",
            )

        if source_template.is_system_form:
            raise BusinessRuleViolation(
                message="System forms cannot be forked",
                rule="system_form_immutable",
            )
        
        name = new_name or f"{source_template.name} (Copy)"
        slug = new_slug or slugify(name)[:100]
        
        # Ensure unique slug
        counter = 1
        original_slug = slug
        while FormTemplate.objects.filter(
            owner_type=new_owner_type,
            owner_id=new_owner_id,
            slug=slug,
            is_current=True
        ).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        # Create forked template
        forked = FormTemplate.objects.create(
            name=name,
            slug=slug,
            description=source_template.description,
            owner_type=new_owner_type,
            owner_id=new_owner_id,
            scope=source_template.scope,
            creator_context=actor_context.to_dict(),
            created_by=actor,
            status=FormStatus.DRAFT,
            version=1,
            is_current=True,
            forked_from=source_template,
            settings=source_template.settings.copy(),
        )
        
        # Copy fields
        for field in source_template.fields.all():
            FormField.objects.create(
                form_template=forked,
                field_key=field.field_key,
                field_type=field.field_type,
                label=field.label,
                description=field.description,
                placeholder=field.placeholder,
                order=field.order,
                step_tag=field.step_tag,
                section_tag=field.section_tag,
                options=field.options.copy() if field.options else [],
                validation_rules=field.validation_rules.copy() if field.validation_rules else {},
                ui_config=field.ui_config.copy() if field.ui_config else {},
                default_value=field.default_value,
                is_required=field.is_required,
                is_indexed=field.is_indexed,
                is_hidden=field.is_hidden,
                is_readonly=field.is_readonly,
            )
        
        logger.info(
            "forms.template.forked",
            form_id=str(forked.id),
            source_id=str(source_template.id),
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_FORKED,
            actor=actor,
            resource=forked,
            request=request,
            details={
                "source_id": str(source_template.id),
                "source_name": source_template.name,
            }
        )
        
        return forked
    
    @staticmethod
    @transaction.atomic
    def add_field(
        *,
        form_template: FormTemplate,
        added_by,
        request: Optional[HttpRequest] = None,
        field_key: str,
        field_type: str,
        label: str,
        order: int,
        description: str = "",
        placeholder: str = "",
        step_tag: str = "",
        section_tag: str = "",
        options: Optional[List] = None,
        validation_rules: Optional[Dict] = None,
        ui_config: Optional[Dict] = None,
        default_value: Any = None,
        is_required: bool = False,
        is_indexed: bool = False,
        is_hidden: bool = False,
        is_readonly: bool = False
    ) -> FormField:
        """Add a field to a form template."""
        if not form_template.is_editable:
            raise BusinessRuleViolation(
                message="Cannot add fields to non-editable form",
                rule="form_immutability"
            )
        
        # Validate field_key uniqueness
        if FormField.objects.filter(
            form_template=form_template,
            field_key=field_key
        ).exists():
            raise ConflictError(
                message=f"Field key '{field_key}' already exists",
                resource="FormField",
                conflict_type="duplicate"
            )
        
        # Validate indexing
        if is_indexed:
            storage_type = FIELD_STORAGE_MAP.get(field_type)
            if storage_type not in INDEXABLE_STORAGE_TYPES:
                raise ValidationError(
                    message=f"Field type '{field_type}' cannot be indexed",
                    field="is_indexed"
                )
            
            indexed_count = FormTemplateSelector.count_indexed_fields(
                form_template_id=form_template.id
            )
            if indexed_count >= MAX_INDEXED_FIELDS:
                raise ValidationError(
                    message=f"Maximum {MAX_INDEXED_FIELDS} indexed fields allowed",
                    field="is_indexed"
                )
        
        field = FormField.objects.create(
            form_template=form_template,
            field_key=field_key,
            field_type=field_type,
            label=label,
            description=description,
            placeholder=placeholder,
            order=order,
            step_tag=step_tag,
            section_tag=section_tag,
            options=options or [],
            validation_rules=validation_rules or {},
            ui_config=ui_config or {},
            default_value=default_value,
            is_required=is_required,
            is_indexed=is_indexed,
            is_hidden=is_hidden,
            is_readonly=is_readonly,
        )
        
        logger.info(
            "forms.field.added",
            form_id=str(form_template.id),
            field_id=str(field.id),
            field_key=field_key,
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_FIELD_ADDED,
            actor=added_by,
            resource=field,
            request=request,
            details={
                "form_id": str(form_template.id),
                "field_key": field_key,
                "field_type": field_type,
            }
        )
        
        return field
```

### 7.2 FormResponseService

```python
class FormResponseService:
    """
    Service for form response submission and management.
    """
    
    @staticmethod
    @transaction.atomic
    def create_response(
        *,
        form_template: FormTemplate,
        actor_context: "ActorContext",
        actor,
        request: Optional[HttpRequest] = None,
        data: Dict[str, Any]
    ) -> FormResponse:
        """
        Create a draft response for a form.

        Args:
            form_template: The form to respond to
            actor_context: Pre-built ActorContext from view
            actor: User object for audit logging (membership.user)
            data: Initial response data

        Returns:
            Created FormResponse in draft status
        """
        if not form_template.accepts_responses:
            raise BusinessRuleViolation(
                message="This form is not accepting responses",
                rule="form_accepts_responses",
            )

        response = FormResponse.objects.create(
            form_template=form_template,
            form_version=form_template.version,
            submitted_by=actor,
            submitter_context=actor_context.to_dict(),
            data=data,
            status=ResponseStatus.DRAFT,
        )

        logger.info(
            "forms.response.created",
            response_id=str(response.id),
            form_id=str(form_template.id),
        )

        AuditService.log(
            action=AuditLog.Action.FORM_RESPONSE_CREATED,
            actor=actor,
            resource=response,
            request=request,
        )

        return response
    
    @staticmethod
    @transaction.atomic
    def update_response(
        *,
        response: FormResponse,
        updated_by,
        request: Optional[HttpRequest] = None,
        data: Dict[str, Any]
    ) -> FormResponse:
        """Update a draft or submitted response."""
        if not response.is_editable:
            raise BusinessRuleViolation(
                message="This response cannot be edited",
                rule="response_immutability"
            )
        
        old_data = response.data
        response.data = data
        response.save(update_fields=['data', 'updated_at'])
        
        logger.info(
            "forms.response.updated",
            response_id=str(response.id),
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_RESPONSE_UPDATED,
            actor=updated_by,
            resource=response,
            request=request,
        )
        
        return response
    
    @staticmethod
    @transaction.atomic
    def submit_response(
        *,
        response: FormResponse,
        actor_context: "ActorContext",
        actor,
        request: Optional[HttpRequest] = None
    ) -> FormResponse:
        """
        Submit a draft response.

        This captures the submitter context and extracts indexed fields.

        Args:
            response: The draft response to submit
            actor_context: Pre-built ActorContext from view (for context capture)
            actor: User object for audit logging (membership.user)
            request: HTTP request for audit context
        """
        if response.status != ResponseStatus.DRAFT:
            raise BusinessRuleViolation(
                message="Only draft responses can be submitted",
                rule="response_submit_from_draft",
            )

        # Validate required fields
        form = response.form_template
        required_fields = FormField.objects.filter(
            form_template=form,
            is_required=True,
        ).values_list('field_key', flat=True)

        missing = [key for key in required_fields if not response.data.get(key)]
        if missing:
            raise ValidationError(
                message=f"Required fields missing: {', '.join(missing)}",
                field="data",
            )

        # Capture fresh submitter context at submission time
        response.submitter_context = actor_context.to_dict()
        response.status = ResponseStatus.SUBMITTED
        response.submitted_at = timezone.now()
        response.save(update_fields=[
            'submitter_context', 'status', 'submitted_at', 'updated_at',
        ])

        # Extract and store indexed field values
        IndexService.extract_and_store_indexes(response=response)

        logger.info(
            "forms.response.submitted",
            response_id=str(response.id),
            form_id=str(form.id),
        )

        AuditService.log(
            action=AuditLog.Action.FORM_RESPONSE_SUBMITTED,
            actor=actor,
            resource=response,
            request=request,
        )

        return response
    
    @staticmethod
    @transaction.atomic
    def process_response(
        *,
        response: FormResponse,
        processed_by,
        request: Optional[HttpRequest] = None,
        notes: str = ""
    ) -> FormResponse:
        """Mark a submitted response as processed."""
        if response.status != ResponseStatus.SUBMITTED:
            raise BusinessRuleViolation(
                message="Only submitted responses can be processed",
                rule="response_process_from_submitted"
            )
        
        response.status = ResponseStatus.PROCESSED
        response.processed_at = timezone.now()
        response.processed_by = processed_by
        response.processor_notes = notes
        response.save(update_fields=[
            'status', 'processed_at', 'processed_by', 'processor_notes', 'updated_at'
        ])
        
        logger.info(
            "forms.response.processed",
            response_id=str(response.id),
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_RESPONSE_PROCESSED,
            actor=processed_by,
            resource=response,
            request=request,
            details={"notes": notes} if notes else {},
        )
        
        return response
    
    @staticmethod
    @transaction.atomic
    def void_response(
        *,
        response: FormResponse,
        voided_by,
        request: Optional[HttpRequest] = None,
        reason: str = ""
    ) -> FormResponse:
        """Void a submitted response (withdraw/invalidate)."""
        if response.status not in [ResponseStatus.DRAFT, ResponseStatus.SUBMITTED]:
            raise BusinessRuleViolation(
                message="Only draft or submitted responses can be voided",
                rule="response_void_allowed_states"
            )
        
        response.status = ResponseStatus.VOID
        response.save(update_fields=['status', 'updated_at'])
        
        logger.info(
            "forms.response.voided",
            response_id=str(response.id),
            reason=reason,
        )
        
        AuditService.log(
            action=AuditLog.Action.FORM_RESPONSE_VOIDED,
            actor=voided_by,
            resource=response,
            request=request,
            details={"reason": reason} if reason else {},
        )
        
        return response
```

### 7.3 IndexService (`apps/forms/indexing.py`)

```python
from typing import Dict, Any
from apps.forms.models import (
    FormResponse, FormField,
    TextFieldIndex, IntegerFieldIndex, DecimalFieldIndex,
    BooleanFieldIndex, DateFieldIndex, DateTimeFieldIndex
)
from apps.forms.constants import FIELD_STORAGE_MAP
from apps.core.constants import StorageType
from apps.core.observability import get_logger
from datetime import date, datetime
from decimal import Decimal

logger = get_logger(__name__)


class IndexService:
    """Service for managing field value indexes."""
    
    INDEX_MODELS = {
        StorageType.TEXT: TextFieldIndex,
        StorageType.INTEGER: IntegerFieldIndex,
        StorageType.DECIMAL: DecimalFieldIndex,
        StorageType.BOOLEAN: BooleanFieldIndex,
        StorageType.DATE: DateFieldIndex,
        StorageType.DATETIME: DateTimeFieldIndex,
    }
    
    @staticmethod
    def extract_and_store_indexes(*, response: FormResponse) -> None:
        """
        Extract indexed field values and store in appropriate index tables.
        
        Called at response submission time.
        """
        # Get indexed fields for the form
        indexed_fields = FormField.objects.filter(
            form_template=response.form_template,
            is_indexed=True
        )
        
        for field in indexed_fields:
            value = response.data.get(field.field_key)
            if value is None:
                continue
            
            storage_type = FIELD_STORAGE_MAP.get(field.field_type)
            if not storage_type or storage_type == StorageType.JSON:
                continue
            
            IndexModel = IndexService.INDEX_MODELS.get(storage_type)
            if not IndexModel:
                continue
            
            try:
                # Convert value to appropriate type
                typed_value = IndexService._convert_value(value, storage_type)
                
                IndexModel.objects.create(
                    response=response,
                    field_key=field.field_key,
                    value=typed_value
                )
                
                logger.debug(
                    "forms.index.created",
                    response_id=str(response.id),
                    field_key=field.field_key,
                    storage_type=storage_type,
                )
            except (ValueError, TypeError) as e:
                logger.warning(
                    "forms.index.conversion_failed",
                    response_id=str(response.id),
                    field_key=field.field_key,
                    error=str(e),
                )
    
    @staticmethod
    def _convert_value(value: Any, storage_type: str) -> Any:
        """Convert value to appropriate type for storage."""
        if storage_type == StorageType.TEXT:
            return str(value)
        elif storage_type == StorageType.INTEGER:
            return int(value)
        elif storage_type == StorageType.DECIMAL:
            return Decimal(str(value))
        elif storage_type == StorageType.BOOLEAN:
            if isinstance(value, bool):
                return value
            return str(value).lower() in ('true', '1', 'yes')
        elif storage_type == StorageType.DATE:
            if isinstance(value, date):
                return value
            return date.fromisoformat(value)
        elif storage_type == StorageType.DATETIME:
            if isinstance(value, datetime):
                return value
            return datetime.fromisoformat(value)
        return value
    
    @staticmethod
    def clear_indexes(*, response: FormResponse) -> None:
        """Clear all indexes for a response (used when re-indexing)."""
        for IndexModel in IndexService.INDEX_MODELS.values():
            IndexModel.objects.filter(response=response).delete()
```

---

## 8. Serializers

### 8.1 Input Serializers (`apps/forms/serializers.py`)

```python
from rest_framework import serializers
from apps.core.serializers import BaseInputSerializer, BaseOutputSerializer
from apps.core.constants import FormStatus, ResponseStatus, FieldType, OwnerType, FormScope
from apps.forms.models import FormTemplate, FormField, FormResponse


# ============================================================================
# INPUT SERIALIZERS
# ============================================================================

class FormTemplateCreateInputSerializer(BaseInputSerializer):
    """Input for creating a form template."""
    name = serializers.CharField(max_length=255)
    slug = serializers.SlugField(max_length=100, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    owner_type = serializers.ChoiceField(choices=OwnerType.choices)
    owner_id = serializers.UUIDField(required=False, allow_null=True)
    scope = serializers.ChoiceField(choices=FormScope.choices)
    settings = serializers.JSONField(required=False, default=dict)


class FormTemplateUpdateInputSerializer(BaseInputSerializer):
    """Input for updating a form template."""
    name = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    settings = serializers.JSONField(required=False)


class FormFieldCreateInputSerializer(BaseInputSerializer):
    """Input for adding a field to a form."""
    field_key = serializers.CharField(max_length=100)
    field_type = serializers.ChoiceField(choices=FieldType.choices)
    label = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    placeholder = serializers.CharField(required=False, allow_blank=True, default="")
    order = serializers.IntegerField(min_value=0)
    step_tag = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    section_tag = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    options = serializers.ListField(required=False, default=list)
    validation_rules = serializers.JSONField(required=False, default=dict)
    ui_config = serializers.JSONField(required=False, default=dict)
    default_value = serializers.JSONField(required=False, allow_null=True)
    is_required = serializers.BooleanField(default=False)
    is_indexed = serializers.BooleanField(default=False)
    is_hidden = serializers.BooleanField(default=False)
    is_readonly = serializers.BooleanField(default=False)


class FormFieldUpdateInputSerializer(BaseInputSerializer):
    """Input for updating a field."""
    label = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    placeholder = serializers.CharField(required=False, allow_blank=True)
    order = serializers.IntegerField(min_value=0, required=False)
    step_tag = serializers.CharField(max_length=50, required=False, allow_blank=True)
    section_tag = serializers.CharField(max_length=50, required=False, allow_blank=True)
    options = serializers.ListField(required=False)
    validation_rules = serializers.JSONField(required=False)
    ui_config = serializers.JSONField(required=False)
    default_value = serializers.JSONField(required=False, allow_null=True)
    is_required = serializers.BooleanField(required=False)
    is_indexed = serializers.BooleanField(required=False)
    is_hidden = serializers.BooleanField(required=False)
    is_readonly = serializers.BooleanField(required=False)


class FormResponseCreateInputSerializer(BaseInputSerializer):
    """Input for creating a response."""
    data = serializers.JSONField()


class FormResponseUpdateInputSerializer(BaseInputSerializer):
    """Input for updating response data."""
    data = serializers.JSONField()


class FormResponseProcessInputSerializer(BaseInputSerializer):
    """Input for processing a response."""
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class FormResponseVoidInputSerializer(BaseInputSerializer):
    """Input for voiding a response."""
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ForkTemplateInputSerializer(BaseInputSerializer):
    """Input for forking a template."""
    new_owner_type = serializers.ChoiceField(choices=OwnerType.choices)
    new_owner_id = serializers.UUIDField()
    new_name = serializers.CharField(max_length=255, required=False)
    new_slug = serializers.SlugField(max_length=100, required=False)
```

### 8.2 Output Serializers

```python
# ============================================================================
# OUTPUT SERIALIZERS
# ============================================================================

class FormFieldOutputSerializer(BaseOutputSerializer):
    """Output for form fields."""
    
    class Meta:
        model = FormField
        fields = [
            'id', 'field_key', 'field_type', 'label', 'description',
            'placeholder', 'order', 'step_tag', 'section_tag', 'options',
            'validation_rules', 'ui_config', 'default_value',
            'is_required', 'is_indexed', 'is_hidden', 'is_readonly',
        ]
        read_only_fields = fields


class FormTemplateListOutputSerializer(BaseOutputSerializer):
    """Minimal output for form template lists."""
    
    class Meta:
        model = FormTemplate
        fields = [
            'id', 'name', 'slug', 'description', 'owner_type',
            'scope', 'status', 'version', 'is_current',
            'is_template_public', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class FormTemplateDetailOutputSerializer(BaseOutputSerializer):
    """Detailed output for form template with fields."""
    fields = FormFieldOutputSerializer(many=True, read_only=True)
    forked_from_name = serializers.CharField(
        source='forked_from.name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = FormTemplate
        fields = [
            'id', 'name', 'slug', 'description', 'owner_type', 'owner_id',
            'scope', 'status', 'version', 'is_current', 'parent_version',
            'is_template_public', 'forked_from', 'forked_from_name',
            'settings', 'fields', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class FormResponseListOutputSerializer(BaseOutputSerializer):
    """Minimal output for response lists."""
    form_name = serializers.CharField(source='form_template.name', read_only=True)
    submitter_email = serializers.CharField(source='submitted_by.email', read_only=True)
    
    class Meta:
        model = FormResponse
        fields = [
            'id', 'form_template', 'form_name', 'form_version',
            'submitted_by', 'submitter_email', 'status',
            'submitted_at', 'processed_at', 'created_at',
        ]
        read_only_fields = fields


class FormResponseDetailOutputSerializer(BaseOutputSerializer):
    """Detailed output for a single response."""
    form_name = serializers.CharField(source='form_template.name', read_only=True)
    submitter_email = serializers.CharField(source='submitted_by.email', read_only=True)
    processor_email = serializers.CharField(
        source='processed_by.email',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = FormResponse
        fields = [
            'id', 'form_template', 'form_name', 'form_version',
            'submitted_by', 'submitter_email', 'submitter_context',
            'data', 'status', 'submitted_at', 'processed_at',
            'processed_by', 'processor_email', 'processor_notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields
```

---

## 9. Views & ViewSets

### 9.1 FormTemplate Views (`apps/forms/views.py`)

```python
from uuid import UUID
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.core.permissions import IsAuthenticated
from apps.core.pagination import StandardPagination
from apps.core.serializers import EmptySerializer, MessageSerializer
from apps.forms.serializers import (
    FormTemplateCreateInputSerializer,
    FormTemplateUpdateInputSerializer,
    FormTemplateListOutputSerializer,
    FormTemplateDetailOutputSerializer,
    FormFieldCreateInputSerializer,
    FormFieldOutputSerializer,
    ForkTemplateInputSerializer,
)
from apps.forms.selectors import FormTemplateSelector, FormFieldSelector
from apps.forms.services import FormBuilderService
from apps.forms.policies import FormTemplatePolicy

from apps.rbac.selectors import MembershipSelector
from apps.rbac.services import RBACService
from apps.core.types import ActorContext


class FormViewMixin:
    """Resolve membership and ActorContext for form views."""

    def get_membership_or_403(self, request, account_type, account_id):
        """
        Get the actor's active membership for the given account context.
        Raises PermissionDenied if not a member.
        """
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=account_type,
            account_id=account_id,
        )
        if not membership:
            from apps.core.exceptions import PermissionDenied
            raise PermissionDenied(
                message="Not a member of this account",
                action="access",
                resource="FormTemplate",
            )
        return membership

    def get_actor_context(self, membership, request):
        """Build ActorContext from membership."""
        return RBACService.build_actor_context(
            membership=membership,
            request=request,
        )


class FormTemplateListView(FormViewMixin, APIView):
    """List and create form templates."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List form templates",
        responses={200: FormTemplateListOutputSerializer(many=True)},
        tags=["Forms"]
    )
    def get(self, request, account_type: str, account_id: UUID):
        """List form templates for an account."""
        membership = self.get_membership_or_403(request, account_type, account_id)

        forms = FormTemplateSelector.list_by_owner(
            owner_type=account_type,
            owner_id=account_id
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(forms, request)
        serializer = FormTemplateListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create form template",
        request=FormTemplateCreateInputSerializer,
        responses={201: FormTemplateDetailOutputSerializer},
        tags=["Forms"]
    )
    def post(self, request, account_type: str, account_id: UUID):
        """Create a new form template."""
        input_serializer = FormTemplateCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        membership = self.get_membership_or_403(request, account_type, account_id)
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_create_form(
            actor_context=actor_context,
            owner_type=input_serializer.validated_data["owner_type"],
        )

        form = FormBuilderService.create_form_template(
            actor_context=actor_context,
            actor=membership.user,
            request=request,
            **input_serializer.validated_data
        )

        output_serializer = FormTemplateDetailOutputSerializer(form)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class FormTemplateDetailView(FormViewMixin, APIView):
    """Retrieve, update, delete form templates."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get form template details",
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"]
    )
    def get(self, request, form_id: UUID):
        """Get form template with fields."""
        form = FormTemplateSelector.get_with_fields(form_template_id=form_id)

        # Public templates viewable by all authenticated users
        if not form.is_template_public:
            membership = self.get_membership_or_403(
                request, form.owner_type, form.owner_id,
            )
            actor_context = self.get_actor_context(membership, request)
            FormTemplatePolicy.can_view_form(
                actor_context=actor_context, form_template=form,
            )

        serializer = FormTemplateDetailOutputSerializer(form)
        return Response(serializer.data)

    @extend_schema(
        summary="Update form template",
        request=FormTemplateUpdateInputSerializer,
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"]
    )
    def patch(self, request, form_id: UUID):
        """Update form template."""
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request, form.owner_type, form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context, form_template=form,
        )

        input_serializer = FormTemplateUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        form = FormBuilderService.update_form_template(
            form_template=form,
            actor=membership.user,
            actor_context=actor_context,
            request=request,
            **input_serializer.validated_data
        )

        output_serializer = FormTemplateDetailOutputSerializer(form)
        return Response(output_serializer.data)

    @extend_schema(
        summary="Delete form template",
        responses={204: EmptySerializer},
        tags=["Forms"]
    )
    def delete(self, request, form_id: UUID):
        """Soft delete form template."""
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request, form.owner_type, form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_delete_form(
            actor_context=actor_context, form_template=form,
        )

        FormBuilderService.delete_form(
            form_template=form,
            actor=membership.user,
            request=request,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class FormTemplatePublishView(FormViewMixin, APIView):
    """Publish a draft form template."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Publish form template",
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"]
    )
    def post(self, request, form_id: UUID):
        """Publish a draft form to active."""
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request, form.owner_type, form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context, form_template=form,
        )

        form = FormBuilderService.publish_form(
            form_template=form,
            published_by=membership.user,
            request=request,
        )

        serializer = FormTemplateDetailOutputSerializer(form)
        return Response(serializer.data)


class FormTemplateArchiveView(FormViewMixin, APIView):
    """Archive an active form template."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Archive form template",
        responses={200: FormTemplateDetailOutputSerializer},
        tags=["Forms"]
    )
    def post(self, request, form_id: UUID):
        """Archive an active form."""
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request, form.owner_type, form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_edit_form(
            actor_context=actor_context, form_template=form,
        )

        form = FormBuilderService.archive_form(
            form_template=form,
            archived_by=membership.user,
            request=request,
        )

        serializer = FormTemplateDetailOutputSerializer(form)
        return Response(serializer.data)


class FormTemplateForkView(FormViewMixin, APIView):
    """Fork a public template."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Fork a public template",
        request=ForkTemplateInputSerializer,
        responses={201: FormTemplateDetailOutputSerializer},
        tags=["Forms"]
    )
    def post(self, request, form_id: UUID):
        """Fork a public template to create owned copy."""
        source = FormTemplateSelector.get_by_id(form_template_id=form_id)

        input_serializer = ForkTemplateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        data = input_serializer.validated_data

        membership = self.get_membership_or_403(
            request, data['new_owner_type'], data['new_owner_id'],
        )
        actor_context = self.get_actor_context(membership, request)

        FormTemplatePolicy.can_create_form(
            actor_context=actor_context, owner_type=data['new_owner_type'],
        )

        forked = FormBuilderService.fork_template(
            source_template=source,
            actor_context=actor_context,
            actor=membership.user,
            request=request,
            **data,
        )

        serializer = FormTemplateDetailOutputSerializer(forked)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PublicTemplateLibraryView(APIView):
    """Browse public template library."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List public templates",
        responses={200: FormTemplateListOutputSerializer(many=True)},
        tags=["Forms"]
    )
    def get(self, request):
        """List all public templates available for forking."""
        scope = request.query_params.get('scope')
        
        templates = FormTemplateSelector.list_public_templates(scope=scope)
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(templates, request)
        serializer = FormTemplateListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
```

### 9.2 FormResponse Views

```python
from uuid import UUID
from apps.forms.serializers import (
    FormResponseCreateInputSerializer,
    FormResponseUpdateInputSerializer,
    FormResponseProcessInputSerializer,
    FormResponseVoidInputSerializer,
    FormResponseListOutputSerializer,
    FormResponseDetailOutputSerializer,
)
from apps.forms.selectors import FormTemplateSelector, FormResponseSelector
from apps.forms.services import FormResponseService
from apps.forms.policies import FormResponsePolicy
from apps.rbac.selectors import MembershipSelector
from apps.rbac.services import RBACService


class FormResponseListView(FormViewMixin, APIView):
    """List and create form responses."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List responses for a form",
        responses={200: FormResponseListOutputSerializer(many=True)},
        tags=["Form Responses"]
    )
    def get(self, request, form_id: UUID):
        """List responses for a form template."""
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)
        membership = self.get_membership_or_403(
            request, form.owner_type, form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormResponsePolicy.can_view_responses(
            actor_context=actor_context, form_template=form,
        )

        status_filter = request.query_params.get('status')
        responses = FormResponseSelector.list_by_form(
            form_template_id=form_id,
            status=status_filter,
        )

        paginator = StandardPagination()
        page = paginator.paginate_queryset(responses, request)
        serializer = FormResponseListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create form response",
        request=FormResponseCreateInputSerializer,
        responses={201: FormResponseDetailOutputSerializer},
        tags=["Form Responses"]
    )
    def post(self, request, form_id: UUID):
        """Create a new draft response."""
        form = FormTemplateSelector.get_by_id(form_template_id=form_id)

        input_serializer = FormResponseCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        membership = self.get_membership_or_403(
            request, form.owner_type, form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        response = FormResponseService.create_response(
            form_template=form,
            actor_context=actor_context,
            actor=membership.user,
            request=request,
            **input_serializer.validated_data,
        )

        output_serializer = FormResponseDetailOutputSerializer(response)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED)


class FormResponseDetailView(APIView):
    """Retrieve and update form responses."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get response details",
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"]
    )
    def get(self, request, response_id: UUID):
        """Get response details."""
        response = FormResponseSelector.get_by_id(response_id=response_id)

        # Owner can always view their own response
        if response.submitted_by_id == request.user.id:
            pass  # allowed
        else:
            # Non-owner needs can_view_responses permission
            form = response.form_template
            membership = MembershipSelector.get_active_membership_for_user_account(
                user=request.user,
                account_type=form.owner_type,
                account_id=form.owner_id,
            )
            if not membership:
                from apps.core.exceptions import PermissionDenied
                raise PermissionDenied(
                    message="Not a member of this account",
                    action="view",
                    resource="FormResponse",
                )
            actor_context = RBACService.build_actor_context(
                membership=membership, request=request,
            )
            FormResponsePolicy.can_view_responses(
                actor_context=actor_context, form_template=form,
            )

        serializer = FormResponseDetailOutputSerializer(response)
        return Response(serializer.data)

    @extend_schema(
        summary="Update response data",
        request=FormResponseUpdateInputSerializer,
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"]
    )
    def patch(self, request, response_id: UUID):
        """Update response data."""
        response = FormResponseSelector.get_by_id(response_id=response_id)

        FormResponsePolicy.can_edit_response(
            user=request.user, response=response,
        )

        input_serializer = FormResponseUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        response = FormResponseService.update_response(
            response=response,
            updated_by=request.user,
            request=request,
            **input_serializer.validated_data,
        )

        output_serializer = FormResponseDetailOutputSerializer(response)
        return Response(output_serializer.data)


class FormResponseSubmitView(FormViewMixin, APIView):
    """Submit a draft response."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Submit response",
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"]
    )
    def post(self, request, response_id: UUID):
        """Submit a draft response."""
        response = FormResponseSelector.get_by_id(response_id=response_id)

        FormResponsePolicy.can_edit_response(
            user=request.user, response=response,
        )

        form = response.form_template
        membership = self.get_membership_or_403(
            request, form.owner_type, form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        response = FormResponseService.submit_response(
            response=response,
            actor_context=actor_context,
            actor=membership.user,
            request=request,
        )

        serializer = FormResponseDetailOutputSerializer(response)
        return Response(serializer.data)


class FormResponseProcessView(FormViewMixin, APIView):
    """Process a submitted response."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Process response",
        request=FormResponseProcessInputSerializer,
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"]
    )
    def post(self, request, response_id: UUID):
        """Mark response as processed."""
        response = FormResponseSelector.get_by_id(response_id=response_id)
        form = response.form_template

        membership = self.get_membership_or_403(
            request, form.owner_type, form.owner_id,
        )
        actor_context = self.get_actor_context(membership, request)

        FormResponsePolicy.can_process_response(
            actor_context=actor_context, response=response,
        )

        input_serializer = FormResponseProcessInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        response = FormResponseService.process_response(
            response=response,
            processed_by=membership.user,
            request=request,
            **input_serializer.validated_data,
        )

        serializer = FormResponseDetailOutputSerializer(response)
        return Response(serializer.data)


class FormResponseVoidView(FormViewMixin, APIView):
    """Void a response."""
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Void response",
        request=FormResponseVoidInputSerializer,
        responses={200: FormResponseDetailOutputSerializer},
        tags=["Form Responses"]
    )
    def post(self, request, response_id: UUID):
        """Void a draft or submitted response."""
        response = FormResponseSelector.get_by_id(response_id=response_id)

        # Owner can void their own, admin needs can_process_response
        if response.submitted_by_id == request.user.id:
            pass  # owner can void own
        else:
            form = response.form_template
            membership = self.get_membership_or_403(
                request, form.owner_type, form.owner_id,
            )
            actor_context = self.get_actor_context(membership, request)
            FormResponsePolicy.can_process_response(
                actor_context=actor_context, response=response,
            )

        input_serializer = FormResponseVoidInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        response = FormResponseService.void_response(
            response=response,
            voided_by=request.user,
            request=request,
            **input_serializer.validated_data,
        )

        serializer = FormResponseDetailOutputSerializer(response)
        return Response(serializer.data)


class MyResponsesView(APIView):
    """Current user's form responses."""
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="List my responses",
        responses={200: FormResponseListOutputSerializer(many=True)},
        tags=["Form Responses"]
    )
    def get(self, request):
        """List current user's responses."""
        form_id = request.query_params.get('form_id')
        
        responses = FormResponseSelector.list_by_submitter(
            user_id=request.user.id,
            form_template_id=form_id
        )
        
        paginator = StandardPagination()
        page = paginator.paginate_queryset(responses, request)
        serializer = FormResponseListOutputSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
```

---

## 10. URLs

### 10.1 URL Configuration (`apps/forms/urls.py`)

```python
from django.urls import path
from apps.forms.views import (
    # Form Templates
    FormTemplateListView,
    FormTemplateDetailView,
    FormTemplatePublishView,
    FormTemplateArchiveView,
    FormTemplateForkView,
    PublicTemplateLibraryView,
    # Form Responses
    FormResponseListView,
    FormResponseDetailView,
    FormResponseSubmitView,
    FormResponseProcessView,
    FormResponseVoidView,
    MyResponsesView,
)

app_name = "forms"

urlpatterns = [
    # Public template library
    path("templates/library/", PublicTemplateLibraryView.as_view(), name="template-library"),
    
    # Form templates (scoped by account)
    path(
        "<str:account_type>/<uuid:account_id>/templates/",
        FormTemplateListView.as_view(),
        name="template-list"
    ),
    
    # Form template operations
    path("templates/<uuid:form_id>/", FormTemplateDetailView.as_view(), name="template-detail"),
    path("templates/<uuid:form_id>/publish/", FormTemplatePublishView.as_view(), name="template-publish"),
    path("templates/<uuid:form_id>/archive/", FormTemplateArchiveView.as_view(), name="template-archive"),
    path("templates/<uuid:form_id>/fork/", FormTemplateForkView.as_view(), name="template-fork"),
    
    # Form responses
    path("templates/<uuid:form_id>/responses/", FormResponseListView.as_view(), name="response-list"),
    path("responses/<uuid:response_id>/", FormResponseDetailView.as_view(), name="response-detail"),
    path("responses/<uuid:response_id>/submit/", FormResponseSubmitView.as_view(), name="response-submit"),
    path("responses/<uuid:response_id>/process/", FormResponseProcessView.as_view(), name="response-process"),
    path("responses/<uuid:response_id>/void/", FormResponseVoidView.as_view(), name="response-void"),
    
    # User's own responses
    path("me/responses/", MyResponsesView.as_view(), name="my-responses"),
]
```

### 10.2 Register in Main URLs

```python
# backend_core/urls.py

urlpatterns = [
    # ...
    path("api/v1/forms/", include("apps.forms.urls", namespace="forms")),
]
```

---

## 11. Signals

### 11.1 Form Signals (`apps/forms/signals.py`)

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction

from apps.forms.models import FormResponse
from apps.core.constants import ResponseStatus


@receiver(post_save, sender=FormResponse)
def on_response_submitted(sender, instance, created, **kwargs):
    """
    React to response submission.
    
    STUB: Trigger notification when response is submitted
    """
    if not created and instance.status == ResponseStatus.SUBMITTED:
        # Schedule notification after commit
        transaction.on_commit(
            lambda: _notify_response_submitted(instance.id)
        )


def _notify_response_submitted(response_id):
    """
    STUB: Send notification for submitted response.
    
    This will be implemented by Notification System.
    Expected: NotificationService.send(
        notification_type=NotificationType.FORM_RESPONSE_SUBMITTED,
        recipient=...,
        context={...}
    )
    """
    pass
```

---

## 12. Permissions & Policies

### 12.1 FormTemplatePolicy (`apps/forms/policies.py`)

```python
from apps.core.exceptions import PermissionDenied
from apps.core.types import ActorContext
from apps.forms.models import FormTemplate, FormResponse


class FormTemplatePolicy:
    """
    Authorization policies for form template operations.

    Uses the 6 form permissions from RBAC registry:
    - can_create_form (business, platform_only)
    - can_edit_form (business, platform_only, global_only)
    - can_delete_form (business, platform_only, global_only)
    - can_view_responses (business, platform_only, global_only)
    - can_export_responses (business, platform_only, global_only)
    - can_process_response (business, platform_only, global_only)

    All methods accept `actor_context: ActorContext` which contains the
    pre-built permissions_snapshot from RBACService.build_actor_context().
    """

    @staticmethod
    def can_create_form(*, actor_context: ActorContext, owner_type: str) -> None:
        """
        Check if actor can create forms for the given owner.

        Raises:
            PermissionDenied: If not authorized
        """
        if not actor_context.has_permission("can_create_form"):
            raise PermissionDenied(
                message="You do not have permission to create forms",
                action="create",
                resource="FormTemplate",
            )

    @staticmethod
    def can_edit_form(*, actor_context: ActorContext, form_template: FormTemplate) -> None:
        """
        Check if actor can edit a form template.

        Rules:
        - System forms cannot be edited by anyone
        - Requires can_edit_form permission
        """
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be edited",
                action="edit",
                resource="FormTemplate",
            )

        if not actor_context.has_permission("can_edit_form"):
            raise PermissionDenied(
                message="You do not have permission to edit forms",
                action="edit",
                resource="FormTemplate",
            )

    @staticmethod
    def can_delete_form(*, actor_context: ActorContext, form_template: FormTemplate) -> None:
        """Check if actor can delete a form template."""
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be deleted",
                action="delete",
                resource="FormTemplate",
            )

        if not actor_context.has_permission("can_delete_form"):
            raise PermissionDenied(
                message="You do not have permission to delete forms",
                action="delete",
                resource="FormTemplate",
            )

    @staticmethod
    def can_view_form(*, actor_context: ActorContext, form_template: FormTemplate) -> None:
        """
        Check if actor can view a form template.

        Rules:
        - Public templates: anyone can view schema
        - Private templates: membership check already handled by FormViewMixin
        """
        if form_template.is_template_public:
            return  # Public templates viewable by all authenticated users

        # Membership check already enforced by FormViewMixin.get_membership_or_403()
        # in the view layer. If we reach here, actor is a member.


class FormResponsePolicy:
    """Authorization policies for form response operations."""

    @staticmethod
    def can_view_responses(*, actor_context: ActorContext, form_template: FormTemplate) -> None:
        """Check if actor can view responses for a form."""
        if not actor_context.has_permission("can_view_responses"):
            raise PermissionDenied(
                message="You do not have permission to view responses",
                action="view",
                resource="FormResponse",
            )

    @staticmethod
    def can_view_own_response(*, user, response: FormResponse) -> None:
        """Check if user can view their own response."""
        if response.submitted_by_id != user.id:
            raise PermissionDenied(
                message="You can only view your own responses",
                action="view",
                resource="FormResponse",
            )

    @staticmethod
    def can_edit_response(*, user, response: FormResponse) -> None:
        """
        Check if actor can edit a response.

        Rules:
        - Only submitter can edit their own response
        - Only editable in draft or submitted status
        """
        if response.submitted_by_id != user.id:
            raise PermissionDenied(
                message="You can only edit your own responses",
                action="edit",
                resource="FormResponse",
            )

        if not response.is_editable:
            raise PermissionDenied(
                message="This response cannot be edited",
                action="edit",
                resource="FormResponse",
            )

    @staticmethod
    def can_process_response(*, actor_context: ActorContext, response: FormResponse) -> None:
        """Check if actor can process a response."""
        if not actor_context.has_permission("can_process_response"):
            raise PermissionDenied(
                message="You do not have permission to process responses",
                action="process",
                resource="FormResponse",
            )

    @staticmethod
    def can_export_responses(*, actor_context: ActorContext, form_template: FormTemplate) -> None:
        """Check if actor can export responses."""
        if not actor_context.has_permission("can_export_responses"):
            raise PermissionDenied(
                message="You do not have permission to export responses",
                action="export",
                resource="FormResponse",
            )
```

---

## 13. Integration Stubs

### 13.1 Transaction System Integration

```python
# STUB: Integration with Transaction System
# This will be implemented by Transaction System
# Reference: Transaction Plan Section X.X
#
# Transaction templates can require form responses:
#
# class TransactionTypeConfig:
#     required_form_template_id: Optional[UUID]  # Form MUST be filled
#     optional_form_template_id: Optional[UUID]  # Form CAN be filled
#
# When creating transaction:
# 1. Check if transaction type requires form
# 2. Validate form_response_id in payload
# 3. Verify response is submitted and matches required form
#
# Example: business_verification_request
# - required_form_template_id = UUID of Business Verification Form
# - Transaction cannot be created without valid form_response_id

def validate_transaction_form_requirement(
    transaction_type: str,
    form_response_id: Optional[UUID]
) -> None:
    """
    STUB: Validate form requirement for transaction.
    
    Called by Transaction System when creating transactions.
    """
    # TODO: Implement via TransactionTypeConfig lookup
    # If required_form_template_id is set:
    #   - form_response_id must be provided
    #   - Response must exist and be submitted
    #   - Response must be for the required form template
    pass
```

### 13.2 RBAC System Integration

```python
# IMPLEMENTED: Integration with RBAC System
# Reference: apps/rbac/services.py, apps/core/types.py
#
# ActorContext construction (in views via FormViewMixin):
#   membership = MembershipSelector.get_active_membership_for_user_account(
#       user=request.user,
#       account_type=account_type,
#       account_id=account_id,
#   )
#   actor_context = RBACService.build_actor_context(
#       membership=membership,
#       request=request,
#   )
#
# Permission checking (in policies):
#   actor_context.has_permission("can_create_form")           # any scope
#   actor_context.has_global_permission("can_edit_form")      # global_only scope
#   actor_context.has_permission_with_scope("can_edit_form", "business")  # specific scope
```

### 13.3 Organization System Integration

```python
# STUB: Integration with Organization System
# Reference: Organization Plan
#
# Form owner validation:
# - owner_type='platform' -> owner_id must be valid PlatformAccount.id
# - owner_type='business' -> owner_id must be valid BusinessAccount.id
# - owner_type='system' -> owner_id must be None
#
# Example validation:
# if owner_type == OwnerType.BUSINESS:
#     from apps.organization.selectors import BusinessAccountSelector
#     BusinessAccountSelector.get_by_id(business_id=owner_id)  # Raises NotFound
```

---

## 14. Testing Strategy

### 14.1 Test Structure

```
backend/apps/forms/tests/
    __init__.py
    conftest.py         # Fixtures
    factories.py        # Factories
    test_models.py      # Model tests
    test_selectors.py   # Selector tests
    test_services.py    # Service tests
    test_policies.py    # Policy tests
    test_views.py       # API tests
    test_indexing.py    # Index extraction tests
```

### 14.2 Factories (`apps/forms/tests/factories.py`)

```python
import uuid
import factory
from django.utils import timezone
from apps.forms.models import FormTemplate, FormField, FormResponse
from apps.core.constants import FormStatus, ResponseStatus, FieldType, OwnerType, FormScope


def _make_actor_context():
    """Produce a realistic 12-key ActorContext dict matching ActorContext.to_dict()."""
    return {
        "user_id": str(uuid.uuid4()),
        "account_type": "business",
        "account_id": str(uuid.uuid4()),
        "membership_id": str(uuid.uuid4()),
        "role_id": str(uuid.uuid4()),
        "role_name": "member",
        "role_level": 50,
        "is_owner": False,
        "permissions_snapshot": [],
        "captured_at": timezone.now().isoformat(),
        "ip_address": "127.0.0.1",
        "user_agent": "test",
    }


class FormTemplateFactory(factory.django.DjangoModelFactory):
    """Factory for FormTemplate."""

    class Meta:
        model = FormTemplate

    name = factory.Sequence(lambda n: f"Form {n}")
    slug = factory.Sequence(lambda n: f"form-{n}")
    description = factory.Faker("paragraph")
    owner_type = OwnerType.BUSINESS
    owner_id = factory.LazyFunction(uuid.uuid4)
    scope = FormScope.BUSINESS
    creator_context = factory.LazyFunction(_make_actor_context)
    status = FormStatus.DRAFT
    version = 1
    is_current = True


class FormFieldFactory(factory.django.DjangoModelFactory):
    """Factory for FormField."""

    class Meta:
        model = FormField

    form_template = factory.SubFactory(FormTemplateFactory)
    field_key = factory.Sequence(lambda n: f"field_{n}")
    field_type = FieldType.TEXT
    label = factory.Sequence(lambda n: f"Field {n}")
    order = factory.Sequence(lambda n: n)
    is_required = False
    is_indexed = False


class FormResponseFactory(factory.django.DjangoModelFactory):
    """Factory for FormResponse."""

    class Meta:
        model = FormResponse

    form_template = factory.SubFactory(FormTemplateFactory)
    form_version = 1
    submitted_by = factory.SubFactory("apps.users.tests.factories.UserFactory")
    submitter_context = factory.LazyFunction(_make_actor_context)
    data = factory.LazyFunction(lambda: {"field_1": "value"})
    status = ResponseStatus.DRAFT
```

### 14.3 Key Test Cases

```python
# test_services.py

@pytest.mark.django_db
class TestFormBuilderService:
    
    def test_create_form_template(self, actor_context, membership, request_mock):
        """Can create a form template."""
        form = FormBuilderService.create_form_template(
            actor_context=actor_context,
            actor=membership.user,
            request=request_mock,
            name="Test Form",
            owner_type=OwnerType.BUSINESS,
            owner_id=membership.account_id,
            scope=FormScope.BUSINESS,
        )

        assert form.name == "Test Form"
        assert form.status == FormStatus.DRAFT
        assert form.creator_context is not None
        assert form.created_by == membership.user

    def test_cannot_create_system_form_via_service(self, actor_context, membership, request_mock):
        """System forms cannot be created via service."""
        with pytest.raises(ValidationError) as exc:
            FormBuilderService.create_form_template(
                actor_context=actor_context,
                actor=membership.user,
                request=request_mock,
                name="System Form",
                owner_type=OwnerType.SYSTEM,
                owner_id=None,
                scope=FormScope.BUSINESS,
            )
        assert "System forms" in str(exc.value)
    
    def test_edit_active_form_creates_new_version(self, active_form, user, request_mock):
        """Editing active form creates new version."""
        old_version = active_form.version
        
        updated = FormBuilderService.update_form_template(
            form_template=active_form,
            updated_by=user,
            request=request_mock,
            name="Updated Name",
        )
        
        assert updated.version == old_version + 1
        assert updated.is_current is True
        
        active_form.refresh_from_db()
        assert active_form.is_current is False
    
    def test_max_indexed_fields_enforced(self, draft_form, user, request_mock):
        """Cannot have more than 5 indexed fields."""
        # Add 5 indexed fields
        for i in range(5):
            FormBuilderService.add_field(
                form_template=draft_form,
                added_by=user,
                request=request_mock,
                field_key=f"indexed_{i}",
                field_type=FieldType.TEXT,
                label=f"Indexed {i}",
                order=i,
                is_indexed=True,
            )
        
        # 6th should fail
        with pytest.raises(ValidationError) as exc:
            FormBuilderService.add_field(
                form_template=draft_form,
                added_by=user,
                request=request_mock,
                field_key="indexed_6",
                field_type=FieldType.TEXT,
                label="Indexed 6",
                order=6,
                is_indexed=True,
            )
        assert "Maximum 5" in str(exc.value)


@pytest.mark.django_db
class TestFormResponseService:
    
    def test_submit_response_captures_context(self, draft_response, actor_context, membership, request_mock):
        """Submitting captures fresh submitter context."""
        response = FormResponseService.submit_response(
            response=draft_response,
            actor_context=actor_context,
            actor=membership.user,
            request=request_mock,
        )

        assert response.status == ResponseStatus.SUBMITTED
        assert response.submitted_at is not None
        assert response.submitter_context["user_id"] == str(membership.user_id)

    def test_submit_validates_required_fields(self, draft_response_missing_required, actor_context, membership, request_mock):
        """Submit fails if required fields missing."""
        with pytest.raises(ValidationError) as exc:
            FormResponseService.submit_response(
                response=draft_response_missing_required,
                actor_context=actor_context,
                actor=membership.user,
                request=request_mock,
            )
        assert "Required fields" in str(exc.value)
    
    def test_cannot_edit_processed_response(self, processed_response, user, request_mock):
        """Processed responses cannot be edited."""
        with pytest.raises(BusinessRuleViolation):
            FormResponseService.update_response(
                response=processed_response,
                updated_by=user,
                request=request_mock,
                data={"new": "data"},
            )
```

### 14.4 Coverage Requirements

- Minimum 80% coverage
- All service methods must have tests
- All policy checks must have tests
- Index extraction must have tests for each storage type
- Version creation must have tests

---

## Appendix: Migration Notes

### A.1 Migration Order

1. Add enums to `apps/core/constants.py`
2. Add AuditLog actions to `apps/core/observability/audit/models.py`
3. Create `apps/forms` app with models
4. Run `makemigrations forms`
5. Run `migrate`
6. Create data migration for system forms (if any)

### A.2 System Form Seeding

System forms should be created via data migration:

```python
# apps/forms/migrations/000X_seed_system_forms.py

def seed_system_forms(apps, schema_editor):
    FormTemplate = apps.get_model('forms', 'FormTemplate')
    FormField = apps.get_model('forms', 'FormField')
    
    # Business Verification Form (required by Transaction System)
    verification_form = FormTemplate.objects.create(
        id=uuid.UUID('...'),  # Fixed UUID for reference
        name="Business Verification",
        slug="business-verification",
        owner_type="system",
        owner_id=None,
        scope="business",
        creator_context={"role_name": "SYSTEM", "captured_at": "..."},
        status="active",
        version=1,
        is_current=True,
    )
    
    # Add fields...
```

### A.3 Foreign Key Considerations

- `FormResponse.form_template` uses `PROTECT` to prevent deletion of forms with responses
- `FormResponse.submitted_by` uses `PROTECT` to preserve audit trail
- `FormTemplate.parent_version` uses `SET_NULL` for version chain integrity
- `FormTemplate.forked_from` uses `SET_NULL` for fork reference integrity

---

### Critical Files for Implementation

- `backend/apps/core/constants.py` - Add FormStatus, ResponseStatus, FieldType, StorageType enums
- `backend/apps/core/observability/audit/models.py` - Add forms.* audit actions
- `backend/apps/core/models/base.py` - Reference for UUIDModel, AuditModel patterns
- `backend/apps/core/types.py` - Reference for ActorContext usage
- `backend/apps/rbac/services.py` - Reference for RBACService.build_actor_context()
- `backend/apps/rbac/selectors.py` - Reference for MembershipSelector.get_active_membership_for_user_account()
- `backend/apps/transaction/policies.py` - Reference for policy pattern (ActorContext.has_permission)

---

*End of Implementation Plan*