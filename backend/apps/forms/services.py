"""
Form Builder Service — template management and response lifecycle.

Provides two service classes:
    FormBuilderService — template CRUD, versioning, field management, publishing
    FormResponseService — response creation, submission, processing, voiding

Key template operations:
    create_form_template — create a new form template with owner context
    update_form_template — update template metadata (draft only)
    publish_form — transition draft/edit-draft to published
    archive_form / unarchive_form — lifecycle management
    create_edit_draft — create a new draft version from published template
    fork_template — clone a template for a different owner
    add_field / update_field / delete_field / reorder_fields — field management

Key response operations:
    create_response — create a draft response for a published template
    submit_response — validate and submit a draft response
    process_response / void_response — admin lifecycle actions
    create_and_submit — atomic create + validate + submit in one call
    link_to_transaction — associate a response with a transaction
    mark_info_requested / update_after_info_request — info-request workflow

All methods use @staticmethod + @transaction.atomic with keyword-only args.
Field values are validated against template schema and indexed for typed queries.
"""
from typing import Any, Dict, List
from uuid import UUID

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from django.utils.text import slugify

from apps.core.constants import FormStatus, OwnerType, ResponseStatus
from apps.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    PermissionDenied,
    ValidationError,
)
from apps.core.observability import AuditLog, AuditService, get_logger
from apps.core.types import ActorContext
from apps.forms.constants import (
    FIELD_STORAGE_MAP,
    INDEXABLE_STORAGE_TYPES,
    MAX_INDEXED_FIELDS,
)
from apps.forms.indexing import IndexService
from apps.forms.models import FormField, FormResponse, FormTemplate
from apps.forms.selectors import FormResponseSelector, FormTemplateSelector
from apps.forms.validators import validate_field_values

logger = get_logger(__name__)


