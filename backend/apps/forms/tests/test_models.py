"""
Tests for Form Builder Models
==============================
Comprehensive model-level tests for FormTemplate, FormField, FormResponse,
and typed Index Tables.
"""

import datetime
import uuid

import pytest
from django.db import IntegrityError

from apps.core.constants import (
    FieldType,
    FormScope,
    FormStatus,
    OwnerType,
    ResponseStatus,
)
from apps.forms.models import (
    BooleanFieldIndex,
    DateFieldIndex,
    DateTimeFieldIndex,
    DecimalFieldIndex,
    FormField,
    FormResponse,
    FormTemplate,
    IntegerFieldIndex,
    TextFieldIndex,
)
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
# FORM TEMPLATE TESTS
# =============================================================================


@pytest.mark.django_db
class TestFormTemplate:
    """Tests for the FormTemplate model."""

    def test_str(self):
        """__str__ returns 'name vN' format."""
        form = FormTemplateFactory(name="Onboarding", version=3)
        assert str(form) == "Onboarding v3"

    def test_is_system_form_true(self):
        """System-owned forms report is_system_form=True."""
        form = SystemFormTemplateFactory()
        assert form.is_system_form is True

    def test_is_system_form_false(self):
        """Business-owned forms report is_system_form=False."""
        form = FormTemplateFactory(owner_type=OwnerType.BUSINESS)
        assert form.is_system_form is False

    def test_is_editable_draft(self):
        """Draft forms are editable."""
        form = FormTemplateFactory(status=FormStatus.DRAFT)
        assert form.is_editable is True

    def test_is_editable_active(self):
        """Active forms are editable."""
        form = ActiveFormTemplateFactory()
        assert form.is_editable is True

    def test_is_editable_archived(self):
        """Archived forms are not editable."""
        form = ArchivedFormTemplateFactory()
        assert form.is_editable is False

    def test_is_editable_system_form(self):
        """System forms are never editable, regardless of status."""
        form = SystemFormTemplateFactory(status=FormStatus.ACTIVE)
        assert form.is_editable is False

    def test_accepts_responses_active_current(self):
        """Active + current forms accept responses."""
        form = ActiveFormTemplateFactory(is_current=True)
        assert form.accepts_responses is True

    def test_accepts_responses_active_not_current(self):
        """Active but non-current forms do not accept responses."""
        form = ActiveFormTemplateFactory(is_current=False)
        assert form.accepts_responses is False

    def test_accepts_responses_draft(self):
        """Draft forms do not accept responses."""
        form = FormTemplateFactory()
        assert form.accepts_responses is False

    def test_soft_delete(self):
        """Soft-deleted forms are excluded from the default manager."""
        form = FormTemplateFactory()
        form_id = form.id
        form.soft_delete()

        assert form.is_deleted is True
        assert FormTemplate.objects.filter(id=form_id).exists() is False

    def test_soft_delete_still_in_all_objects(self):
        """Soft-deleted forms remain accessible via all_objects manager."""
        form = FormTemplateFactory()
        form_id = form.id
        form.soft_delete()

        assert FormTemplate.all_objects.filter(id=form_id).exists() is True

    def test_unique_slug_per_owner_version(self):
        """Duplicate (owner_type, owner_id, slug, version) raises IntegrityError."""
        owner_id = uuid.uuid4()
        FormTemplateFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=owner_id,
            slug="onboarding",
            version=1,
        )
        with pytest.raises(IntegrityError):
            FormTemplateFactory(
                owner_type=OwnerType.BUSINESS,
                owner_id=owner_id,
                slug="onboarding",
                version=1,
            )

    def test_ordering_by_created_at_desc(self):
        """Default ordering returns newest forms first."""
        user = UserFactory()
        form_old = FormTemplateFactory(created_by=user)
        form_new = FormTemplateFactory(created_by=user)

        forms = list(
            FormTemplate.objects.filter(
                id__in=[form_old.id, form_new.id],
            )
        )
        assert forms[0].id == form_new.id
        assert forms[1].id == form_old.id


# =============================================================================
# FORM FIELD TESTS
# =============================================================================


