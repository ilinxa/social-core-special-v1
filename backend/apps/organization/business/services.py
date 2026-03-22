# apps/organization/business/services.py
"""
Business Services - Business logic for business account operations.

All write operations go through services. Services use keyword-only arguments
for clarity and to prevent positional argument errors.

Key rules:
- owner parameter in create_business() is the authenticated request.user
- Slugs must be validated against both current and historical slugs
- Ownership is tracked via RBAC Membership.is_owner flag
"""

from typing import TYPE_CHECKING
from uuid import UUID

from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.core.constants import BusinessStatus, VerificationStatus
from apps.core.exceptions import ConflictError, ValidationError
from apps.core.observability import AuditLog, AuditService, get_logger
from apps.organization.business.models import (
    BusinessAccount,
    BusinessProfile,
    BusinessSlugHistory,
)
from apps.organization.business.selectors import BusinessAccountSelector

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model

    User = get_user_model()

logger = get_logger(__name__)


class BusinessAccountService:
    """Service for BusinessAccount operations."""

    @staticmethod
    def _validate_slug(*, slug: str, exclude_business_id: UUID | None = None) -> None:
        """
        Validate that a slug is available.

        Args:
            slug: The slug to validate.
            exclude_business_id: Optionally exclude a business from the check.

        Raises:
            ConflictError: If slug is already in use or was used historically.
        """
        if BusinessAccountSelector.slug_exists(
            slug=slug, exclude_business_id=exclude_business_id
        ):
            raise ConflictError(
                message=f"Slug '{slug}' is not available",
                resource="BusinessAccount",
                conflict_type="slug_taken",
            )

    @staticmethod
    @transaction.atomic
    def create_business(
        *,
        owner: "User",
        legal_name: str,
        country: str,
        slug: str | None = None,
        business_type: str | None = None,
        registration_number: str | None = None,
        tax_id: str | None = None,
        legal_address: str | None = None,
        display_name: str | None = None,
        request=None,
    ) -> BusinessAccount:
        """
        Create a new business account.

        The owner parameter is the authenticated user (request.user).
        This user becomes the initial owner via RBAC membership creation.

        Args:
            owner: The user creating the business (becomes owner).
            legal_name: Legal business name.
            country: ISO 3166-1 alpha-2 country code.
            slug: URL slug (auto-generated from legal_name if not provided).
            business_type: Type of business (from BusinessType choices).
            registration_number: Business registration number.
            tax_id: Tax identification number.
            legal_address: Legal address.
            display_name: Display name for profile (defaults to legal_name).
            request: HTTP request for audit context.

        Returns:
            BusinessAccount: The created business.

        Raises:
            ConflictError: If slug is already in use.
        """
        # Generate slug if not provided
        if not slug:
            slug = slugify(legal_name)

        # Validate slug availability
        BusinessAccountService._validate_slug(slug=slug)

        # Create business account
        business = BusinessAccount.objects.create(
            legal_name=legal_name,
            slug=slug,
            country=country,
            business_type=business_type or "other",
            registration_number=registration_number or "",
            tax_id=tax_id or "",
            legal_address=legal_address or "",
            status=BusinessStatus.ACTIVE,
            created_by=owner,
            updated_by=owner,
        )

        # Create profile
        BusinessProfile.objects.create(
            business=business,
            display_name=display_name or legal_name,
        )

        logger.info(
            "business.created",
            business_id=str(business.id),
            slug=business.slug,
            owner_id=str(owner.id),
        )

        AuditService.log(
            action=AuditLog.Action.BUSINESS_CREATED,
            actor=owner,
            resource=business,
            resource_type="BusinessAccount",
            resource_id=business.id,
            request=request,
            details={
                "legal_name": legal_name,
                "slug": slug,
                "country": country,
            },
        )

        # RBAC Integration: Create roles and owner membership
        from apps.rbac.services import RBACService

        RBACService.initialize_business_account(
            business_id=business.id,
            owner=owner,  # request.user - becomes initial owner
            request=request,
        )

        # This creates:
        # 1. Predefined roles (Owner level 0, Base Member level 10)
        # 2. Owner membership for the user with is_owner=True
        #
        # INVARIANT: The `owner` param is the authenticated user (request.user).
        # This user gets a Membership with is_owner=True.
        # Ownership is determined by Membership.is_owner flag, NOT by role name.

        return business

    @staticmethod
    @transaction.atomic
    def update(
        *,
        business: BusinessAccount,
        legal_name: str | None = None,
        registration_number: str | None = None,
        tax_id: str | None = None,
        country: str | None = None,
        city: str | None = None,
        legal_address: str | None = None,
        business_type: str | None = None,
        settings: dict | None = None,
        open_member_request: bool | None = None,
        actor: "User",
        request=None,
    ) -> BusinessAccount:
        """
        Update a business account.

        Args:
            business: The business to update.
            legal_name: New legal name.
            registration_number: New registration number.
            tax_id: New tax ID.
            country: New country code.
            city: City name.
            legal_address: New legal address.
            business_type: New business type.
            settings: New settings to merge.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            BusinessAccount: Updated business.
        """
        changes = {}
        update_fields = ["updated_by", "updated_at"]

        if legal_name is not None and legal_name != business.legal_name:
            changes["legal_name"] = {"old": business.legal_name, "new": legal_name}
            business.legal_name = legal_name
            update_fields.append("legal_name")

        if (
            registration_number is not None
            and registration_number != business.registration_number
        ):
            changes["registration_number"] = {
                "old": business.registration_number,
                "new": registration_number,
            }
            business.registration_number = registration_number
            update_fields.append("registration_number")

        if tax_id is not None and tax_id != business.tax_id:
            changes["tax_id"] = {"old": business.tax_id, "new": tax_id}
            business.tax_id = tax_id
            update_fields.append("tax_id")

        if country is not None and country != business.country:
            changes["country"] = {"old": business.country, "new": country}
            business.country = country
            update_fields.append("country")

        if city is not None and city != business.city:
            changes["city"] = {"old": business.city, "new": city}
            business.city = city
            update_fields.append("city")

        if legal_address is not None and legal_address != business.legal_address:
            changes["legal_address"] = {
                "old": business.legal_address,
                "new": legal_address,
            }
            business.legal_address = legal_address
            update_fields.append("legal_address")

        if business_type is not None and business_type != business.business_type:
            changes["business_type"] = {
                "old": business.business_type,
                "new": business_type,
            }
            business.business_type = business_type
            update_fields.append("business_type")

        if settings is not None:
            old_settings = business.settings.copy()
            business.settings.update(settings)
            changes["settings"] = {"old": old_settings, "new": business.settings}
            update_fields.append("settings")

        if (
            open_member_request is not None
            and open_member_request != business.open_member_request
        ):
            changes["open_member_request"] = {
                "old": business.open_member_request,
                "new": open_member_request,
            }
            business.open_member_request = open_member_request
            update_fields.append("open_member_request")

        business.updated_by = actor
        business.save(update_fields=update_fields)

        if changes:
            logger.info(
                "business.updated",
                business_id=str(business.id),
                changed_fields=list(changes.keys()),
            )

            AuditService.log_change(
                action=AuditLog.Action.BUSINESS_UPDATED,
                actor=actor,
                resource=business,
                before={k: v["old"] for k, v in changes.items()},
                after={k: v["new"] for k, v in changes.items()},
                request=request,
            )

        return business

    @staticmethod
    @transaction.atomic
    def update_slug(
        *,
        business: BusinessAccount,
        new_slug: str,
        actor: "User",
        request=None,
    ) -> BusinessAccount:
        """
        Change a business's slug with redirect tracking.

        The old slug is stored in history and can never be reused.

        Args:
            business: The business to update.
            new_slug: The new slug.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            BusinessAccount: Updated business.

        Raises:
            ConflictError: If new slug is already in use.
            ValidationError: If trying to set same slug.
        """
        old_slug = business.slug

        if old_slug == new_slug:
            raise ValidationError(
                message="New slug is the same as current slug",
                field="slug",
            )

        # Validate new slug availability
        BusinessAccountService._validate_slug(
            slug=new_slug, exclude_business_id=business.id
        )

        # Store old slug in history
        BusinessSlugHistory.objects.create(
            business=business,
            old_slug=old_slug,
        )

        # Update business slug
        business.slug = new_slug
        business.updated_by = actor
        business.save(update_fields=["slug", "updated_by", "updated_at"])

        logger.info(
            "business.slug_changed",
            business_id=str(business.id),
            old_slug=old_slug,
            new_slug=new_slug,
        )

        AuditService.log_change(
            action=AuditLog.Action.BUSINESS_SLUG_CHANGED,
            actor=actor,
            resource=business,
            before={"slug": old_slug},
            after={"slug": new_slug},
            request=request,
        )

        return business

    @staticmethod
    @transaction.atomic
    def suspend(
        *,
        business: BusinessAccount,
        reason: str,
        actor: "User",
        request=None,
    ) -> BusinessAccount:
        """
        Suspend a business (platform action).

        Args:
            business: The business to suspend.
            reason: Reason for suspension.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            BusinessAccount: Updated business.
        """
        old_status = business.status
        business.status = BusinessStatus.SUSPENDED
        business.updated_by = actor
        business.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info(
            "business.suspended",
            business_id=str(business.id),
            reason=reason,
        )

        AuditService.log(
            action=AuditLog.Action.BUSINESS_SUSPENDED,
            actor=actor,
            resource=business,
            resource_type="BusinessAccount",
            resource_id=business.id,
            request=request,
            details={"reason": reason, "old_status": old_status},
        )

        return business

    @staticmethod
    @transaction.atomic
    def reactivate(
        *,
        business: BusinessAccount,
        actor: "User",
        request=None,
    ) -> BusinessAccount:
        """
        Reactivate a suspended business.

        Args:
            business: The business to reactivate.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            BusinessAccount: Updated business.

        Raises:
            ValidationError: If business is not suspended.
        """
        if business.status != BusinessStatus.SUSPENDED:
            raise ValidationError(
                message="Business is not suspended",
                field="status",
            )

        business.status = BusinessStatus.ACTIVE
        business.updated_by = actor
        business.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info(
            "business.reactivated",
            business_id=str(business.id),
        )

        AuditService.log(
            action=AuditLog.Action.BUSINESS_REACTIVATED,
            actor=actor,
            resource=business,
            resource_type="BusinessAccount",
            resource_id=business.id,
            request=request,
        )

        return business

    @staticmethod
    @transaction.atomic
    def archive(
        *,
        business: BusinessAccount,
        actor: "User",
        request=None,
    ) -> BusinessAccount:
        """
        Archive a business (owner action).

        Args:
            business: The business to archive.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            BusinessAccount: Updated business.
        """
        business.status = BusinessStatus.ARCHIVED
        business.updated_by = actor
        business.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info(
            "business.archived",
            business_id=str(business.id),
        )

        AuditService.log(
            action=AuditLog.Action.BUSINESS_ARCHIVED,
            actor=actor,
            resource=business,
            resource_type="BusinessAccount",
            resource_id=business.id,
            request=request,
        )

        return business

    @staticmethod
    @transaction.atomic
    def soft_delete(
        *,
        business: BusinessAccount,
        actor: "User",
        request=None,
    ) -> BusinessAccount:
        """
        Soft delete a business.

        Args:
            business: The business to delete.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            BusinessAccount: Deleted business.
        """
        business.soft_delete(user=actor)
        business.status = BusinessStatus.DELETED
        business.updated_by = actor
        business.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info(
            "business.deleted",
            business_id=str(business.id),
        )

        AuditService.log(
            action=AuditLog.Action.BUSINESS_DELETED,
            actor=actor,
            resource=business,
            resource_type="BusinessAccount",
            resource_id=business.id,
            request=request,
        )

        return business

    @staticmethod
    @transaction.atomic
    def update_verification_status(
        *,
        business: BusinessAccount,
        status: str,
        actor: "User",
        request=None,
    ) -> BusinessAccount:
        """
        Update business verification status.

        Called by Transaction system's VerificationOutcomeHandler.

        Args:
            business: The business to update.
            status: New verification status.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            BusinessAccount: Updated business.
        """
        old_status = business.verification_status
        business.verification_status = status
        business.updated_by = actor

        update_fields = ["verification_status", "updated_by", "updated_at"]

        if status == VerificationStatus.VERIFIED:
            business.verified_at = timezone.now()
            business.verified_by = actor
            update_fields.extend(["verified_at", "verified_by"])

            AuditService.log(
                action=AuditLog.Action.VERIFICATION_APPROVED,
                actor=actor,
                resource=business,
                resource_type="BusinessAccount",
                resource_id=business.id,
                request=request,
                details={"old_status": old_status},
            )
        elif status == VerificationStatus.REJECTED:
            AuditService.log(
                action=AuditLog.Action.VERIFICATION_REJECTED,
                actor=actor,
                resource=business,
                resource_type="BusinessAccount",
                resource_id=business.id,
                request=request,
                details={"old_status": old_status},
            )

        business.save(update_fields=update_fields)

        logger.info(
            "business.verification_status_updated",
            business_id=str(business.id),
            old_status=old_status,
            new_status=status,
        )

        return business


