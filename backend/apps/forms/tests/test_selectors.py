"""
Tests for Form Builder Selectors
==================================
Comprehensive selector-level tests for FormTemplateSelector, FormFieldSelector,
and FormResponseSelector.
"""

import uuid

import pytest

from apps.core.constants import (
    FormStatus,
    OwnerType,
    FormScope,
    ResponseStatus,
    FieldType,
)
from apps.core.exceptions import NotFound
from apps.forms.selectors import (
    FormTemplateSelector,
    FormFieldSelector,
    FormResponseSelector,
)
from apps.forms.tests.factories import (
    FormTemplateFactory,
    ActiveFormTemplateFactory,
    SystemFormTemplateFactory,
    PublicFormTemplateFactory,
    FormFieldFactory,
    FormResponseFactory,
)
from apps.users.tests.factories import UserFactory


# =============================================================================
# FORM TEMPLATE SELECTOR TESTS
# =============================================================================


@pytest.mark.django_db
class TestFormTemplateSelector:
    """Tests for FormTemplateSelector read-only queries."""

    # ---- get_by_id ---------------------------------------------------------

    def test_get_by_id(self):
        """get_by_id returns the form template matching the given ID."""
        form = FormTemplateFactory()

        result = FormTemplateSelector.get_by_id(form_template_id=form.id)

        assert result.id == form.id
        assert result.name == form.name

    def test_get_by_id_not_found(self):
        """get_by_id raises NotFound for a non-existent UUID."""
        random_id = uuid.uuid4()

        with pytest.raises(NotFound):
            FormTemplateSelector.get_by_id(form_template_id=random_id)

    # ---- get_by_id_or_none -------------------------------------------------

    def test_get_by_id_or_none_found(self):
        """get_by_id_or_none returns the form template when it exists."""
        form = FormTemplateFactory()

        result = FormTemplateSelector.get_by_id_or_none(form_template_id=form.id)

        assert result is not None
        assert result.id == form.id

    def test_get_by_id_or_none_not_found(self):
        """get_by_id_or_none returns None for a non-existent UUID."""
        random_id = uuid.uuid4()

        result = FormTemplateSelector.get_by_id_or_none(form_template_id=random_id)

        assert result is None

    # ---- get_by_slug -------------------------------------------------------

    def test_get_by_slug(self):
        """get_by_slug returns the form matching owner + slug."""
        form = FormTemplateFactory(slug="my-form")

        result = FormTemplateSelector.get_by_slug(
            owner_type=form.owner_type,
            owner_id=form.owner_id,
            slug=form.slug,
        )

        assert result.id == form.id
        assert result.slug == "my-form"

    def test_get_by_slug_not_found(self):
        """get_by_slug raises NotFound when no matching form exists."""
        with pytest.raises(NotFound):
            FormTemplateSelector.get_by_slug(
                owner_type=OwnerType.BUSINESS,
                owner_id=uuid.uuid4(),
                slug="nonexistent-slug",
            )

    # ---- get_current_version -----------------------------------------------

    def test_get_current_version_already_current(self):
        """get_current_version returns the same form if it is already current."""
        form = FormTemplateFactory(is_current=True)

        result = FormTemplateSelector.get_current_version(form_template_id=form.id)

        assert result.id == form.id

    def test_get_current_version_returns_current(self):
        """get_current_version resolves a stale version to the current one."""
        owner_id = uuid.uuid4()
        v1 = FormTemplateFactory(
            slug="versioned-form",
            owner_id=owner_id,
            version=1,
            is_current=False,
        )
        v2 = FormTemplateFactory(
            slug="versioned-form",
            owner_type=v1.owner_type,
            owner_id=owner_id,
            version=2,
            is_current=True,
        )

        result = FormTemplateSelector.get_current_version(form_template_id=v1.id)

        assert result.id == v2.id
        assert result.version == 2

    # ---- list_by_owner -----------------------------------------------------

    def test_list_by_owner(self):
        """list_by_owner returns only forms owned by the specified owner."""
        owner_id = uuid.uuid4()
        other_owner_id = uuid.uuid4()

        FormTemplateFactory(owner_id=owner_id, slug="form-a")
        FormTemplateFactory(owner_id=owner_id, slug="form-b")
        FormTemplateFactory(owner_id=other_owner_id, slug="form-c")

        results = FormTemplateSelector.list_by_owner(
            owner_type=OwnerType.BUSINESS,
            owner_id=owner_id,
        )

        assert results.count() == 2
        slugs = set(results.values_list("slug", flat=True))
        assert slugs == {"form-a", "form-b"}

    def test_list_by_owner_with_status_filter(self):
        """list_by_owner filters by status when provided."""
        owner_id = uuid.uuid4()

        FormTemplateFactory(
            owner_id=owner_id,
            slug="draft-form",
            status=FormStatus.DRAFT,
        )
        ActiveFormTemplateFactory(
            owner_id=owner_id,
            slug="active-form",
        )

        results = FormTemplateSelector.list_by_owner(
            owner_type=OwnerType.BUSINESS,
            owner_id=owner_id,
            status=FormStatus.ACTIVE,
        )

        assert results.count() == 1
        assert results.first().slug == "active-form"

    def test_list_by_owner_current_only(self):
        """list_by_owner with current_only=True excludes non-current versions."""
        owner_id = uuid.uuid4()

        FormTemplateFactory(
            owner_id=owner_id,
            slug="versioned",
            version=1,
            is_current=False,
        )
        current = FormTemplateFactory(
            owner_id=owner_id,
            slug="versioned",
            version=2,
            is_current=True,
        )

        results = FormTemplateSelector.list_by_owner(
            owner_type=OwnerType.BUSINESS,
            owner_id=owner_id,
            current_only=True,
        )

        assert results.count() == 1
        assert results.first().id == current.id

    # ---- list_public_templates ---------------------------------------------

    def test_list_public_templates(self):
        """list_public_templates returns only public, active, current forms."""
        PublicFormTemplateFactory(slug="public-form")
        FormTemplateFactory(slug="private-form")  # not public

        results = FormTemplateSelector.list_public_templates()
        slugs = set(results.values_list("slug", flat=True))

        assert "public-form" in slugs
        assert "private-form" not in slugs

    def test_list_public_templates_scope_filter(self):
        """list_public_templates filters by scope when provided."""
        PublicFormTemplateFactory(slug="platform-public", scope=FormScope.PLATFORM)
        PublicFormTemplateFactory(slug="business-public", scope=FormScope.BUSINESS)

        results = FormTemplateSelector.list_public_templates(
            scope=FormScope.PLATFORM,
        )
        slugs = set(results.values_list("slug", flat=True))

        assert "platform-public" in slugs
        assert "business-public" not in slugs

    # ---- list_system_forms -------------------------------------------------

    def test_list_system_forms(self):
        """list_system_forms returns only system-owned, current forms."""
        SystemFormTemplateFactory(slug="system-form")
        FormTemplateFactory(slug="non-system-form")  # business-owned

        results = FormTemplateSelector.list_system_forms()

        # 3 from seed migration + 1 from factory
        assert results.filter(slug="system-form").exists()
        assert not results.filter(slug="non-system-form").exists()

    # ---- get_with_fields ---------------------------------------------------

    def test_get_with_fields(self):
        """get_with_fields returns the form with fields prefetched."""
        form = FormTemplateFactory()
        FormFieldFactory(form_template=form, field_key="first_name", order=0)
        FormFieldFactory(form_template=form, field_key="last_name", order=1)

        result = FormTemplateSelector.get_with_fields(form_template_id=form.id)

        assert result.id == form.id
        # Access prefetched fields without additional queries.
        field_keys = [f.field_key for f in result.fields.all()]
        assert len(field_keys) == 2
        assert set(field_keys) == {"first_name", "last_name"}

    # ---- count_indexed_fields ----------------------------------------------

    def test_count_indexed_fields(self):
        """count_indexed_fields returns the number of indexed fields only."""
        form = FormTemplateFactory()
        FormFieldFactory(form_template=form, field_key="indexed_1", is_indexed=True, order=0)
        FormFieldFactory(form_template=form, field_key="indexed_2", is_indexed=True, order=1)
        FormFieldFactory(form_template=form, field_key="not_indexed", is_indexed=False, order=2)

        count = FormTemplateSelector.count_indexed_fields(form_template_id=form.id)

        assert count == 2


