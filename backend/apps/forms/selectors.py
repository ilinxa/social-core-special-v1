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
        form = FormTemplate.objects.filter(id=form_template_id).first()
        if not form:
            raise NotFound(resource="FormTemplate", resource_id=form_template_id)
        return form

    @staticmethod
    def get_by_id_or_none(*, form_template_id: UUID) -> Optional[FormTemplate]:
        return FormTemplate.objects.filter(id=form_template_id).first()

    @staticmethod
    def get_by_slug(
        *,
        owner_type: str,
        owner_id: Optional[UUID],
        slug: str,
        current_only: bool = True,
    ) -> FormTemplate:
        qs = FormTemplate.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            slug=slug,
        )
        if current_only:
            qs = qs.filter(is_current=True)
        form = qs.first()
        if not form:
            raise NotFound(
                message=f"Form '{slug}' not found",
                resource="FormTemplate",
                resource_id=slug,
            )
        return form

    @staticmethod
    def get_current_version(*, form_template_id: UUID) -> FormTemplate:
        form = FormTemplateSelector.get_by_id(form_template_id=form_template_id)
        if form.is_current:
            return form
        current = FormTemplate.objects.filter(
            owner_type=form.owner_type,
            owner_id=form.owner_id,
            slug=form.slug,
            is_current=True,
        ).first()
        if not current:
            raise NotFound(
                message="No current version found",
                resource="FormTemplate",
                resource_id=form_template_id,
            )
        return current

    @staticmethod
    def list_by_owner(
        *,
        owner_type: str,
        owner_id: Optional[UUID],
        status: Optional[str] = None,
        current_only: bool = True,
    ) -> QuerySet[FormTemplate]:
        qs = FormTemplate.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id,
        )
        if status:
            qs = qs.filter(status=status)
        if current_only:
            qs = qs.filter(is_current=True)
        return qs

    @staticmethod
    def list_public_templates(*, scope: Optional[str] = None) -> QuerySet[FormTemplate]:
        qs = FormTemplate.objects.public_templates()
        if scope:
            qs = qs.filter(scope=scope)
        return qs

    @staticmethod
    def list_system_forms(*, scope: Optional[str] = None) -> QuerySet[FormTemplate]:
        qs = FormTemplate.objects.filter(
            owner_type=OwnerType.SYSTEM,
            is_current=True,
        )
        if scope:
            qs = qs.filter(scope=scope)
        return qs

    @staticmethod
    def get_by_slug_or_none(
        *,
        owner_type: str,
        owner_id: Optional[UUID],
        slug: str,
        current_only: bool = True,
    ) -> Optional[FormTemplate]:
        qs = FormTemplate.objects.filter(
            owner_type=owner_type,
            owner_id=owner_id,
            slug=slug,
        )
        if current_only:
            qs = qs.filter(is_current=True)
        return qs.first()

    @staticmethod
    def get_with_fields(*, form_template_id: UUID) -> FormTemplate:
        form = (
            FormTemplate.objects.prefetch_related("fields")
            .filter(id=form_template_id)
            .first()
        )
        if not form:
            raise NotFound(resource="FormTemplate", resource_id=form_template_id)
        return form

    @staticmethod
    def count_indexed_fields(*, form_template_id: UUID) -> int:
        return FormField.objects.filter(
            form_template_id=form_template_id,
            is_indexed=True,
        ).count()


class FormFieldSelector:
    """Read-only queries for FormField."""

    @staticmethod
    def get_by_id(*, field_id: UUID) -> FormField:
        field = (
            FormField.objects.select_related("form_template")
            .filter(id=field_id)
            .first()
        )
        if not field:
            raise NotFound(resource="FormField", resource_id=field_id)
        return field

    @staticmethod
    def list_by_form(
        *,
        form_template_id: UUID,
        step_tag: Optional[str] = None,
    ) -> QuerySet[FormField]:
        qs = FormField.objects.filter(form_template_id=form_template_id)
        if step_tag:
            qs = qs.filter(step_tag=step_tag)
        return qs.order_by("order")

    @staticmethod
    def list_indexed_fields(*, form_template_id: UUID) -> QuerySet[FormField]:
        return FormField.objects.filter(
            form_template_id=form_template_id,
            is_indexed=True,
        ).order_by("order")

    @staticmethod
    def get_step_tags(*, form_template_id: UUID) -> List[str]:
        return list(
            FormField.objects.filter(form_template_id=form_template_id)
            .exclude(step_tag="")
            .values_list("step_tag", flat=True)
            .distinct()
            .order_by("order")
        )


class FormResponseSelector:
    """Read-only queries for FormResponse."""

    @staticmethod
    def get_by_id(*, response_id: UUID) -> FormResponse:
        response = (
            FormResponse.objects.select_related("form_template", "submitted_by")
            .filter(id=response_id)
            .first()
        )
        if not response:
            raise NotFound(resource="FormResponse", resource_id=response_id)
        return response

    @staticmethod
    def get_by_id_or_none(*, response_id: UUID) -> Optional[FormResponse]:
        return FormResponse.objects.filter(id=response_id).first()

    @staticmethod
    def list_by_form(
        *,
        form_template_id: UUID,
        status: Optional[str] = None,
    ) -> QuerySet[FormResponse]:
        qs = FormResponse.objects.filter(
            form_template_id=form_template_id,
        ).select_related("submitted_by__profile", "form_template")
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    @staticmethod
    def list_by_submitter(
        *,
        user_id: UUID,
        form_template_id: Optional[UUID] = None,
    ) -> QuerySet[FormResponse]:
        qs = FormResponse.objects.filter(submitted_by_id=user_id)
        if form_template_id:
            qs = qs.filter(form_template_id=form_template_id)
        return qs.select_related("form_template")

    @staticmethod
    def get_by_transaction_id(*, transaction_id: UUID) -> Optional[FormResponse]:
        return (
            FormResponse.objects.select_related("form_template")
            .filter(transaction_id=transaction_id)
            .first()
        )

    @staticmethod
    def exists_for_user_and_form(
        *,
        user_id: UUID,
        form_template_id: UUID,
        status: Optional[str] = None,
    ) -> bool:
        qs = FormResponse.objects.filter(
            submitted_by_id=user_id,
            form_template_id=form_template_id,
        )
        if status:
            qs = qs.filter(status=status)
        return qs.exists()
