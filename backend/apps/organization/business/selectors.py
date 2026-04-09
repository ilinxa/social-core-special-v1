# apps/organization/business/selectors.py
"""
Business Selectors - Read-only queries for business data.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from django.db.models import QuerySet

from apps.core.exceptions import NotFound
from apps.organization.business.models import (
    BusinessAccount,
    BusinessProfile,
    BusinessSlugHistory,
)

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()


class BusinessAccountSelector:
    """Read-only queries for BusinessAccount."""

    @staticmethod
    def get_by_id(
        *, business_id: UUID, include_deleted: bool = False
    ) -> BusinessAccount:
        """
        Get a business by its UUID.

        Args:
            business_id: The business UUID.
            include_deleted: If True, include soft-deleted businesses.

        Returns:
            BusinessAccount: The business instance.

        Raises:
            NotFound: If business doesn't exist.
        """
        manager = (
            BusinessAccount.all_objects if include_deleted else BusinessAccount.objects
        )
        try:
            return manager.select_related("profile").get(id=business_id)
        except BusinessAccount.DoesNotExist:
            raise NotFound(
                message="Business not found",
                resource="BusinessAccount",
                resource_id=str(business_id),
            )

    @staticmethod
    def get_by_slug(*, slug: str, include_deleted: bool = False) -> BusinessAccount:
        """
        Get a business by its slug.

        Args:
            slug: The business slug.
            include_deleted: If True, include soft-deleted businesses.

        Returns:
            BusinessAccount: The business instance.

        Raises:
            NotFound: If business doesn't exist with this slug.
        """
        manager = (
            BusinessAccount.all_objects if include_deleted else BusinessAccount.objects
        )
        try:
            return manager.select_related("profile").get(slug=slug)
        except BusinessAccount.DoesNotExist:
            raise NotFound(
                message="Business not found",
                resource="BusinessAccount",
                resource_id=slug,
            )

    @staticmethod
    def get_by_slug_or_redirect(*, slug: str) -> tuple[BusinessAccount, str | None]:
        """
        Get a business by slug, checking slug history for redirects.

        Args:
            slug: The business slug.

        Returns:
            Tuple of (BusinessAccount, redirect_slug or None).
            If redirect_slug is not None, the request should redirect.

        Raises:
            NotFound: If business doesn't exist and no redirect found.
        """
        # Try direct match first
        try:
            business = BusinessAccount.objects.select_related("profile").get(slug=slug)
            return business, None
        except BusinessAccount.DoesNotExist:
            pass

        # Check slug history for redirect
        try:
            history = BusinessSlugHistory.objects.select_related("business").get(
                old_slug=slug
            )
            return history.business, history.business.slug
        except BusinessSlugHistory.DoesNotExist:
            raise NotFound(
                message="Business not found",
                resource="BusinessAccount",
                resource_id=slug,
            )

    @staticmethod
    def list_all(*, include_deleted: bool = False) -> QuerySet[BusinessAccount]:
        """All businesses (governance view). Optionally include soft-deleted."""
        manager = (
            BusinessAccount.all_objects if include_deleted else BusinessAccount.objects
        )
        return manager.select_related("profile").order_by("-created_at")

    @staticmethod
    def list_filtered(
        *,
        status: str | None = None,
        verification_status: str | None = None,
        business_type: str | None = None,
        country: str | None = None,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> QuerySet[BusinessAccount]:
        """Filtered list for governance. Supports status, verification, type, country, search."""
        qs = BusinessAccountSelector.list_all(include_deleted=include_deleted)
        if status:
            qs = qs.filter(status=status)
        if verification_status:
            qs = qs.filter(verification_status=verification_status)
        if business_type:
            qs = qs.filter(business_type=business_type)
        if country:
            qs = qs.filter(country=country)
        if search:
            qs = qs.filter(legal_name__icontains=search)
        return qs

    @staticmethod
    def list_active() -> QuerySet[BusinessAccount]:
        """Get all active businesses."""
        return BusinessAccount.objects.active().select_related("profile")

    @staticmethod
    def list_verified() -> QuerySet[BusinessAccount]:
        """Get all verified businesses."""
        return BusinessAccount.objects.verified().select_related("profile")

    @staticmethod
    def list_pending_verification() -> QuerySet[BusinessAccount]:
        """Get businesses pending verification."""
        return BusinessAccount.objects.pending_verification().select_related("profile")

    @staticmethod
    def list_by_country(*, country: str) -> QuerySet[BusinessAccount]:
        """Get active businesses by country."""
        return (
            BusinessAccount.objects.active()
            .filter(country=country)
            .select_related("profile")
        )

    @staticmethod
    def slug_exists(*, slug: str, exclude_business_id: UUID | None = None) -> bool:
        """
        Check if a slug is already in use (or was used historically).

        Args:
            slug: The slug to check.
            exclude_business_id: Optionally exclude a business from the check.

        Returns:
            True if slug is used/reserved, False if available.
        """
        # Check current slugs
        qs = BusinessAccount.all_objects.filter(slug=slug)
        if exclude_business_id:
            qs = qs.exclude(id=exclude_business_id)
        if qs.exists():
            return True

        # Check historical slugs (never reusable)
        if BusinessSlugHistory.objects.filter(old_slug=slug).exists():
            return True

        return False

    @staticmethod
    def list_by_owner(*, user: "User") -> QuerySet[BusinessAccount]:
        """
        Get businesses where user is the owner (via RBAC membership).
        """
        from apps.core.constants import AccountType, MembershipStatus
        from apps.rbac.selectors import MembershipSelector

        owner_memberships = MembershipSelector.get_memberships_for_user(
            user=user,
            status=MembershipStatus.ACTIVE,
        ).filter(
            account_type=AccountType.BUSINESS,
            is_owner=True,
        )
        business_ids = list(owner_memberships.values_list("account_id", flat=True))

        return BusinessAccount.objects.filter(
            id__in=business_ids,
            is_deleted=False,
        ).select_related("profile")

    @staticmethod
    def list_by_member(*, user: "User") -> QuerySet[BusinessAccount]:
        """
        Get businesses where user is an active member (including owner).
        """
        from apps.core.constants import AccountType, MembershipStatus
        from apps.rbac.selectors import MembershipSelector

        memberships = MembershipSelector.get_memberships_for_user(
            user=user,
            status=MembershipStatus.ACTIVE,
        ).filter(
            account_type=AccountType.BUSINESS,
        )
        business_ids = list(memberships.values_list("account_id", flat=True))

        return BusinessAccount.objects.filter(
            id__in=business_ids,
            is_deleted=False,
        ).select_related("profile")


class BusinessProfileSelector:
    """Read-only queries for BusinessProfile."""

    @staticmethod
    def get_by_business_id(*, business_id: UUID) -> BusinessProfile:
        """
        Get a business profile by business ID.

        Args:
            business_id: The business UUID.

        Returns:
            BusinessProfile: The profile instance.

        Raises:
            NotFound: If profile doesn't exist.
        """
        try:
            return BusinessProfile.objects.select_related("business").get(
                business_id=business_id
            )
        except BusinessProfile.DoesNotExist:
            raise NotFound(
                message="Business profile not found",
                resource="BusinessProfile",
                resource_id=str(business_id),
            )

    @staticmethod
    def list_public() -> QuerySet[BusinessProfile]:
        """Get all public business profiles."""
        return BusinessProfile.objects.filter(
            is_public=True, business__is_deleted=False, business__status="active"
        ).select_related("business")
