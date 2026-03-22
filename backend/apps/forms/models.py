"""
Form Builder Models
===================
FormTemplate, FormField, FormResponse, and Index Tables.
"""

from django.conf import settings
from django.db import models

from apps.core.constants import (
    FieldType,
    FormScope,
    FormStatus,
    OwnerType,
    ResponseStatus,
)
from apps.core.models import AuditModel, UUIDModel
from apps.forms.managers import FormResponseManager, FormTemplateManager


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
    description = models.TextField(
        blank=True,
        default="",
        help_text="Form description",
    )

    # Ownership (who owns this form)
    owner_type = models.CharField(
        max_length=20,
        choices=OwnerType.choices,
        db_index=True,
        help_text="Who owns this form template",
    )
    owner_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="UUID of owner account (null for system forms)",
    )

    # Scope (where this form can be used)
    scope = models.CharField(
        max_length=20,
        choices=FormScope.choices,
        db_index=True,
        help_text="Where this form can be used",
    )

    # Creator context (captured at creation time)
    creator_context = models.JSONField(
        help_text="ActorContext snapshot at creation time",
    )

    # Status and versioning
    status = models.CharField(
        max_length=20,
        choices=FormStatus.choices,
        default=FormStatus.DRAFT,
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(
        default=True,
        db_index=True,
        help_text="True if this is the current version",
    )
    parent_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_versions",
        help_text="Previous version this was created from",
    )

    # Template library
    is_template_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text="If true, visible in public template library",
    )
    forked_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="forks",
        help_text="Template this was forked from",
    )

    # Settings
    settings = models.JSONField(
        default=dict,
        blank=True,
        help_text="Form-level settings (expiry, notifications, etc.)",
    )

    # Managers
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
                condition=models.Q(is_deleted=False),
                name="unique_form_slug_per_owner_version",
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
        return self.owner_type == OwnerType.SYSTEM

    @property
    def is_editable(self) -> bool:
        if self.is_system_form:
            return False
        return self.status in [FormStatus.DRAFT, FormStatus.ACTIVE]

    @property
    def accepts_responses(self) -> bool:
        return self.status == FormStatus.ACTIVE and self.is_current


class FormField(UUIDModel):
    """
    Field definition within a form template.

    INVARIANT: field_key must be unique within a form template.
    INVARIANT: Only indexable storage types can have is_indexed=True.
    """

    form_template = models.ForeignKey(
        FormTemplate,
        on_delete=models.CASCADE,
        related_name="fields",
    )

    # Identity
    field_key = models.CharField(
        max_length=100,
        help_text="Machine-readable field identifier",
    )
    field_type = models.CharField(
        max_length=50,
        choices=FieldType.choices,
        help_text="Field type determining input and validation",
    )

    # Display
    label = models.CharField(max_length=255, help_text="Field label")
    description = models.TextField(
        blank=True,
        default="",
        help_text="Help text for the field",
    )
    placeholder = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Placeholder text",
    )

    # Structure
    order = models.PositiveIntegerField(
        help_text="Display order (lower first)",
    )
    step_tag = models.CharField(
        max_length=50,
        blank=True,
        default="",
        db_index=True,
        help_text="Groups fields into wizard steps",
    )
    section_tag = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Visual grouping within a step",
    )

    # Configuration
    options = models.JSONField(
        default=list,
        blank=True,
        help_text="Options for select, radio, etc.",
    )
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Validation rules (min_length, max_value, etc.)",
    )
    ui_config = models.JSONField(
        default=dict,
        blank=True,
        help_text="UI configuration (width, layout_hint)",
    )
    default_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Default value or dynamic token",
    )

    # Behavior flags
    is_required = models.BooleanField(
        default=False,
        help_text="Field must have a value",
    )
    is_indexed = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Value goes to typed index table (max 5 per form)",
    )
    is_hidden = models.BooleanField(
        default=False,
        help_text="System/internal field, not shown in UI",
    )
    is_readonly = models.BooleanField(
        default=False,
        help_text="Displayed but not editable",
    )

    class Meta:
        db_table = "form_field"
        verbose_name = "Form Field"
        verbose_name_plural = "Form Fields"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["form_template", "field_key"],
                name="unique_field_key_per_form",
            ),
        ]
        indexes = [
            models.Index(fields=["form_template", "order"]),
            models.Index(fields=["form_template", "step_tag"]),
            models.Index(fields=["form_template", "is_indexed"]),
        ]

    def __str__(self):
        return self.field_key


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
        related_name="responses",
    )
    form_version = models.PositiveIntegerField(
        help_text="Form version at submission time",
    )

    # Submitter
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="form_responses",
    )
    submitter_context = models.JSONField(
        help_text="ActorContext snapshot at submission time",
    )

    # Data
    data = models.JSONField(
        help_text="Complete response data as JSON",
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=ResponseStatus.choices,
        default=ResponseStatus.DRAFT,
        db_index=True,
    )
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When response was submitted",
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When response was processed",
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="processed_form_responses",
    )

    # Processing notes
    processor_notes = models.TextField(
        blank=True,
        default="",
        help_text="Notes from processor",
    )

    # Transaction integration
    transaction_id = models.UUIDField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Linked transaction UUID",
    )
    context_type = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Context type: platform, business, or user",
    )
    context_id = models.UUIDField(
        null=True,
        blank=True,
        help_text="Context account UUID",
    )

    # Revision tracking (for info-requested updates)
    revision = models.PositiveIntegerField(default=1)
    revision_history = models.JSONField(
        default=list,
        help_text="Previous revision snapshots",
    )
    info_requested_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When additional info was last requested",
    )

    # Managers
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
            models.Index(fields=["transaction_id"]),
        ]

    def __str__(self):
        return f"Response {self.id} ({self.status})"

    @property
    def is_editable(self) -> bool:
        return self.status in [ResponseStatus.DRAFT, ResponseStatus.SUBMITTED]


