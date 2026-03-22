# apps/forms/tests/test_services.py
"""
Comprehensive tests for Form Builder services.

Covers:
- FormBuilderService: create, update, publish, archive, delete, fork, add_field
- FormResponseService: create, update, submit, process, void
"""

import uuid

import pytest

from apps.core.constants import (
    AccountType,
    FieldType,
    FormScope,
    FormStatus,
    OwnerType,
    ResponseStatus,
)
from apps.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    PermissionDenied,
    ValidationError,
)
from apps.core.observability import AuditLog
from apps.core.types import ActorContext
from apps.forms.models import FormField, FormResponse, FormTemplate
from apps.forms.services import FormBuilderService, FormResponseService
from apps.forms.tests.factories import (
    ActiveFormTemplateFactory,
    ArchivedFormTemplateFactory,
    FormFieldFactory,
    FormResponseFactory,
    FormTemplateFactory,
    PublicFormTemplateFactory,
    SubmittedFormResponseFactory,
    SystemFormTemplateFactory,
)
from apps.users.tests.factories import UserFactory

# =============================================================================
# FormBuilderService — Create
# =============================================================================


@pytest.mark.django_db
class TestFormBuilderServiceCreate:
    """Tests for FormBuilderService.create_form_template."""

    def test_create_form_template(self, user, business):
        """Create with valid params produces correct form attributes."""
        actor_context = ActorContext.for_user_context(user, request=None)

        form = FormBuilderService.create_form_template(
            actor_context=actor_context,
            actor=user,
            name="Customer Intake",
            slug="customer-intake",
            description="Intake form for new customers",
            owner_type=OwnerType.BUSINESS,
            owner_id=business.id,
            scope=FormScope.BUSINESS,
        )

        assert form.name == "Customer Intake"
        assert form.slug == "customer-intake"
        assert form.description == "Intake form for new customers"
        assert form.owner_type == OwnerType.BUSINESS
        assert form.owner_id == business.id
        assert form.scope == FormScope.BUSINESS
        assert form.version == 1
        assert form.is_current is True
        assert form.status == FormStatus.DRAFT
        assert form.created_by == user

    def test_create_form_template_auto_slug(self, user, business):
        """When slug is not provided, it is auto-generated from the name."""
        actor_context = ActorContext.for_user_context(user, request=None)

        form = FormBuilderService.create_form_template(
            actor_context=actor_context,
            actor=user,
            name="My Special Form",
            owner_type=OwnerType.BUSINESS,
            owner_id=business.id,
            scope=FormScope.BUSINESS,
        )

        assert form.slug == "my-special-form"

    def test_create_form_template_system_blocked(self, user):
        """Creating a system form via the service raises ValidationError."""
        actor_context = ActorContext.for_user_context(user, request=None)

        with pytest.raises(ValidationError):
            FormBuilderService.create_form_template(
                actor_context=actor_context,
                actor=user,
                name="System Form",
                owner_type=OwnerType.SYSTEM,
                owner_id=None,
                scope=FormScope.PLATFORM,
            )

    def test_create_form_template_duplicate_slug(self, user, business):
        """Duplicate slug within the same owner raises ConflictError."""
        actor_context = ActorContext.for_user_context(user, request=None)

        FormBuilderService.create_form_template(
            actor_context=actor_context,
            actor=user,
            name="First Form",
            slug="shared-slug",
            owner_type=OwnerType.BUSINESS,
            owner_id=business.id,
            scope=FormScope.BUSINESS,
        )

        with pytest.raises(ConflictError):
            FormBuilderService.create_form_template(
                actor_context=actor_context,
                actor=user,
                name="Second Form",
                slug="shared-slug",
                owner_type=OwnerType.BUSINESS,
                owner_id=business.id,
                scope=FormScope.BUSINESS,
            )

    def test_create_form_template_creates_audit_log(self, user, business):
        """Creating a form produces an audit log entry."""
        actor_context = ActorContext.for_user_context(user, request=None)

        FormBuilderService.create_form_template(
            actor_context=actor_context,
            actor=user,
            name="Audited Form",
            owner_type=OwnerType.BUSINESS,
            owner_id=business.id,
            scope=FormScope.BUSINESS,
        )

        assert AuditLog.objects.filter(
            action=AuditLog.Action.FORM_TEMPLATE_CREATED,
        ).exists()


# =============================================================================
# FormBuilderService — Update
# =============================================================================