# =============================================================================
# FORM FIELD SELECTOR TESTS
# =============================================================================


@pytest.mark.django_db
class TestFormFieldSelector:
    """Tests for FormFieldSelector read-only queries."""

    # ---- get_by_id ---------------------------------------------------------

    def test_get_by_id(self):
        """get_by_id returns the field with form_template selected."""
        field = FormFieldFactory()

        result = FormFieldSelector.get_by_id(field_id=field.id)

        assert result.id == field.id
        # form_template should be select_related — no extra query needed.
        assert result.form_template is not None
        assert result.form_template.id == field.form_template_id

    def test_get_by_id_not_found(self):
        """get_by_id raises NotFound for a non-existent UUID."""
        random_id = uuid.uuid4()

        with pytest.raises(NotFound):
            FormFieldSelector.get_by_id(field_id=random_id)

    # ---- list_by_form ------------------------------------------------------

    def test_list_by_form(self):
        """list_by_form returns all fields for the given form, ordered."""
        form_a = FormTemplateFactory()
        form_b = FormTemplateFactory()

        f1 = FormFieldFactory(form_template=form_a, field_key="c_field", order=2)
        f2 = FormFieldFactory(form_template=form_a, field_key="a_field", order=0)
        f3 = FormFieldFactory(form_template=form_a, field_key="b_field", order=1)
        FormFieldFactory(form_template=form_b, field_key="other", order=0)

        results = FormFieldSelector.list_by_form(form_template_id=form_a.id)

        assert results.count() == 3
        ids = list(results.values_list("id", flat=True))
        assert ids == [f2.id, f3.id, f1.id]  # ordered by 'order' field

    def test_list_by_form_step_filter(self):
        """list_by_form filters by step_tag when provided."""
        form = FormTemplateFactory()
        FormFieldFactory(form_template=form, field_key="s1_f1", step_tag="step1", order=0)
        FormFieldFactory(form_template=form, field_key="s1_f2", step_tag="step1", order=1)
        FormFieldFactory(form_template=form, field_key="s2_f1", step_tag="step2", order=2)

        results = FormFieldSelector.list_by_form(
            form_template_id=form.id,
            step_tag="step1",
        )

        assert results.count() == 2
        keys = list(results.values_list("field_key", flat=True))
        assert keys == ["s1_f1", "s1_f2"]

    # ---- list_indexed_fields -----------------------------------------------

    def test_list_indexed_fields(self):
        """list_indexed_fields returns only indexed fields, ordered."""
        form = FormTemplateFactory()
        FormFieldFactory(form_template=form, field_key="idx_1", is_indexed=True, order=1)
        FormFieldFactory(form_template=form, field_key="idx_2", is_indexed=True, order=0)
        FormFieldFactory(form_template=form, field_key="normal", is_indexed=False, order=2)

        results = FormFieldSelector.list_indexed_fields(form_template_id=form.id)

        assert results.count() == 2
        keys = list(results.values_list("field_key", flat=True))
        assert keys == ["idx_2", "idx_1"]  # ordered by 'order' field

    # ---- get_step_tags -----------------------------------------------------

    def test_get_step_tags(self):
        """get_step_tags returns distinct non-empty step_tags ordered by first occurrence."""
        form = FormTemplateFactory()
        FormFieldFactory(form_template=form, field_key="f1", step_tag="step1", order=0)
        FormFieldFactory(form_template=form, field_key="f2", step_tag="step2", order=1)
        FormFieldFactory(form_template=form, field_key="f3", step_tag="", order=2)  # excluded

        tags = FormFieldSelector.get_step_tags(form_template_id=form.id)

        assert tags == ["step1", "step2"]


