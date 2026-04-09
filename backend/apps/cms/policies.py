# apps/cms/policies.py
"""
CMS Policies
==============
Authorization logic for CMS actions.

The CMS uses MembershipPolicy.authorize_action() directly in service methods
(same pattern as Form Builder). This module provides additional CMS-specific
policy checks that go beyond permission checks.
"""

from apps.cms.models import (
    BlockTemplateActivation,
    Page,
    PageSectionPlacement,
    SectionBlockPlacement,
    SectionTemplateActivation,
)
from apps.core.exceptions import BusinessRuleViolation


def _safe_check(fn, **kwargs) -> bool:
    """Convert exception-raising permission checks to booleans."""
    try:
        fn(**kwargs)
        return True
    except Exception:
        return False


class CMSPolicy:
    """CMS-specific authorization checks beyond RBAC permissions."""

    @staticmethod
    def get_viewer_permissions(*, user, actor_context=None) -> dict[str, bool]:
        """
        Tier 1.5: Return evaluated permission booleans for CMS resources.

        Injected into GET detail responses via PermissionInjectMixin.
        Uses actor_context permissions snapshot when available,
        falls back to basic auth checks.
        """
        from apps.rbac.policies import MembershipPolicy

        if not user or not user.is_authenticated:
            return {
                "can_view_content": False,
                "can_edit_content": False,
                "can_publish_content": False,
                "can_create_site": False,
                "can_edit_site": False,
                "can_delete_site": False,
                "can_create_page": False,
                "can_edit_page": False,
                "can_delete_page": False,
                "can_upload_media": False,
                "can_edit_media": False,
                "can_delete_media": False,
                "can_create_api_key": False,
                "can_activate_template": False,
            }

        if actor_context is None:
            return {"can_view_content": True}

        def _has(perm_code):
            return _safe_check(
                MembershipPolicy.authorize_action,
                actor_context=actor_context,
                required_permission=perm_code,
            )

        return {
            "can_view_content": _has("can_view_cms_content"),
            "can_edit_content": _has("can_edit_cms_content"),
            "can_publish_content": _has("can_publish_cms_content"),
            "can_create_site": _has("can_create_cms_site"),
            "can_edit_site": _has("can_edit_cms_site"),
            "can_delete_site": _has("can_delete_cms_site"),
            "can_create_page": _has("can_create_cms_page"),
            "can_edit_page": _has("can_edit_cms_page"),
            "can_delete_page": _has("can_delete_cms_page"),
            "can_upload_media": _has("can_upload_cms_media"),
            "can_edit_media": _has("can_edit_cms_media"),
            "can_delete_media": _has("can_delete_cms_media"),
            "can_create_api_key": _has("can_create_cms_api_key"),
            "can_activate_template": _has("can_activate_cms_template"),
        }

    @staticmethod
    def can_delete_page(*, page: Page) -> None:
        """Check if a page can be deleted."""
        if page.is_required:
            raise BusinessRuleViolation(
                message="Required pages cannot be deleted",
                rule="required_page_delete",
            )

    @staticmethod
    def can_hide_page(*, page: Page) -> None:
        """Check if a page can be hidden."""
        if page.is_required:
            raise BusinessRuleViolation(
                message="Required pages cannot be hidden",
                rule="required_page_hide",
            )

    @staticmethod
    def can_hide_section_placement(*, placement: PageSectionPlacement) -> None:
        """Check if a section placement can be hidden."""
        if placement.is_required:
            raise BusinessRuleViolation(
                message="Required section placements cannot be hidden",
                rule="required_section_hide",
            )

    @staticmethod
    def can_hide_block_placement(*, placement: SectionBlockPlacement) -> None:
        """Check if a block placement can be hidden."""
        if placement.is_required:
            raise BusinessRuleViolation(
                message="Required block placements cannot be hidden",
                rule="required_block_hide",
            )


class CMSActivationPolicy:
    """Policy checks for template activation/deactivation."""

    @staticmethod
    def can_deactivate_section_template(
        *, activation: SectionTemplateActivation, org_type: str, org_id
    ) -> None:
        """Cannot deactivate if active placements reference this template."""
        has_usage = PageSectionPlacement.objects.filter(
            template=activation.template,
            page__site__owner_type=org_type,
            page__site__owner_id=org_id,
            page__is_deleted=False,
        ).exists()
        if has_usage:
            raise BusinessRuleViolation(
                message="Cannot deactivate template that is in use by active pages",
                rule="template_in_use",
            )

    @staticmethod
    def can_deactivate_block_template(
        *, activation: BlockTemplateActivation, org_type: str, org_id
    ) -> None:
        """Cannot deactivate if active placements reference this template."""
        has_usage = SectionBlockPlacement.objects.filter(
            template=activation.template,
            section_placement__page__site__owner_type=org_type,
            section_placement__page__site__owner_id=org_id,
            section_placement__page__is_deleted=False,
        ).exists()
        if has_usage:
            raise BusinessRuleViolation(
                message="Cannot deactivate template that is in use by active pages",
                rule="template_in_use",
            )