@pytest.mark.django_db
class TestFormBuilderServiceUpdate:
    """Tests for FormBuilderService.update_form_template."""

    def test_update_draft_in_place(self, draft_form, user):
        """Updating a draft form modifies it in-place (same ID)."""
        original_id = draft_form.id

        result = FormBuilderService.update_form_template(
            form_template=draft_form,
            updated_by=user,
            name="Updated Name",
        )

        assert result.id == original_id
        assert result.name == "Updated Name"

    def test_update_draft_no_changes(self, draft_form, user):
        """Updating with identical values makes no changes."""
        original_updated_at = draft_form.updated_at

        result = FormBuilderService.update_form_template(
            form_template=draft_form,
            updated_by=user,
            name=draft_form.name,
            description=draft_form.description,
        )

        result.refresh_from_db()
        assert result.updated_at == original_updated_at

    def test_update_active_creates_new_version(self, active_form, user):
        """Updating an active form creates a new version (different ID)."""
        old_id = active_form.id
        old_version = active_form.version

        result = FormBuilderService.update_form_template(
            form_template=active_form,
            updated_by=user,
            name="Updated Active Form",
        )

        assert result.id != old_id
        assert result.version == old_version + 1
        assert result.is_current is True
        assert result.name == "Updated Active Form"

        # Old version should no longer be current
        active_form.refresh_from_db()
        assert active_form.is_current is False

    def test_update_active_copies_fields(self, active_form, user):
        """New version created from active form copies all fields."""
        FormFieldFactory(
            form_template=active_form,
            field_key="first_name",
            field_type=FieldType.TEXT,
            label="First Name",
            order=1,
        )
        FormFieldFactory(
            form_template=active_form,
            field_key="email",
            field_type=FieldType.EMAIL,
            label="Email",
            order=2,
        )

        result = FormBuilderService.update_form_template(
            form_template=active_form,
            updated_by=user,
            name="Updated With Fields",
        )

        new_fields = result.fields.all().order_by("order")
        assert new_fields.count() == 2
        assert new_fields[0].field_key == "first_name"
        assert new_fields[1].field_key == "email"

    def test_update_non_editable_raises(self, user):
        """Updating an archived form raises BusinessRuleViolation."""
        archived_form = ArchivedFormTemplateFactory(created_by=user)

        with pytest.raises(BusinessRuleViolation):
            FormBuilderService.update_form_template(
                form_template=archived_form,
                updated_by=user,
                name="Should Fail",
            )

    def test_update_system_form_raises(self, user):
        """Updating a system form raises BusinessRuleViolation (is_editable=False)."""
        system_form = SystemFormTemplateFactory(
            status=FormStatus.ACTIVE,
            created_by=user,
        )

        with pytest.raises(BusinessRuleViolation):
            FormBuilderService.update_form_template(
                form_template=system_form,
                updated_by=user,
                name="Should Fail",
            )


# =============================================================================
# FormBuilderService — Publish
# =============================================================================


@pytest.mark.django_db
class TestFormBuilderServicePublish:
    """Tests for FormBuilderService.publish_form."""

    def test_publish_draft(self, draft_form, user):
        """Publishing a draft form transitions it to ACTIVE."""
        result = FormBuilderService.publish_form(
            form_template=draft_form,
            published_by=user,
        )

        assert result.status == FormStatus.ACTIVE

    def test_publish_non_draft_raises(self, active_form, user):
        """Publishing a non-draft form raises BusinessRuleViolation."""
        with pytest.raises(BusinessRuleViolation):
            FormBuilderService.publish_form(
                form_template=active_form,
                published_by=user,
            )

    def test_publish_creates_audit_log(self, draft_form, user):
        """Publishing creates an audit log entry."""
        FormBuilderService.publish_form(
            form_template=draft_form,
            published_by=user,
        )

        assert AuditLog.objects.filter(
            action=AuditLog.Action.FORM_TEMPLATE_PUBLISHED,
        ).exists()


# =============================================================================
# FormBuilderService — Archive
# =============================================================================


