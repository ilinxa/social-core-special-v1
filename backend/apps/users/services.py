"""
User Services
=============
Business logic for user operations.

All write operations to the User and UserProfile models MUST go through
this service layer. This ensures consistent validation, logging, and
business rule enforcement.

Governance Rules:
    - No other system writes to users table directly
    - All user mutations MUST go through UserService
    - Auth system must NOT mutate User except via UserService
    - Direct User.objects.update() is FORBIDDEN outside of UserService

Usage:
    from apps.users.services import UserService

    # Create user
    user = UserService.create_user(
        email='user@example.com',
        password='secure_password'
    )

    # Update profile
    profile = UserService.update_profile(
        user=user,
        first_name='John',
        last_name='Doe'
    )
"""

import re

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.core.exceptions import ConflictError, ValidationError

# Observability
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditLog, AuditService
from apps.core.utils.password import validate_password_strength
from apps.users.models import User, UserProfile

logger = get_logger(__name__)

# Reserved usernames that cannot be claimed by users.
RESERVED_USERNAMES = frozenset(
    {
        # Platform routes
        "admin",
        "administrator",
        "support",
        "help",
        "about",
        "contact",
        "settings",
        "profile",
        "login",
        "logout",
        "register",
        "signup",
        "signin",
        "home",
        "explore",
        "search",
        "dashboard",
        # System / brand
        "system",
        "moderator",
        "staff",
        "official",
        "root",
        "superuser",
        "api",
        "platform",
        "business",
        "bconsole",
        "pconsole",
        # Common reserved
        "null",
        "undefined",
        "anonymous",
        "unknown",
        "deleted",
        "removed",
        "everyone",
        "nobody",
        "noreply",
        "postmaster",
        "webmaster",
    }
)