class BusinessProfileService:
    """Service for BusinessProfile operations."""

    @staticmethod
    @transaction.atomic
    def update(
        *,
        profile: BusinessProfile,
        display_name: str | None = None,
        tagline: str | None = None,
        description: str | None = None,
        logo=None,
        cover_image=None,
        website: str | None = None,
        contact_email: str | None = None,
        contact_phone: str | None = None,
        industry: str | None = None,
        company_size: str | None = None,
        founded_year: int | None = None,
        social_links: dict | None = None,
        tags: list | None = None,
        custom_fields: dict | None = None,
        is_public: bool | None = None,
        actor: "User",
        request=None,
    ) -> BusinessProfile:
        """
        Update a business profile.

        Args:
            profile: The profile to update.
            display_name: Display name.
            tagline: Tagline.
            description: Description.
            logo: Logo image.
            cover_image: Cover image.
            website: Website URL.
            contact_email: Contact email.
            contact_phone: Contact phone.
            industry: Industry.
            company_size: Company size.
            founded_year: Founded year.
            social_links: Social links.
            tags: Discovery tags.
            custom_fields: Custom fields (Form Builder).
            is_public: Whether profile is public.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            BusinessProfile: Updated profile.
        """
        changes = {}
        update_fields = ["updated_at"]

        if display_name is not None:
            changes["display_name"] = {"old": profile.display_name, "new": display_name}
            profile.display_name = display_name
            update_fields.append("display_name")

        if tagline is not None:
            changes["tagline"] = {"old": profile.tagline, "new": tagline}
            profile.tagline = tagline
            update_fields.append("tagline")

        if description is not None:
            changes["description"] = {"old": profile.description, "new": description}
            profile.description = description
            update_fields.append("description")

        if logo is not None:
            profile.logo = logo
            update_fields.append("logo")

        if cover_image is not None:
            profile.cover_image = cover_image
            update_fields.append("cover_image")

        if website is not None:
            changes["website"] = {"old": profile.website, "new": website}
            profile.website = website
            update_fields.append("website")

        if contact_email is not None:
            changes["contact_email"] = {
                "old": profile.contact_email,
                "new": contact_email,
            }
            profile.contact_email = contact_email
            update_fields.append("contact_email")

        if contact_phone is not None:
            changes["contact_phone"] = {
                "old": profile.contact_phone,
                "new": contact_phone,
            }
            profile.contact_phone = contact_phone
            update_fields.append("contact_phone")

        if industry is not None:
            changes["industry"] = {"old": profile.industry, "new": industry}
            profile.industry = industry
            update_fields.append("industry")

        if company_size is not None:
            changes["company_size"] = {"old": profile.company_size, "new": company_size}
            profile.company_size = company_size
            update_fields.append("company_size")

        if founded_year is not None:
            changes["founded_year"] = {"old": profile.founded_year, "new": founded_year}
            profile.founded_year = founded_year
            update_fields.append("founded_year")

        if social_links is not None:
            changes["social_links"] = {"old": profile.social_links, "new": social_links}
            profile.social_links = social_links
            update_fields.append("social_links")

        if tags is not None:
            changes["tags"] = {"old": profile.tags, "new": tags}
            profile.tags = tags
            update_fields.append("tags")

        if custom_fields is not None:
            changes["custom_fields"] = {
                "old": profile.custom_fields,
                "new": custom_fields,
            }
            profile.custom_fields = custom_fields
            update_fields.append("custom_fields")

        if is_public is not None:
            changes["is_public"] = {"old": profile.is_public, "new": is_public}
            profile.is_public = is_public
            update_fields.append("is_public")

        profile.save(update_fields=update_fields)

        # Update business's updated_by
        profile.business.updated_by = actor
        profile.business.save(update_fields=["updated_by", "updated_at"])

        if changes:
            logger.info(
                "business.profile_updated",
                business_id=str(profile.business_id),
                changed_fields=list(changes.keys()),
            )

            AuditService.log(
                action=AuditLog.Action.BUSINESS_PROFILE_UPDATED,
                actor=actor,
                resource=profile,
                resource_type="BusinessProfile",
                resource_id=profile.business_id,
                request=request,
                changes=changes,
            )

        return profile