@pytest.mark.django_db
class TestFormBuilderServiceArchive:
    """Tests for FormBuilderService.archive_form."""

    def test_archive_active(self, active_form, user):
        """Archiving an active form transitions it to ARCHIVED."""
        result = FormBuilderService.archive_form(
            form_template=active_form,
            archived_by=user,
        )

        assert result.status == FormStatus.ARCHIVED

    def test_archive_non_active_raises(self, draft_form, user):
        """Archiving a non-active form raises BusinessRuleViolation."""
        with pytest.raises(BusinessRuleViolation):
            FormBuilderService.archive_form(
                form_template=draft_form,
                archived_by=user,
            )

    def test_archive_system_form_raises(self, user):
        """Archiving a system form raises PermissionDenied."""
        system_form = SystemFormTemplateFactory(
            status=FormStatus.ACTIVE,
            created_by=user,
        )

        with pytest.raises(PermissionDenied):
            FormBuilderService.archive_form(
                form_template=system_form,
                archived_by=user,
            )


# =============================================================================
# FormBuilderService — Delete
# =============================================================================


@pytest.mark.django_db
class TestFormBuilderServiceDelete:
    """Tests for FormBuilderService.delete_form."""

    def test_delete_form(self, draft_form, user):
        """Deleting a form sets status to DELETED and is_deleted=True."""
        result = FormBuilderService.delete_form(
            form_template=draft_form,
            deleted_by=user,
        )

        # In-memory object has status=DELETED
        assert result.status == FormStatus.DELETED

        # Verify soft-delete flag is persisted
        draft_form.refresh_from_db()
        assert draft_form.is_deleted is True

    def test_delete_system_form_raises(self, user):
        """Deleting a system form raises PermissionDenied."""
        system_form = SystemFormTemplateFactory(created_by=user)

        with pytest.raises(PermissionDenied):
            FormBuilderService.delete_form(
                form_template=system_form,
                deleted_by=user,
            )


# =============================================================================
# FormBuilderService — Fork
# =============================================================================


@pytest.mark.django_db
class TestFormBuilderServiceFork:
    """Tests for FormBuilderService.fork_template."""

    def test_fork_public_template(self, user, business):
        """Forking a public template copies it with fields."""
        source = PublicFormTemplateFactory(created_by=user)
        FormFieldFactory(
            form_template=source,
            field_key="name",
            field_type=FieldType.TEXT,
            label="Name",
            order=1,
        )
        FormFieldFactory(
            form_template=source,
            field_key="email",
            field_type=FieldType.EMAIL,
            label="Email",
            order=2,
        )

        actor_context = ActorContext.for_user_context(user, request=None)

        forked = FormBuilderService.fork_template(
            source_template=source,
            actor_context=actor_context,
            actor=user,
            new_owner_type=OwnerType.BUSINESS,
            new_owner_id=business.id,
        )

        assert forked.forked_from == source
        assert forked.version == 1
        assert forked.status == FormStatus.DRAFT
        assert forked.is_current is True
        assert forked.fields.count() == 2

        field_keys = list(forked.fields.values_list("field_key", flat=True))
        assert "name" in field_keys
        assert "email" in field_keys

    def test_fork_non_public_raises(self, user, business):
        """Forking a non-public template raises PermissionDenied."""
        source = ActiveFormTemplateFactory(
            is_template_public=False,
            created_by=user,
        )
        actor_context = ActorContext.for_user_context(user, request=None)

        with pytest.raises(PermissionDenied):
            FormBuilderService.fork_template(
                source_template=source,
                actor_context=actor_context,
                actor=user,
                new_owner_type=OwnerType.BUSINESS,
                new_owner_id=business.id,
            )

    def test_fork_system_form_succeeds(self, user, business):
        """Forking a public system form creates a business-owned copy."""
        system_form = SystemFormTemplateFactory(
            is_template_public=True,
            status=FormStatus.ACTIVE,
            created_by=user,
        )
        actor_context = ActorContext.for_user_context(user, request=None)

        forked = FormBuilderService.fork_template(
            source_template=system_form,
            actor_context=actor_context,
            actor=user,
            new_owner_type=OwnerType.BUSINESS,
            new_owner_id=business.id,
        )

        assert forked.owner_type == OwnerType.BUSINESS
        assert forked.owner_id == business.id
        assert forked.forked_from == system_form
        assert forked.status == FormStatus.DRAFT

    def test_fork_slug_collision_auto_resolves(self, user, business):
        """When the target owner already has the slug, '-1' is appended."""
        source = PublicFormTemplateFactory(
            name="Shared Form",
            slug="shared-form",
            created_by=user,
        )

        # Create an existing form with the same slug in the target owner
        FormTemplateFactory(
            name="Shared Form",
            slug="shared-form",
            owner_type=OwnerType.BUSINESS,
            owner_id=business.id,
            created_by=user,
        )

        actor_context = ActorContext.for_user_context(user, request=None)

        forked = FormBuilderService.fork_template(
            source_template=source,
            actor_context=actor_context,
            actor=user,
            new_owner_type=OwnerType.BUSINESS,
            new_owner_id=business.id,
            new_slug="shared-form",
        )

        assert forked.slug == "shared-form-1"