@pytest.mark.django_db
class TestFormField:
    """Tests for the FormField model."""

    def test_str(self):
        """__str__ returns the field_key."""
        field = FormFieldFactory(field_key="full_name")
        assert str(field) == "full_name"

    def test_ordering_by_order(self):
        """Fields are ordered by the 'order' column ascending."""
        template = FormTemplateFactory()
        f2 = FormFieldFactory(form_template=template, field_key="b", order=2)
        f0 = FormFieldFactory(form_template=template, field_key="a", order=0)
        f1 = FormFieldFactory(form_template=template, field_key="c", order=1)

        fields = list(FormField.objects.filter(form_template=template))
        assert fields[0].id == f0.id
        assert fields[1].id == f1.id
        assert fields[2].id == f2.id

    def test_unique_field_key_per_form(self):
        """Duplicate field_key on the same template raises IntegrityError."""
        template = FormTemplateFactory()
        FormFieldFactory(form_template=template, field_key="email")
        with pytest.raises(IntegrityError):
            FormFieldFactory(form_template=template, field_key="email")


# =============================================================================
# FORM RESPONSE TESTS
# =============================================================================


@pytest.mark.django_db
class TestFormResponse:
    """Tests for the FormResponse model."""

    def test_str(self):
        """__str__ contains 'Response' and the status."""
        response = FormResponseFactory()
        text = str(response)
        assert "Response" in text
        assert response.status in text

    def test_is_editable_draft(self):
        """Draft responses are editable."""
        response = FormResponseFactory(status=ResponseStatus.DRAFT)
        assert response.is_editable is True

    def test_is_editable_submitted(self):
        """Submitted responses are editable."""
        response = SubmittedFormResponseFactory()
        assert response.is_editable is True

    def test_is_editable_processed(self):
        """Processed responses are not editable."""
        response = FormResponseFactory(status=ResponseStatus.PROCESSED)
        assert response.is_editable is False

    def test_is_editable_void(self):
        """Void responses are not editable."""
        response = FormResponseFactory(status=ResponseStatus.VOID)
        assert response.is_editable is False


# =============================================================================
# INDEX TABLE TESTS
# =============================================================================


@pytest.mark.django_db
class TestIndexTables:
    """Tests for typed field index tables."""

    def test_text_field_index_creation(self):
        """TextFieldIndex stores and retrieves a text value."""
        response = FormResponseFactory()
        index = TextFieldIndex.objects.create(
            response=response,
            field_key="company_name",
            value="Acme Corp",
        )
        assert TextFieldIndex.objects.filter(id=index.id).exists()
        assert index.value == "Acme Corp"

    def test_integer_field_index_creation(self):
        """IntegerFieldIndex stores and retrieves an integer value."""
        response = FormResponseFactory()
        index = IntegerFieldIndex.objects.create(
            response=response,
            field_key="employee_count",
            value=42,
        )
        assert IntegerFieldIndex.objects.filter(id=index.id).exists()
        assert index.value == 42

    def test_boolean_field_index_creation(self):
        """BooleanFieldIndex stores and retrieves a boolean value."""
        response = FormResponseFactory()
        index = BooleanFieldIndex.objects.create(
            response=response,
            field_key="accepts_terms",
            value=True,
        )
        assert BooleanFieldIndex.objects.filter(id=index.id).exists()
        assert index.value is True

    def test_date_field_index_creation(self):
        """DateFieldIndex stores and retrieves a date value."""
        response = FormResponseFactory()
        target_date = datetime.date(2026, 1, 15)
        index = DateFieldIndex.objects.create(
            response=response,
            field_key="start_date",
            value=target_date,
        )
        assert DateFieldIndex.objects.filter(id=index.id).exists()
        assert index.value == target_date

    def test_cascade_delete_on_response(self):
        """Deleting a response cascades to all related index entries."""
        response = FormResponseFactory()

        text_idx = TextFieldIndex.objects.create(
            response=response,
            field_key="name",
            value="Test",
        )
        int_idx = IntegerFieldIndex.objects.create(
            response=response,
            field_key="age",
            value=30,
        )
        bool_idx = BooleanFieldIndex.objects.create(
            response=response,
            field_key="active",
            value=True,
        )

        # Hard-delete the response (bypassing PROTECT on form_template
        # by deleting through the DB-level cascade from response side)
        response_id = response.id
        FormResponse.all_objects.filter(id=response_id).delete()

        assert not TextFieldIndex.objects.filter(id=text_idx.id).exists()
        assert not IntegerFieldIndex.objects.filter(id=int_idx.id).exists()
        assert not BooleanFieldIndex.objects.filter(id=bool_idx.id).exists()