# =============================================================================
# FORM RESPONSE SELECTOR TESTS
# =============================================================================


@pytest.mark.django_db
class TestFormResponseSelector:
    """Tests for FormResponseSelector read-only queries."""

    # ---- get_by_id ---------------------------------------------------------

    def test_get_by_id(self):
        """get_by_id returns the response with form_template and submitted_by selected."""
        response = FormResponseFactory()

        result = FormResponseSelector.get_by_id(response_id=response.id)

        assert result.id == response.id
        # select_related fields should be populated without extra queries.
        assert result.form_template is not None
        assert result.submitted_by is not None
        assert result.form_template.id == response.form_template_id
        assert result.submitted_by.id == response.submitted_by_id

    def test_get_by_id_not_found(self):
        """get_by_id raises NotFound for a non-existent UUID."""
        random_id = uuid.uuid4()

        with pytest.raises(NotFound):
            FormResponseSelector.get_by_id(response_id=random_id)

    # ---- get_by_id_or_none -------------------------------------------------

    def test_get_by_id_or_none_found(self):
        """get_by_id_or_none returns the response when it exists."""
        response = FormResponseFactory()

        result = FormResponseSelector.get_by_id_or_none(response_id=response.id)

        assert result is not None
        assert result.id == response.id

    def test_get_by_id_or_none_not_found(self):
        """get_by_id_or_none returns None for a non-existent UUID."""
        random_id = uuid.uuid4()

        result = FormResponseSelector.get_by_id_or_none(response_id=random_id)

        assert result is None

    # ---- list_by_form ------------------------------------------------------

    def test_list_by_form(self):
        """list_by_form returns only responses for the given form template."""
        form_a = ActiveFormTemplateFactory()
        form_b = ActiveFormTemplateFactory()

        FormResponseFactory(form_template=form_a)
        FormResponseFactory(form_template=form_a)
        FormResponseFactory(form_template=form_b)

        results = FormResponseSelector.list_by_form(form_template_id=form_a.id)

        assert results.count() == 2

    def test_list_by_form_status_filter(self):
        """list_by_form filters by status when provided."""
        form = ActiveFormTemplateFactory()

        FormResponseFactory(form_template=form, status=ResponseStatus.DRAFT)
        FormResponseFactory(form_template=form, status=ResponseStatus.SUBMITTED)

        results = FormResponseSelector.list_by_form(
            form_template_id=form.id,
            status=ResponseStatus.SUBMITTED,
        )

        assert results.count() == 1
        assert results.first().status == ResponseStatus.SUBMITTED

    # ---- list_by_submitter -------------------------------------------------

    def test_list_by_submitter(self):
        """list_by_submitter returns only responses by the given user."""
        user_a = UserFactory()
        user_b = UserFactory()

        FormResponseFactory(submitted_by=user_a)
        FormResponseFactory(submitted_by=user_a)
        FormResponseFactory(submitted_by=user_b)

        results = FormResponseSelector.list_by_submitter(user_id=user_a.id)

        assert results.count() == 2

    def test_list_by_submitter_form_filter(self):
        """list_by_submitter filters by form_template_id when provided."""
        user = UserFactory()
        form_a = ActiveFormTemplateFactory()
        form_b = ActiveFormTemplateFactory()

        FormResponseFactory(submitted_by=user, form_template=form_a)
        FormResponseFactory(submitted_by=user, form_template=form_b)

        results = FormResponseSelector.list_by_submitter(
            user_id=user.id,
            form_template_id=form_a.id,
        )

        assert results.count() == 1
        assert results.first().form_template_id == form_a.id

    # ---- exists_for_user_and_form ------------------------------------------

    def test_exists_for_user_and_form_true(self):
        """exists_for_user_and_form returns True when a response exists."""
        response = FormResponseFactory()

        result = FormResponseSelector.exists_for_user_and_form(
            user_id=response.submitted_by_id,
            form_template_id=response.form_template_id,
        )

        assert result is True

    def test_exists_for_user_and_form_false(self):
        """exists_for_user_and_form returns False when no response exists."""
        user = UserFactory()
        form = ActiveFormTemplateFactory()

        result = FormResponseSelector.exists_for_user_and_form(
            user_id=user.id,
            form_template_id=form.id,
        )

        assert result is False
