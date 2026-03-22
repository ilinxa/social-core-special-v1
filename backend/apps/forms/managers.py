from django.db import models

from apps.core.constants import FormStatus, OwnerType, ResponseStatus
from apps.core.models import SoftDeleteManager


class FormTemplateQuerySet(models.QuerySet):
    """Chainable query helpers for FormTemplate."""

    def active(self):
        return self.filter(status=FormStatus.ACTIVE)

    def current_versions(self):
        return self.filter(is_current=True)

    def by_owner(self, *, owner_type: str, owner_id):
        return self.filter(owner_type=owner_type, owner_id=owner_id)

    def by_scope(self, *, scope: str):
        return self.filter(scope=scope)

    def public_templates(self):
        return self.filter(
            is_template_public=True,
            status=FormStatus.ACTIVE,
            is_current=True,
        )

    def system_forms(self):
        return self.filter(owner_type=OwnerType.SYSTEM)

    def with_fields(self):
        return self.prefetch_related("fields")


class FormTemplateManager(SoftDeleteManager):
    """Manager for FormTemplate with soft-delete support."""

    def get_queryset(self):
        return FormTemplateQuerySet(self.model, using=self._db).filter(
            is_deleted=False,
        )

    def active(self):
        return self.get_queryset().active()

    def current_versions(self):
        return self.get_queryset().current_versions()

    def by_owner(self, **kwargs):
        return self.get_queryset().by_owner(**kwargs)

    def by_scope(self, **kwargs):
        return self.get_queryset().by_scope(**kwargs)

    def public_templates(self):
        return self.get_queryset().public_templates()

    def system_forms(self):
        return self.get_queryset().system_forms()

    def with_fields(self):
        return self.get_queryset().with_fields()


class FormResponseQuerySet(models.QuerySet):
    """Chainable query helpers for FormResponse."""

    def by_form(self, *, form_template_id):
        return self.filter(form_template_id=form_template_id)

    def by_submitter(self, *, user_id):
        return self.filter(submitted_by_id=user_id)

    def submitted(self):
        return self.filter(status=ResponseStatus.SUBMITTED)

    def pending_processing(self):
        return self.filter(
            status=ResponseStatus.SUBMITTED,
            processed_at__isnull=True,
        )

    def with_form(self):
        return self.select_related("form_template")


class FormResponseManager(SoftDeleteManager):
    """Manager for FormResponse with soft-delete support."""

    def get_queryset(self):
        return FormResponseQuerySet(self.model, using=self._db).filter(
            is_deleted=False,
        )