# =============================================================================
# FormBuilderService — Add Field
# =============================================================================


@pytest.mark.django_db
class TestFormBuilderServiceAddField:
    """Tests for FormBuilderService.add_field."""

    def test_add_field(self, draft_form, user):
        """Adding a field creates it with correct attributes."""
        field = FormBuilderService.add_field(
            form_template=draft_form,
            added_by=user,
            field_key="company_name",
            field_type=FieldType.TEXT,
            label="Company Name",
            order=1,
            is_required=True,
        )

        assert field.form_template == draft_form
        assert field.field_key == "company_name"
        assert field.field_type == FieldType.TEXT
        assert field.label == "Company Name"
        assert field.order == 1
        assert field.is_required is True

    def test_add_field_duplicate_key_raises(self, draft_form, user):
        """Adding a field with a duplicate key raises ConflictError."""
        FormBuilderService.add_field(
            form_template=draft_form,
            added_by=user,
            field_key="email",
            field_type=FieldType.EMAIL,
            label="Email",
            order=1,
        )

        with pytest.raises(ConflictError):
            FormBuilderService.add_field(
                form_template=draft_form,
                added_by=user,
                field_key="email",
                field_type=FieldType.TEXT,
                label="Email Again",
                order=2,
            )

    def test_add_field_non_editable_raises(self, user):
        """Adding a field to an archived form raises BusinessRuleViolation."""
        archived_form = ArchivedFormTemplateFactory(created_by=user)

        with pytest.raises(BusinessRuleViolation):
            FormBuilderService.add_field(
                form_template=archived_form,
                added_by=user,
                field_key="name",
                field_type=FieldType.TEXT,
                label="Name",
                order=1,
            )

    def test_add_field_non_indexable_type_raises(self, draft_form, user):
        """Indexing a non-indexable field type raises ValidationError."""
        with pytest.raises(ValidationError):
            FormBuilderService.add_field(
                form_template=draft_form,
                added_by=user,
                field_key="tags",
                field_type=FieldType.MULTISELECT,
                label="Tags",
                order=1,
                is_indexed=True,
            )

    def test_add_field_max_indexed_raises(self, draft_form, user):
        """Exceeding the max indexed fields limit raises ValidationError."""
        for i in range(5):
            FormBuilderService.add_field(
                form_template=draft_form,
                added_by=user,
                field_key=f"indexed_field_{i}",
                field_type=FieldType.TEXT,
                label=f"Indexed Field {i}",
                order=i,
                is_indexed=True,
            )

        with pytest.raises(ValidationError):
            FormBuilderService.add_field(
                form_template=draft_form,
                added_by=user,
                field_key="indexed_field_6",
                field_type=FieldType.TEXT,
                label="Indexed Field 6",
                order=6,
                is_indexed=True,
            )


# =============================================================================
# FormResponseService — Create
# =============================================================================


@pytest.mark.django_db
class TestFormResponseServiceCreate:
    """Tests for FormResponseService.create_response."""

    def test_create_response(self, active_form, user):
        """Creating a response on an active form sets correct defaults."""
        actor_context = ActorContext.for_user_context(user, request=None)

        response = FormResponseService.create_response(
            form_template=active_form,
            actor_context=actor_context,
            actor=user,
            data={"field_1": "hello"},
        )

        assert response.status == ResponseStatus.DRAFT
        assert response.form_version == active_form.version
        assert response.form_template == active_form
        assert response.submitted_by == user
        assert response.data == {"field_1": "hello"}

    def test_create_response_not_accepting(self, draft_form, user):
        """Creating a response on a non-active form raises BusinessRuleViolation."""
        actor_context = ActorContext.for_user_context(user, request=None)

        with pytest.raises(BusinessRuleViolation):
            FormResponseService.create_response(
                form_template=draft_form,
                actor_context=actor_context,
                actor=user,
                data={"field_1": "hello"},
            )


# =============================================================================
# FormResponseService — Update
# =============================================================================


