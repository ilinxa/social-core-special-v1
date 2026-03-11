# apps/forms/tests/factories.py
"""
Factory-boy factories for Forms app tests.

Usage:
    from apps.forms.tests.factories import FormTemplateFactory, FormFieldFactory

    # Create a form template
    template = FormTemplateFactory()

    # Create with specific attributes
    template = ActiveFormTemplateFactory(name="My Active Form")

    # Build without saving to DB
    template = FormTemplateFactory.build()
"""

import uuid

import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from apps.core.constants import (
    OwnerType,
    FormScope,
    FormStatus,
    ResponseStatus,
    FieldType,
)
from apps.forms.models import FormTemplate, FormField, FormResponse
from apps.users.tests.factories import UserFactory


# =============================================================================
# FORM TEMPLATE FACTORIES
# =============================================================================


class FormTemplateFactory(DjangoModelFactory):
    """
    Factory for creating test form templates.

    Defaults to a draft business-owned form.
    """

    class Meta:
        model = FormTemplate

    name = factory.Sequence(lambda n: f"Test Form {n}")
    slug = factory.LazyAttribute(lambda obj: obj.name.lower().replace(" ", "-"))
    description = "Test form"
    owner_type = OwnerType.BUSINESS
    owner_id = factory.LazyFunction(uuid.uuid4)
    scope = FormScope.BUSINESS
    creator_context = factory.LazyFunction(dict)
    status = FormStatus.DRAFT
    version = 1
    is_current = True
    settings = factory.LazyFunction(dict)
    created_by = factory.SubFactory(UserFactory)


class ActiveFormTemplateFactory(FormTemplateFactory):
    """Factory for creating active (published) form templates."""

    status = FormStatus.ACTIVE


class ArchivedFormTemplateFactory(FormTemplateFactory):
    """Factory for creating archived form templates."""

    status = FormStatus.ARCHIVED


class SystemFormTemplateFactory(FormTemplateFactory):
    """Factory for creating system-owned form templates."""

    owner_type = OwnerType.SYSTEM
    owner_id = None


class PublicFormTemplateFactory(ActiveFormTemplateFactory):
    """Factory for creating public template library entries."""

    is_template_public = True


# =============================================================================
# FORM FIELD FACTORIES
# =============================================================================


class FormFieldFactory(DjangoModelFactory):
    """
    Factory for creating test form fields.

    Defaults to a non-required text field.
    """

    class Meta:
        model = FormField

    form_template = factory.SubFactory(FormTemplateFactory)
    field_key = factory.Sequence(lambda n: f"field_{n}")
    field_type = FieldType.TEXT
    label = factory.LazyAttribute(
        lambda obj: obj.field_key.replace("_", " ").title()
    )
    description = ""
    placeholder = ""
    order = factory.Sequence(lambda n: n)
    step_tag = ""
    section_tag = ""
    options = factory.LazyFunction(list)
    validation_rules = factory.LazyFunction(dict)
    ui_config = factory.LazyFunction(dict)
    default_value = None
    is_required = False
    is_indexed = False
    is_hidden = False
    is_readonly = False


# =============================================================================
# FORM RESPONSE FACTORIES
# =============================================================================


class FormResponseFactory(DjangoModelFactory):
    """
    Factory for creating test form responses.

    Defaults to a draft response on an active form template.
    """

    class Meta:
        model = FormResponse

    form_template = factory.SubFactory(ActiveFormTemplateFactory)
    form_version = factory.LazyAttribute(lambda obj: obj.form_template.version)
    submitted_by = factory.SubFactory(UserFactory)
    submitter_context = factory.LazyFunction(dict)
    data = factory.LazyFunction(dict)
    status = ResponseStatus.DRAFT


class SubmittedFormResponseFactory(FormResponseFactory):
    """Factory for creating submitted form responses."""

    status = ResponseStatus.SUBMITTED
    submitted_at = factory.LazyFunction(timezone.now)