class FormBuilderService:
    """Service for form template creation and management."""

    @staticmethod
    @transaction.atomic
    def create_form_template(
        *,
        actor_context: "ActorContext",
        actor,
        request: HttpRequest | None = None,
        name: str,
        slug: str | None = None,
        description: str = "",
        owner_type: str,
        owner_id: UUID | None = None,
        scope: str,
        settings: Dict | None = None,
    ) -> FormTemplate:
        if owner_type == OwnerType.SYSTEM:
            raise ValidationError(
                message="System forms can only be created via migration",
                field="owner_type",
            )

        if not slug:
            slug = slugify(name)[:100]

        if FormTemplate.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            slug=slug,
            is_current=True,
        ).exists():
            raise ConflictError(
                message=f"Form with slug '{slug}' already exists",
                resource="FormTemplate",
                conflict_type="duplicate",
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
            details={"owner_type": owner_type, "scope": scope},
        )

        return form

    @staticmethod
    @transaction.atomic
    def update_form_template(
        *,
        form_template: FormTemplate,
        updated_by,
        request: HttpRequest | None = None,
        name: str | None = None,
        description: str | None = None,
        settings: Dict | None = None,
    ) -> FormTemplate:
        if not form_template.is_editable:
            raise BusinessRuleViolation(
                message="This form cannot be edited",
                rule="form_immutability",
            )

        if form_template.status == FormStatus.ACTIVE:
            return FormBuilderService._create_new_version(
                form_template=form_template,
                updated_by=updated_by,
                request=request,
                name=name,
                description=description,
                settings=settings,
            )

        changes = {}
        if name is not None and form_template.name != name:
            changes["name"] = {"old": form_template.name, "new": name}
            form_template.name = name

        if description is not None and form_template.description != description:
            changes["description"] = {
                "old": form_template.description,
                "new": description,
            }
            form_template.description = description

        if settings is not None:
            changes["settings"] = {"old": form_template.settings, "new": settings}
            form_template.settings = settings

        if changes:
            form_template.updated_by = updated_by
            form_template.save(
                update_fields=list(changes.keys()) + ["updated_by", "updated_at"],
            )

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
        request: HttpRequest | None = None,
        name: str | None = None,
        description: str | None = None,
        settings: Dict | None = None,
    ) -> FormTemplate:
        form_template.is_current = False
        form_template.updated_by = updated_by
        form_template.save(update_fields=["is_current", "updated_by", "updated_at"])

        new_version = FormTemplate.objects.create(
            name=name if name is not None else form_template.name,
            slug=form_template.slug,
            description=(
                description if description is not None else form_template.description
            ),
            owner_type=form_template.owner_type,
            owner_id=form_template.owner_id,
            scope=form_template.scope,
            creator_context=form_template.creator_context,
            created_by=updated_by,
            status=FormStatus.ACTIVE,
            version=form_template.version + 1,
            is_current=True,
            parent_version=form_template,
            is_template_public=form_template.is_template_public,
            forked_from=form_template.forked_from,
            settings=settings if settings is not None else form_template.settings,
        )

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
            },
        )

        return new_version

    @staticmethod
    @transaction.atomic
    def publish_form(
        *,
        form_template: FormTemplate,
        published_by,
        request: HttpRequest | None = None,
    ) -> FormTemplate:
        if form_template.status != FormStatus.DRAFT:
            raise BusinessRuleViolation(
                message="Only draft forms can be published",
                rule="form_publish_from_draft",
            )

        form_template.status = FormStatus.ACTIVE
        form_template.updated_by = published_by
        form_template.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info("forms.template.published", form_id=str(form_template.id))

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
        request: HttpRequest | None = None,
    ) -> FormTemplate:
        if form_template.status != FormStatus.ACTIVE:
            raise BusinessRuleViolation(
                message="Only active forms can be archived",
                rule="form_archive_from_active",
            )

        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be archived",
                action="archive",
                resource="FormTemplate",
            )

        form_template.status = FormStatus.ARCHIVED
        form_template.updated_by = archived_by
        form_template.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info("forms.template.archived", form_id=str(form_template.id))

        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_ARCHIVED,
            actor=archived_by,
            resource=form_template,
            request=request,
        )

        return form_template

    @staticmethod
    @transaction.atomic
    def unarchive_form(
        *,
        form_template: FormTemplate,
        unarchived_by,
        request: HttpRequest | None = None,
    ) -> FormTemplate:
        if form_template.status != FormStatus.ARCHIVED:
            raise BusinessRuleViolation(
                message="Only archived forms can be restored",
                rule="form_unarchive_from_archived",
            )

        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be modified",
                action="unarchive",
                resource="FormTemplate",
            )

        form_template.status = FormStatus.DRAFT
        form_template.updated_by = unarchived_by
        form_template.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info("forms.template.unarchived", form_id=str(form_template.id))

        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_UPDATED,
            actor=unarchived_by,
            resource=form_template,
            request=request,
            details={"action": "unarchive", "new_status": "draft"},
        )

        return form_template

    @staticmethod
    @transaction.atomic
    def create_edit_draft(
        *,
        form_template: FormTemplate,
        created_by,
        request: HttpRequest | None = None,
    ) -> FormTemplate:
        """Create a new DRAFT version from an active form for editing."""
        if form_template.status != FormStatus.ACTIVE:
            raise BusinessRuleViolation(
                message="Only active forms can create an edit draft",
                rule="form_edit_draft_from_active",
            )

        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be edited",
                action="create_edit_draft",
                resource="FormTemplate",
            )

        # Mark old version as not current
        form_template.is_current = False
        form_template.updated_by = created_by
        form_template.save(update_fields=["is_current", "updated_by", "updated_at"])

        new_draft = FormTemplate.objects.create(
            name=form_template.name,
            slug=form_template.slug,
            description=form_template.description,
            owner_type=form_template.owner_type,
            owner_id=form_template.owner_id,
            scope=form_template.scope,
            creator_context=form_template.creator_context,
            created_by=created_by,
            status=FormStatus.DRAFT,
            version=form_template.version + 1,
            is_current=True,
            parent_version=form_template,
            is_template_public=form_template.is_template_public,
            forked_from=form_template.forked_from,
            settings=form_template.settings.copy() if form_template.settings else {},
        )

        for field in form_template.fields.all():
            FormField.objects.create(
                form_template=new_draft,
                field_key=field.field_key,
                field_type=field.field_type,
                label=field.label,
                description=field.description,
                placeholder=field.placeholder,
                order=field.order,
                step_tag=field.step_tag,
                section_tag=field.section_tag,
                options=field.options.copy() if field.options else [],
                validation_rules=(
                    field.validation_rules.copy() if field.validation_rules else {}
                ),
                ui_config=field.ui_config.copy() if field.ui_config else {},
                default_value=field.default_value,
                is_required=field.is_required,
                is_indexed=field.is_indexed,
                is_hidden=field.is_hidden,
                is_readonly=field.is_readonly,
            )

        logger.info(
            "forms.template.edit_draft_created",
            form_id=str(new_draft.id),
            parent_id=str(form_template.id),
            new_version=new_draft.version,
        )

        AuditService.log(
            action=AuditLog.Action.FORM_TEMPLATE_VERSIONED,
            actor=created_by,
            resource=new_draft,
            request=request,
            details={
                "action": "create_edit_draft",
                "parent_id": str(form_template.id),
                "old_version": form_template.version,
                "new_version": new_draft.version,
            },
        )

        return new_draft

    @staticmethod
    @transaction.atomic
    def delete_form(
        *,
        form_template: FormTemplate,
        deleted_by,
        request: HttpRequest | None = None,
    ) -> FormTemplate:
        if form_template.is_system_form:
            raise PermissionDenied(
                message="System forms cannot be deleted",
                action="delete",
                resource="FormTemplate",
            )

        form_template.status = FormStatus.DELETED
        form_template.save(update_fields=["status", "updated_at"])
        form_template.soft_delete(user=deleted_by)

        logger.info("forms.template.deleted", form_id=str(form_template.id))

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
        request: HttpRequest | None = None,
        new_owner_type: str,
        new_owner_id: UUID,
        new_name: str | None = None,
        new_slug: str | None = None,
    ) -> FormTemplate:
        if not source_template.is_template_public:
            raise PermissionDenied(
                message="Only public templates can be forked",
                action="fork",
                resource="FormTemplate",
            )

        name = new_name or f"{source_template.name} (Copy)"
        slug = new_slug or slugify(name)[:100]

        counter = 1
        original_slug = slug
        while FormTemplate.objects.filter(
            owner_type=new_owner_type,
            owner_id=new_owner_id,
            slug=slug,
            is_current=True,
        ).exists():
            slug = f"{original_slug}-{counter}"
            counter += 1

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
            settings=(
                source_template.settings.copy() if source_template.settings else {}
            ),
        )

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
                validation_rules=(
                    field.validation_rules.copy() if field.validation_rules else {}
                ),
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
            },
        )

        return forked

    @staticmethod
    @transaction.atomic
    def add_field(
        *,
        form_template: FormTemplate,
        added_by,
        request: HttpRequest | None = None,
        field_key: str,
        field_type: str,
        label: str,
        order: int,
        description: str = "",
        placeholder: str = "",
        step_tag: str = "",
        section_tag: str = "",
        options: List | None = None,
        validation_rules: Dict | None = None,
        ui_config: Dict | None = None,
        default_value: Any = None,
        is_required: bool = False,
        is_indexed: bool = False,
        is_hidden: bool = False,
        is_readonly: bool = False,
    ) -> FormField:
        if not form_template.is_editable:
            raise BusinessRuleViolation(
                message="Cannot add fields to non-editable form",
                rule="form_immutability",
            )

        if FormField.objects.filter(
            form_template=form_template,
            field_key=field_key,
        ).exists():
            raise ConflictError(
                message=f"Field key '{field_key}' already exists",
                resource="FormField",
                conflict_type="duplicate",
            )

        if is_indexed:
            storage_type = FIELD_STORAGE_MAP.get(field_type)
            if storage_type not in INDEXABLE_STORAGE_TYPES:
                raise ValidationError(
                    message=f"Field type '{field_type}' cannot be indexed",
                    field="is_indexed",
                )

            indexed_count = FormTemplateSelector.count_indexed_fields(
                form_template_id=form_template.id,
            )
            if indexed_count >= MAX_INDEXED_FIELDS:
                raise ValidationError(
                    message=f"Maximum {MAX_INDEXED_FIELDS} indexed fields allowed",
                    field="is_indexed",
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
            },
        )

        return field

    @staticmethod
    @transaction.atomic
    def update_field(
        *,
        field: FormField,
        updated_by,
        request: HttpRequest | None = None,
        data: Dict[str, Any],
    ) -> FormField:
        """Update a form field's properties.

        Only the keys present in `data` are updated. The form template must
        be in DRAFT status.
        """
        form_template = field.form_template
        if not form_template.is_editable:
            raise BusinessRuleViolation(
                message="Cannot update fields on a non-editable form",
                rule="form_immutability",
            )

        if form_template.status != FormStatus.DRAFT:
            raise BusinessRuleViolation(
                message="Fields can only be modified on draft forms",
                rule="form_field_draft_only",
            )

        UPDATABLE_FIELDS = {
            "label",
            "help_text",
            "placeholder",
            "options",
            "validation_rules",
            "is_required",
            "is_indexable",
            "section_tag",
            "step_tag",
            "conditional_logic",
        }

        # Map API field names to model field names where they differ
        FIELD_NAME_MAP = {
            "help_text": "description",
            "is_indexable": "is_indexed",
            "conditional_logic": "ui_config",
        }

        changes = {}
        update_fields = []
        for api_name, value in data.items():
            if api_name not in UPDATABLE_FIELDS:
                continue
            model_field = FIELD_NAME_MAP.get(api_name, api_name)
            old_value = getattr(field, model_field)
            if old_value != value:
                changes[model_field] = {"old": old_value, "new": value}
                setattr(field, model_field, value)
                update_fields.append(model_field)

        if update_fields:
            field.save(update_fields=update_fields)

            logger.info(
                "forms.field.updated",
                form_id=str(form_template.id),
                field_id=str(field.id),
                fields=list(changes.keys()),
            )

            AuditService.log(
                action=AuditLog.Action.FORM_FIELD_UPDATED,
                actor=updated_by,
                resource=field,
                request=request,
                changes=changes,
            )

        return field

    @staticmethod
    @transaction.atomic
    def delete_field(
        *,
        field: FormField,
        deleted_by,
        request: HttpRequest | None = None,
    ) -> None:
        """Delete a form field and reorder remaining fields to close the gap.

        The form template must be in DRAFT status.
        """
        form_template = field.form_template
        if not form_template.is_editable:
            raise BusinessRuleViolation(
                message="Cannot delete fields from a non-editable form",
                rule="form_immutability",
            )

        if form_template.status != FormStatus.DRAFT:
            raise BusinessRuleViolation(
                message="Fields can only be deleted from draft forms",
                rule="form_field_draft_only",
            )

        field_id = str(field.id)
        field_key = field.field_key
        deleted_order = field.order

        field.delete()

        # Reorder remaining fields to close the gap
        remaining = FormField.objects.filter(
            form_template=form_template,
            order__gt=deleted_order,
        ).order_by("order")
        for f in remaining:
            f.order = f.order - 1
            f.save(update_fields=["order"])

        logger.info(
            "forms.field.removed",
            form_id=str(form_template.id),
            field_id=field_id,
            field_key=field_key,
        )

        AuditService.log(
            action=AuditLog.Action.FORM_FIELD_REMOVED,
            actor=deleted_by,
            resource=form_template,
            request=request,
            details={
                "field_id": field_id,
                "field_key": field_key,
            },
        )

    @staticmethod
    @transaction.atomic
    def reorder_fields(
        *,
        form_template: FormTemplate,
        field_orders: List[Dict[str, Any]],
        reordered_by,
        request: HttpRequest | None = None,
    ) -> List[FormField]:
        """Bulk reorder fields within a form template.

        Accepts a list of {field_id, order} dicts.
        Uses a two-pass approach with high offset to avoid potential
        unique constraint violations on the order field.
        """
        if not form_template.is_editable:
            raise BusinessRuleViolation(
                message="Cannot reorder fields on a non-editable form",
                rule="form_immutability",
            )

        if form_template.status != FormStatus.DRAFT:
            raise BusinessRuleViolation(
                message="Fields can only be reordered on draft forms",
                rule="form_field_draft_only",
            )

        field_ids = [entry["field_id"] for entry in field_orders]
        fields = FormField.objects.filter(
            id__in=field_ids,
            form_template=form_template,
        )

        if fields.count() != len(field_ids):
            raise ValidationError(
                message="One or more field IDs do not belong to this template",
                field="fields",
            )

        order_map = {entry["field_id"]: entry["order"] for entry in field_orders}

        # Pass 1: offset all orders to high values to avoid collisions
        OFFSET = 100000
        for field in fields:
            field.order = OFFSET + field.order
            field.save(update_fields=["order"])

        # Pass 2: set actual desired orders
        fields = FormField.objects.filter(id__in=field_ids, form_template=form_template)
        for field in fields:
            field.order = order_map[field.id]
            field.save(update_fields=["order"])

        result = FormField.objects.filter(
            form_template=form_template,
        ).order_by("order")

        logger.info(
            "forms.fields.reordered",
            form_id=str(form_template.id),
            field_count=len(field_orders),
        )

        AuditService.log(
            action=AuditLog.Action.FORM_FIELD_UPDATED,
            actor=reordered_by,
            resource=form_template,
            request=request,
            details={"action": "reorder", "field_count": len(field_orders)},
        )

        return list(result)