@pytest.mark.django_db
class TestFormResponseServiceUpdate:
    """Tests for FormResponseService.update_response."""

    def test_update_response_data(self, draft_response, user):
        """Updating a draft response changes data."""
        new_data = {"field_1": "updated_value", "field_2": "extra"}

        result = FormResponseService.update_response(
            response=draft_response,
            updated_by=user,
            data=new_data,
        )

        assert result.data == new_data

    def test_update_non_editable_raises(self, active_form, user):
        """Updating a processed response raises BusinessRuleViolation."""
        processed_response = FormResponseFactory(
            form_template=active_form,
            submitted_by=user,
            status=ResponseStatus.PROCESSED,
            data={"field_1": "value"},
        )

        with pytest.raises(BusinessRuleViolation):
            FormResponseService.update_response(
                response=processed_response,
                updated_by=user,
                data={"field_1": "new_value"},
            )


# =============================================================================
# FormResponseService — Submit
# =============================================================================


@pytest.mark.django_db
class TestFormResponseServiceSubmit:
    """Tests for FormResponseService.submit_response."""

    def test_submit_response(self, draft_response, user):
        """Submitting a draft response with valid data sets SUBMITTED status."""
        actor_context = ActorContext.for_user_context(user, request=None)

        result = FormResponseService.submit_response(
            response=draft_response,
            actor_context=actor_context,
            actor=user,
        )

        assert result.status == ResponseStatus.SUBMITTED
        assert result.submitted_at is not None

    def test_submit_missing_required_field(self, active_form, user):
        """Submitting without required field data raises ValidationError."""
        # Add a required field to the form
        FormFieldFactory(
            form_template=active_form,
            field_key="required_field",
            field_type=FieldType.TEXT,
            label="Required Field",
            order=1,
            is_required=True,
        )

        # Create response missing the required field
        response = FormResponseFactory(
            form_template=active_form,
            submitted_by=user,
            data={"other_field": "value"},
        )

        actor_context = ActorContext.for_user_context(user, request=None)

        with pytest.raises(ValidationError):
            FormResponseService.submit_response(
                response=response,
                actor_context=actor_context,
                actor=user,
            )

    def test_submit_non_draft_raises(self, submitted_response, user):
        """Submitting a non-draft response raises BusinessRuleViolation."""
        actor_context = ActorContext.for_user_context(user, request=None)

        with pytest.raises(BusinessRuleViolation):
            FormResponseService.submit_response(
                response=submitted_response,
                actor_context=actor_context,
                actor=user,
            )


# =============================================================================
# FormResponseService — Process
# =============================================================================


@pytest.mark.django_db
class TestFormResponseServiceProcess:
    """Tests for FormResponseService.process_response."""

    def test_process_response(self, submitted_response, user):
        """Processing a submitted response sets PROCESSED status and notes."""
        result = FormResponseService.process_response(
            response=submitted_response,
            processed_by=user,
            notes="Approved by reviewer",
        )

        assert result.status == ResponseStatus.PROCESSED
        assert result.processed_at is not None
        assert result.processor_notes == "Approved by reviewer"
        assert result.processed_by == user

    def test_process_non_submitted_raises(self, draft_response, user):
        """Processing a non-submitted response raises BusinessRuleViolation."""
        with pytest.raises(BusinessRuleViolation):
            FormResponseService.process_response(
                response=draft_response,
                processed_by=user,
            )


# =============================================================================
# FormResponseService — Void
# =============================================================================


@pytest.mark.django_db
class TestFormResponseServiceVoid:
    """Tests for FormResponseService.void_response."""

    def test_void_from_draft(self, draft_response, user):
        """Voiding a draft response sets VOID status."""
        result = FormResponseService.void_response(
            response=draft_response,
            voided_by=user,
        )

        assert result.status == ResponseStatus.VOID

    def test_void_from_submitted(self, submitted_response, user):
        """Voiding a submitted response sets VOID status."""
        result = FormResponseService.void_response(
            response=submitted_response,
            voided_by=user,
        )

        assert result.status == ResponseStatus.VOID

    def test_void_processed_raises(self, active_form, user):
        """Voiding a processed response raises BusinessRuleViolation."""
        processed_response = FormResponseFactory(
            form_template=active_form,
            submitted_by=user,
            status=ResponseStatus.PROCESSED,
            data={"field_1": "value"},
        )

        with pytest.raises(BusinessRuleViolation):
            FormResponseService.void_response(
                response=processed_response,
                voided_by=user,
            )