class UserService:
    """
    Business logic for user operations.

    All methods are static to emphasize that this is a stateless service.
    Each method handles a specific user-related operation with proper
    validation, logging, and transaction management.
    """

    @staticmethod
    @transaction.atomic
    def create_user(
        *,
        email: str,
        password: str,
        username: str | None = None,
        referred_by_id: int | None = None,
        request: HttpRequest | None = None,
    ) -> User:
        """
        Create a new user with profile.

        This is the primary entry point for user registration. It:
            - Validates email uniqueness (case-insensitive)
            - Validates username uniqueness (if provided)
            - Validates password strength
            - Creates user with provided or auto-generated username
            - Profile is created automatically via signal

        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            username: Optional username (auto-generated if not provided)
            referred_by_id: Optional referrer user ID
            request: HTTP request for audit context (optional)

        Returns:
            Created User instance

        Raises:
            ConflictError: If email or username already exists
            ValidationError: If password doesn't meet requirements
        """
        # Normalize email
        email = email.strip().lower()

        # Validate email uniqueness
        if User.objects.filter(email__iexact=email).exists():
            raise ConflictError(
                message="A user with this email already exists",
                resource="User",
                conflict_type="duplicate",
            )

        # Validate username uniqueness (if provided)
        if username:
            username = username.strip().lower()
            if User.objects.filter(username__iexact=username).exists():
                raise ConflictError(
                    message="This username is already taken",
                    resource="User",
                    conflict_type="duplicate",
                )

        # Validate password strength
        password_errors = validate_password_strength(password)
        if password_errors:
            raise ValidationError(message=password_errors[0], field="password")

        # Get referrer if provided
        referred_by = None
        if referred_by_id:
            referred_by = User.objects.filter(id=referred_by_id).first()

        # Build extra fields
        extra_fields = {}
        if username:
            extra_fields["username"] = username

        # Create user (profile created via signal)
        user = User.objects.create_user(
            email=email,
            password=password,
            referred_by=referred_by,
            **extra_fields,
        )

        logger.info(
            "user.created",
            user_id=str(user.id),
            referred_by=str(referred_by_id) if referred_by_id else None,
        )

        # Audit: User created
        AuditService.log(
            action=AuditLog.Action.USER_CREATED,
            actor=user,
            resource=user,
            request=request,
            details={
                "referred_by": str(referred_by_id) if referred_by_id else None,
            },
        )

        return user

    @staticmethod
    def verify_email(*, user: User, request: HttpRequest | None = None) -> User:
        """
        Mark user's email as verified.

        Called by Auth system after successful email verification.
        Sets is_verified=True and updates the timestamp.

        Args:
            user: User instance to verify
            request: HTTP request for audit context (optional)

        Returns:
            Updated User instance
        """
        if user.is_verified:
            logger.debug(
                "user.already_verified",
                user_id=str(user.id),
            )
            return user

        user.is_verified = True
        user.save(update_fields=["is_verified", "updated_at"])

        logger.info(
            "user.verified",
            user_id=str(user.id),
        )
        AuditService.log(
            action=AuditLog.Action.EMAIL_VERIFIED,
            actor=user,
            resource=user,
            request=request,
        )

        return user

    @staticmethod
    def unverify_email(*, user: User, request: HttpRequest | None = None) -> User:
        """
        Mark user's email as unverified.

        Used when user changes their email address - they must re-verify.

        Args:
            user: User instance to unverify
            request: HTTP request for audit context (optional)

        Returns:
            Updated User instance
        """
        user.is_verified = False
        user.save(update_fields=["is_verified", "updated_at"])

        logger.info(
            "user.unverified",
            user_id=str(user.id),
        )
        AuditService.log(
            action=AuditLog.Action.EMAIL_UNVERIFIED,
            actor=user,
            resource=user,
            request=request,
        )

        return user

    @staticmethod
    @transaction.atomic
    def update_profile(
        *,
        user: User,
        first_name: str | None = None,
        last_name: str | None = None,
        phone: str | None = None,
        timezone: str | None = None,
        language: str | None = None,
        bio: str | None = None,
        country: str | None = None,
        city: str | None = None,
        tags: list | None = None,
        is_public: bool | None = None,
        request: HttpRequest | None = None,
    ) -> UserProfile:
        """
        Update user profile fields.

        Only updates fields that are explicitly passed (not None).
        Empty string is a valid value and will be saved.

        Args:
            user: User whose profile to update
            first_name: New first name
            last_name: New last name
            phone: New phone number
            timezone: New timezone (e.g., 'America/New_York')
            language: New language code (e.g., 'en', 'fr')
            bio: Short bio text
            country: ISO 3166-1 alpha-2 country code
            city: City name
            tags: List of tag strings
            request: HTTP request for audit context (optional)

        Returns:
            Updated UserProfile instance
        """
        profile = user.profile
        updated_fields = []
        changes = {}

        if first_name is not None:
            if profile.first_name != first_name.strip():
                changes["first_name"] = {
                    "old": profile.first_name,
                    "new": first_name.strip(),
                }
            profile.first_name = first_name.strip()
            updated_fields.append("first_name")

        if last_name is not None:
            if profile.last_name != last_name.strip():
                changes["last_name"] = {
                    "old": profile.last_name,
                    "new": last_name.strip(),
                }
            profile.last_name = last_name.strip()
            updated_fields.append("last_name")

        if phone is not None:
            if profile.phone != phone.strip():
                changes["phone"] = {"old": profile.phone, "new": phone.strip()}
            profile.phone = phone.strip()
            updated_fields.append("phone")

        if timezone is not None:
            if profile.timezone != timezone:
                changes["timezone"] = {"old": profile.timezone, "new": timezone}
            profile.timezone = timezone
            updated_fields.append("timezone")

        if language is not None:
            if profile.language != language:
                changes["language"] = {"old": profile.language, "new": language}
            profile.language = language
            updated_fields.append("language")

        if bio is not None:
            if profile.bio != bio:
                changes["bio"] = {"old": profile.bio, "new": bio}
            profile.bio = bio
            updated_fields.append("bio")

        if country is not None:
            if profile.country != country:
                changes["country"] = {"old": profile.country, "new": country}
            profile.country = country
            updated_fields.append("country")

        if city is not None:
            if profile.city != city:
                changes["city"] = {"old": profile.city, "new": city}
            profile.city = city
            updated_fields.append("city")

        if tags is not None:
            if profile.tags != tags:
                changes["tags"] = {"old": profile.tags, "new": tags}
            profile.tags = tags
            updated_fields.append("tags")

        if is_public is not None:
            if profile.is_public != is_public:
                changes["is_public"] = {"old": profile.is_public, "new": is_public}
            profile.is_public = is_public
            updated_fields.append("is_public")

        if updated_fields:
            updated_fields.append("updated_at")
            profile.save(update_fields=updated_fields)

            logger.info(
                "profile.updated",
                user_id=str(user.id),
                fields=updated_fields,
            )

            # Audit: Profile updated (only if changes were made)
            if changes:
                AuditService.log(
                    action=AuditLog.Action.PROFILE_UPDATED,
                    actor=user,
                    resource=profile,
                    request=request,
                    changes=changes,
                )

        return profile

    @staticmethod
    def update_avatar(
        *, user: User, avatar, request: HttpRequest | None = None
    ) -> UserProfile:
        """
        Update user's avatar image.

        Args:
            user: User whose avatar to update
            avatar: ImageFile instance
            request: HTTP request for audit context (optional)

        Returns:
            Updated UserProfile instance
        """
        profile = user.profile

        # Delete old avatar if exists
        if profile.avatar:
            profile.avatar.delete(save=False)

        profile.avatar = avatar
        profile.save(update_fields=["avatar", "updated_at"])

        logger.info(
            "avatar.updated",
            user_id=str(user.id),
        )

        # Audit: Avatar changed
        AuditService.log(
            action=AuditLog.Action.AVATAR_CHANGED,
            actor=user,
            resource=profile,
            request=request,
            details={
                "filename": avatar.name if hasattr(avatar, "name") else None,
                "size": avatar.size if hasattr(avatar, "size") else None,
            },
        )

        return profile

    @staticmethod
    def remove_avatar(*, user: User, request: HttpRequest | None = None) -> UserProfile:
        """
        Remove user's avatar image.

        Args:
            user: User whose avatar to remove
            request: HTTP request for audit context (optional)

        Returns:
            Updated UserProfile instance
        """
        profile = user.profile

        if profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None
            profile.save(update_fields=["avatar", "updated_at"])

            logger.info(
                "avatar.removed",
                user_id=str(user.id),
            )

            # Audit: Avatar deleted
            AuditService.log(
                action=AuditLog.Action.AVATAR_DELETED,
                actor=user,
                resource=profile,
                request=request,
            )

        return profile

    @staticmethod
    def update_cover_image(
        *, user: User, cover_image, request: HttpRequest | None = None
    ) -> UserProfile:
        """Update user's cover image."""
        profile = user.profile

        if profile.cover_image:
            profile.cover_image.delete(save=False)

        profile.cover_image = cover_image
        profile.save(update_fields=["cover_image", "updated_at"])

        logger.info("cover_image.updated", user_id=str(user.id))

        AuditService.log(
            action=AuditLog.Action.COVER_IMAGE_CHANGED,
            actor=user,
            resource=profile,
            request=request,
            details={
                "filename": cover_image.name if hasattr(cover_image, "name") else None,
                "size": cover_image.size if hasattr(cover_image, "size") else None,
            },
        )

        return profile

    @staticmethod
    def remove_cover_image(
        *, user: User, request: HttpRequest | None = None
    ) -> UserProfile:
        """Remove user's cover image."""
        profile = user.profile

        if profile.cover_image:
            profile.cover_image.delete(save=False)
            profile.cover_image = None
            profile.save(update_fields=["cover_image", "updated_at"])

            logger.info("cover_image.removed", user_id=str(user.id))

            AuditService.log(
                action=AuditLog.Action.COVER_IMAGE_DELETED,
                actor=user,
                resource=profile,
                request=request,
            )

        return profile

    @staticmethod
    def deactivate_user(*, user: User, request: HttpRequest | None = None) -> User:
        """
        Deactivate user account (soft delete).

        Deactivated users:
            - Cannot log in
            - Are automatically unverified (business rule)
            - Retain their data for potential reactivation

        Args:
            user: User to deactivate
            request: HTTP request for audit context (optional)

        Returns:
            Updated User instance
        """
        user.is_active = False
        # NOTE: Business rule enforcement - verified users become unverified when deactivated.
        # This replaces the removed DB-level CheckConstraint 'verified_only_if_active'
        # which was removed because it prevented clean reactivation flows.
        user.is_verified = False
        user.save(update_fields=["is_active", "is_verified", "updated_at"])

        logger.info(
            "user.deactivated",
            user_id=str(user.id),
        )

        # Audit: User deactivated
        AuditService.log(
            action=AuditLog.Action.USER_DEACTIVATED,
            actor=user,
            resource=user,
            request=request,
        )

        # Revoke all sessions and tokens
        from apps.auth.services import AuthService

        AuthService.logout_all(user=user, reason="account_deactivated", request=request)

        return user

    @staticmethod
    def reactivate_user(*, user: User, request: HttpRequest | None = None) -> User:
        """
        Reactivate deactivated user account.

        Note: User will need to re-verify their email after reactivation.

        Args:
            user: User to reactivate
            request: HTTP request for audit context (optional)

        Returns:
            Updated User instance
        """
        user.is_active = True
        # is_verified stays False - user must re-verify
        user.save(update_fields=["is_active", "updated_at"])

        logger.info(
            "user.reactivated",
            user_id=str(user.id),
        )

        # Audit: User reactivated
        AuditService.log(
            action=AuditLog.Action.USER_REACTIVATED,
            actor=user,
            resource=user,
            request=request,
        )

        return user

    @staticmethod
    @transaction.atomic
    def change_username(
        *, user: User, new_username: str, request: HttpRequest | None = None
    ) -> User:
        """
        Change user's username.

        Username rules:
            - 5-30 characters
            - Alphanumeric and underscores only
            - Must be unique (case-insensitive)
            - Cannot be a reserved name

        Args:
            user: User instance
            new_username: New username (will be lowercased)
            request: HTTP request for audit context (optional)

        Returns:
            Updated User instance

        Raises:
            ConflictError: If username already taken
            ValidationError: If username format invalid
        """
        new_username = new_username.strip()
        old_username = user.username

        # Validate format
        if not re.match(r"^[a-zA-Z0-9_]{5,30}$", new_username):
            raise ValidationError(
                message="Username must be 5-30 alphanumeric characters or underscores",
                field="username",
            )

        # Check reserved names
        if new_username.lower() in RESERVED_USERNAMES:
            raise ValidationError(message="This username is reserved", field="username")

        # Check uniqueness (case-insensitive)
        if (
            User.objects.filter(username__iexact=new_username)
            .exclude(id=user.id)
            .exists()
        ):
            raise ConflictError(
                message="This username is already taken",
                resource="User",
                conflict_type="duplicate",
            )

        user.username = new_username.lower()
        user.save(update_fields=["username", "updated_at"])

        logger.info(
            "username.changed",
            user_id=str(user.id),
            old_username=old_username,
            new_username=user.username,
        )

        # Audit: User updated (username change)
        AuditService.log(
            action=AuditLog.Action.USER_UPDATED,
            actor=user,
            resource=user,
            request=request,
            changes={"username": {"old": old_username, "new": user.username}},
        )

        return user

    @staticmethod
    def update_last_login(*, user: User) -> User:
        """
        Update user's last login timestamp.

        Called by Auth system on successful login.

        Args:
            user: User who logged in

        Returns:
            Updated User instance
        """
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        return user

    @staticmethod
    @transaction.atomic
    def change_email(
        *, user: User, new_email: str, request: HttpRequest | None = None
    ) -> User:
        """
        Change user's email address.

        The new email must be unique. User will be marked as unverified
        and must complete email verification for the new address.

        Args:
            user: User instance
            new_email: New email address
            request: HTTP request for audit context (optional)

        Returns:
            Updated User instance

        Raises:
            ConflictError: If email already exists
        """
        new_email = new_email.strip().lower()
        old_email = user.email

        # Validate uniqueness
        if User.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
            raise ConflictError(
                message="A user with this email already exists",
                resource="User",
                conflict_type="duplicate",
            )

        user.email = new_email
        user.is_verified = False  # Must re-verify new email
        user.save(update_fields=["email", "is_verified", "updated_at"])

        logger.info(
            "email.changed",
            user_id=str(user.id),
            requires_verification=True,
        )

        # Audit: User updated (email change)
        AuditService.log(
            action=AuditLog.Action.USER_UPDATED,
            actor=user,
            resource=user,
            request=request,
            changes={"email": {"old": old_email, "new": new_email}},
            details={"requires_verification": True},
        )

        return user
