# apps/organization/platform/services.py
"""
Platform Services - Business logic for platform operations.

All write operations go through services. Services use keyword-only arguments
for clarity and to prevent positional argument errors.
"""

from typing import Any

from django.db import transaction

from apps.core.exceptions import ConflictError
from apps.core.observability import AuditLog, AuditService, get_logger
from apps.organization.platform.models import PlatformAccount, PlatformProfile
from apps.organization.platform.selectors import PlatformAccountSelector

logger = get_logger(__name__)


class PlatformAccountService:
    """Service for PlatformAccount operations."""

    @staticmethod
    @transaction.atomic
    def configure(
        *,
        name: str,
        settings: dict | None = None,
        actor,
        request=None,
    ) -> PlatformAccount:
        """
        Initial platform configuration (one-time setup).

        Args:
            name: Platform name for the profile.
            settings: Optional platform-wide settings.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            PlatformAccount: The configured platform account.

        Raises:
            ConflictError: If platform is already configured.
        """
        # Check if already configured
        if PlatformAccountSelector.exists():
            platform = PlatformAccountSelector.get()
            if platform.is_configured:
                raise ConflictError(
                    message="Platform is already configured",
                    resource="PlatformAccount",
                    conflict_type="already_configured",
                )

        # Create or get the singleton
        platform, created = PlatformAccount.objects.get_or_create(
            singleton_key=1,
            defaults={
                "is_configured": True,
                "settings": settings or {},
                "created_by": actor,
                "updated_by": actor,
            },
        )

        if not created:
            platform.is_configured = True
            platform.settings = settings or {}
            platform.updated_by = actor
            platform.save()

        # Create or update profile
        PlatformProfile.objects.update_or_create(
            platform=platform,
            defaults={"name": name},
        )

        logger.info(
            "platform.configured",
            platform_id=str(platform.id),
            actor_id=str(actor.id) if actor else None,
        )

        AuditService.log(
            action=AuditLog.Action.PLATFORM_CONFIGURED,
            actor=actor,
            resource=platform,
            resource_type="PlatformAccount",
            resource_id=platform.id,
            request=request,
            details={"name": name},
        )

        # RBAC Integration: Create platform predefined roles
        # NOTE: This creates the role structure, but does NOT create memberships.
        # Platform memberships should be created separately via a management command
        # or through the Transaction system when inviting users to the platform.
        from apps.core.constants import AccountType
        from apps.rbac.models import Role
        from apps.rbac.services import RBACService

        # Only initialize if roles don't exist yet
        if not Role.objects.filter(
            account_type=AccountType.PLATFORM, account_id=platform.id
        ).exists():
            RBACService.initialize_platform_account(platform_id=platform.id)

        return platform

    @staticmethod
    @transaction.atomic
    def update_settings(
        *,
        settings: dict[str, Any] | None = None,
        open_member_request: bool | None = None,
        actor,
        request=None,
    ) -> PlatformAccount:
        """
        Update platform-wide settings.

        Args:
            settings: New settings to merge with existing.
            open_member_request: Whether to accept membership requests.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            PlatformAccount: Updated platform account.
        """
        platform = PlatformAccountSelector.get()
        update_fields = ["updated_by", "updated_at"]
        old_settings = platform.settings.copy()

        if settings is not None:
            platform.settings.update(settings)
            update_fields.append("settings")

        if (
            open_member_request is not None
            and open_member_request != platform.open_member_request
        ):
            platform.open_member_request = open_member_request
            update_fields.append("open_member_request")

        platform.updated_by = actor
        platform.save(update_fields=update_fields)

        logger.info(
            "platform.settings_updated",
            platform_id=str(platform.id),
            actor_id=str(actor.id) if actor else None,
        )

        AuditService.log_change(
            action=AuditLog.Action.PLATFORM_SETTINGS_UPDATED,
            actor=actor,
            resource=platform,
            before={"settings": old_settings},
            after={"settings": platform.settings},
            request=request,
        )

        return platform


class PlatformProfileService:
    """Service for PlatformProfile operations."""

    @staticmethod
    @transaction.atomic
    def update(
        *,
        name: str | None = None,
        tagline: str | None = None,
        description: str | None = None,
        logo=None,
        favicon=None,
        primary_color: str | None = None,
        secondary_color: str | None = None,
        contact_email: str | None = None,
        contact_phone: str | None = None,
        address: str | None = None,
        social_links: dict | None = None,
        actor,
        request=None,
    ) -> PlatformProfile:
        """
        Update platform profile.

        Args:
            name: Platform name.
            tagline: Platform tagline.
            description: Platform description.
            logo: Logo image file.
            favicon: Favicon image file.
            primary_color: Primary brand color (hex).
            secondary_color: Secondary brand color (hex).
            contact_email: Contact email address.
            contact_phone: Contact phone number.
            address: Physical address.
            social_links: Social media links dict.
            actor: User performing the action.
            request: HTTP request for audit context.

        Returns:
            PlatformProfile: Updated profile.
        """
        platform = PlatformAccountSelector.get()
        profile = platform.profile

        # Track changes
        changes = {}

        # Update only provided fields
        update_fields = ["updated_at"]

        if name is not None:
            changes["name"] = {"old": profile.name, "new": name}
            profile.name = name
            update_fields.append("name")

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

        if favicon is not None:
            profile.favicon = favicon
            update_fields.append("favicon")

        if primary_color is not None:
            changes["primary_color"] = {
                "old": profile.primary_color,
                "new": primary_color,
            }
            profile.primary_color = primary_color
            update_fields.append("primary_color")

        if secondary_color is not None:
            changes["secondary_color"] = {
                "old": profile.secondary_color,
                "new": secondary_color,
            }
            profile.secondary_color = secondary_color
            update_fields.append("secondary_color")

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

        if address is not None:
            changes["address"] = {"old": profile.address, "new": address}
            profile.address = address
            update_fields.append("address")

        if social_links is not None:
            changes["social_links"] = {"old": profile.social_links, "new": social_links}
            profile.social_links = social_links
            update_fields.append("social_links")

        profile.save(update_fields=update_fields)

        # Update platform's updated_by
        platform.updated_by = actor
        platform.save(update_fields=["updated_by", "updated_at"])

        logger.info(
            "platform.profile_updated",
            platform_id=str(platform.id),
            actor_id=str(actor.id) if actor else None,
            changed_fields=list(changes.keys()),
        )

        AuditService.log(
            action=AuditLog.Action.PLATFORM_PROFILE_UPDATED,
            actor=actor,
            resource=profile,
            resource_type="PlatformProfile",
            resource_id=platform.id,
            request=request,
            changes=changes,
        )

        return profile