class FormResponseService:
    """Service for form response submission and management."""

    @staticmethod
    @transaction.atomic
    def create_response(
        *,
        form_template: FormTemplate,
        actor_context: "ActorContext",
        actor,
        request: HttpRequest | None = None,
        data: Dict[str, Any],
    ) -> FormResponse:
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
        request: HttpRequest | None = None,
        data: Dict[str, Any],
    ) -> FormResponse:
        if not response.is_editable:
            raise BusinessRuleViolation(
                message="This response cannot be edited",
                rule="response_immutability",
            )

        response.data = data
        response.save(update_fields=["data", "updated_at"])

        logger.info("forms.response.updated", response_id=str(response.id))

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
        request: HttpRequest | None = None,
    ) -> FormResponse:
        if response.status != ResponseStatus.DRAFT:
            raise BusinessRuleViolation(
                message="Only draft responses can be submitted",
                rule="response_submit_from_draft",
            )

        all_fields = list(
            FormField.objects.filter(
                form_template=response.form_template,
            )
        )

        required_missing = [
            f.field_key
            for f in all_fields
            if f.is_required and not response.data.get(f.field_key)
        ]
        if required_missing:
            raise ValidationError(
                message=f"Required fields missing: {', '.join(required_missing)}",
                field="data",
            )

        type_errors = validate_field_values(all_fields, response.data)
        if type_errors:
            raise ValidationError(
                message=f"Field validation errors: {'; '.join(type_errors)}",
                field="data",
            )

        response.submitter_context = actor_context.to_dict()
        response.status = ResponseStatus.SUBMITTED
        response.submitted_at = timezone.now()
        response.save(
            update_fields=[
                "submitter_context",
                "status",
                "submitted_at",
                "updated_at",
            ]
        )

        IndexService.extract_and_store(response=response)

        logger.info(
            "forms.response.submitted",
            response_id=str(response.id),
            form_id=str(response.form_template_id),
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
        request: HttpRequest | None = None,
        notes: str = "",
    ) -> FormResponse:
        if response.status != ResponseStatus.SUBMITTED:
            raise BusinessRuleViolation(
                message="Only submitted responses can be processed",
                rule="response_process_from_submitted",
            )

        response.status = ResponseStatus.PROCESSED
        response.processed_at = timezone.now()
        response.processed_by = processed_by
        response.processor_notes = notes
        response.save(
            update_fields=[
                "status",
                "processed_at",
                "processed_by",
                "processor_notes",
                "updated_at",
            ]
        )

        logger.info("forms.response.processed", response_id=str(response.id))

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
        request: HttpRequest | None = None,
        reason: str = "",
    ) -> FormResponse:
        if response.status not in [ResponseStatus.DRAFT, ResponseStatus.SUBMITTED]:
            raise BusinessRuleViolation(
                message="Only draft or submitted responses can be voided",
                rule="response_void_allowed_states",
            )

        response.status = ResponseStatus.VOID
        response.save(update_fields=["status", "updated_at"])

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

    # =========================================================================
    # TRANSACTION INTEGRATION
    # =========================================================================

    @staticmethod
    @transaction.atomic
    def create_and_submit(
        *,
        form_template: FormTemplate,
        data: Dict[str, Any],
        context_type: str = "",
        context_id: UUID | None = None,
        actor_context: ActorContext,
        actor,
        request: HttpRequest | None = None,
    ) -> FormResponse:
        """Create a form response and immediately submit it (for transaction-linked forms)."""
        if not form_template.accepts_responses:
            raise BusinessRuleViolation(
                message="This form is not accepting responses",
                rule="form_accepts_responses",
            )

        all_fields = list(form_template.fields.all())

        required_missing = [
            f.field_key
            for f in all_fields
            if f.is_required and not data.get(f.field_key)
        ]
        if required_missing:
            raise ValidationError(
                message=f"Required fields missing: {', '.join(required_missing)}",
                field="data",
            )

        type_errors = validate_field_values(all_fields, data)
        if type_errors:
            raise ValidationError(
                message=f"Field validation errors: {'; '.join(type_errors)}",
                field="data",
            )

        response = FormResponse.objects.create(
            form_template=form_template,
            form_version=form_template.version,
            submitted_by=actor,
            submitter_context=actor_context.to_dict(),
            data=data,
            status=ResponseStatus.SUBMITTED,
            submitted_at=timezone.now(),
            context_type=context_type,
            context_id=context_id,
            revision=1,
            created_by=actor,
            updated_by=actor,
        )

        IndexService.extract_and_store(response=response)

        logger.info(
            "forms.response.created_and_submitted",
            response_id=str(response.id),
            form_id=str(form_template.id),
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
    def link_to_transaction(
        *,
        response_id: UUID,
        transaction_id: UUID,
    ) -> FormResponse:
        """Link a form response to a transaction (bidirectional)."""
        response = FormResponseSelector.get_by_id(response_id=response_id)

        if response.transaction_id and response.transaction_id != transaction_id:
            raise ConflictError(
                message="Form response is already linked to a different transaction",
                resource="FormResponse",
                conflict_type="already_linked",
            )

        response.transaction_id = transaction_id
        response.save(update_fields=["transaction_id", "updated_at"])

        return response

    @staticmethod
    @transaction.atomic
    def mark_info_requested(
        *,
        response_id: UUID,
        actor,
    ) -> FormResponse:
        """Mark a form response as having info requested."""
        response = FormResponseSelector.get_by_id(response_id=response_id)

        response.info_requested_at = timezone.now()
        response.updated_by = actor
        response.save(update_fields=["info_requested_at", "updated_at", "updated_by"])

        return response

    @staticmethod
    @transaction.atomic
    def update_after_info_request(
        *,
        response_id: UUID,
        data: Dict[str, Any],
        actor_context: ActorContext,
        actor,
        request: HttpRequest | None = None,
    ) -> FormResponse:
        """Update a form response after info was requested.

        Validates:
        - Linked transaction is in INFO_REQUESTED status
        - Actor is original submitter
        - Required fields present
        Then: saves revision history, updates data, re-extracts indexes.
        """
        from apps.transaction.constants import TransactionStatus
        from apps.transaction.selectors import TransactionSelector

        response = FormResponseSelector.get_by_id(response_id=response_id)

        if not response.transaction_id:
            raise ValidationError(
                message="Response is not linked to a transaction",
                field="transaction_id",
            )

        txn = TransactionSelector.get_by_id(
            transaction_id=response.transaction_id,
        )
        if txn.status != TransactionStatus.INFO_REQUESTED:
            raise ValidationError(
                message="Can only update response when transaction is in INFO_REQUESTED status",
                field="status",
            )

        if response.submitted_by_id != actor.id:
            raise PermissionDenied(
                message="Only the original submitter can update the response",
                action="update",
                resource="FormResponse",
            )

        all_fields = list(response.form_template.fields.all())

        required_missing = [
            f.field_key
            for f in all_fields
            if f.is_required and not data.get(f.field_key)
        ]
        if required_missing:
            raise ValidationError(
                message=f"Required fields missing: {', '.join(required_missing)}",
                field="data",
            )

        type_errors = validate_field_values(all_fields, data)
        if type_errors:
            raise ValidationError(
                message=f"Field validation errors: {'; '.join(type_errors)}",
                field="data",
            )

        # Save current data to revision history
        history_entry = {
            "revision": response.revision,
            "data": response.data,
            "submitted_at": (
                response.submitted_at.isoformat() if response.submitted_at else None
            ),
            "submitted_by": str(response.submitted_by_id),
        }
        response.revision_history = response.revision_history + [history_entry]

        # Update response
        response.data = data
        response.revision += 1
        response.submitted_at = timezone.now()
        response.submitter_context = actor_context.to_dict()
        response.info_requested_at = None
        response.updated_by = actor
        response.save(
            update_fields=[
                "data",
                "revision",
                "revision_history",
                "submitted_at",
                "submitter_context",
                "info_requested_at",
                "updated_at",
                "updated_by",
            ]
        )

        # Re-extract indexed fields
        IndexService.clear_indexes(response=response)
        IndexService.extract_and_store(response=response)

        logger.info(
            "forms.response.updated_after_info_request",
            response_id=str(response.id),
            revision=response.revision,
        )

        AuditService.log(
            action=AuditLog.Action.FORM_RESPONSE_UPDATED,
            actor=actor,
            resource=response,
            request=request,
            details={"revision": response.revision},
        )

        return response
