# apps/cms/policies.py
"""
CMS Policies
==============
Authorization logic for CMS actions.

The CMS uses MembershipPolicy.authorize_action() directly in service methods
(same pattern as Form Builder). This module provides additional CMS-specific
policy checks that go beyond permission checks.
"""

from apps.cms.models import Page, PageSectionPlacement, SectionBlockPlacement
from apps.core.exceptions import BusinessRuleViolation


class CMSPolicy:
    """CMS-specific authorization checks beyond RBAC permissions."""

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