# =============================================================================
# INDEX TABLES
# =============================================================================


class BaseFieldIndex(UUIDModel):
    """Abstract base for typed field index tables."""

    response = models.ForeignKey(
        FormResponse,
        on_delete=models.CASCADE,
        related_name="%(class)s_indexes",
    )
    field_key = models.CharField(
        max_length=100,
        db_index=True,
        help_text="The field key this value is for",
    )

    class Meta:
        abstract = True


class TextFieldIndex(BaseFieldIndex):
    value = models.TextField(help_text="Indexed text value")

    class Meta:
        db_table = "form_text_field_index"
        verbose_name = "text field index"
        verbose_name_plural = "text field indexes"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class IntegerFieldIndex(BaseFieldIndex):
    value = models.BigIntegerField(help_text="Indexed integer value")

    class Meta:
        db_table = "form_integer_field_index"
        verbose_name = "integer field index"
        verbose_name_plural = "integer field indexes"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class DecimalFieldIndex(BaseFieldIndex):
    value = models.DecimalField(
        max_digits=19,
        decimal_places=4,
        help_text="Indexed decimal value",
    )

    class Meta:
        db_table = "form_decimal_field_index"
        verbose_name = "decimal field index"
        verbose_name_plural = "decimal field indexes"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class BooleanFieldIndex(BaseFieldIndex):
    value = models.BooleanField(help_text="Indexed boolean value")

    class Meta:
        db_table = "form_boolean_field_index"
        verbose_name = "boolean field index"
        verbose_name_plural = "boolean field indexes"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class DateFieldIndex(BaseFieldIndex):
    value = models.DateField(help_text="Indexed date value")

    class Meta:
        db_table = "form_date_field_index"
        verbose_name = "date field index"
        verbose_name_plural = "date field indexes"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]


class DateTimeFieldIndex(BaseFieldIndex):
    value = models.DateTimeField(help_text="Indexed datetime value")

    class Meta:
        db_table = "form_datetime_field_index"
        verbose_name = "datetime field index"
        verbose_name_plural = "datetime field indexes"
        indexes = [
            models.Index(fields=["response", "field_key"]),
            models.Index(fields=["field_key", "value"]),
        ]
