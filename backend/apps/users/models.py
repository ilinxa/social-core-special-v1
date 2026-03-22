"""
User Models
===========
Custom user model and user profile for email-based authentication.

Models:
    - User: Core user account with email as the primary identifier
    - UserProfile: Extended user information (name, avatar, preferences)

The User model:
    - Uses email as the unique identifier (not username)
    - Has auto-generated unique username for public display
    - Includes referral tracking
    - Integrates with Django's permission system

Design Decisions:
    - User contains auth-related fields only
    - Profile contains personal/display information
    - Profile is auto-created via signal when User is created
"""

import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.postgres.indexes import GinIndex
from django.db import models

from apps.core.models import TimeStampedModel
from apps.users.managers import CustomUserManager


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    """
    Custom User model using email as the unique identifier.

    Inherits from:
        - AbstractBaseUser: Core auth functionality (password hashing, etc.)
        - PermissionsMixin: Permission system (is_superuser, groups, permissions)
        - TimeStampedModel: created_at, updated_at

    Fields:
        email: Primary identifier for authentication
        username: Public identifier (auto-generated, changeable)
        is_active: Can the user log in?
        is_verified: Has the email been verified?
        is_staff: Can access admin site?
        is_superuser: Has all permissions (inherited)
        referred_by: User who referred this user
        last_login: Last successful login (inherited)
        date_joined: Account creation timestamp

    Note:
        Password field is inherited from AbstractBaseUser.
    """

    # Primary key (UUID for consistency with BusinessAccount and PlatformAccount)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Authentication field (login identifier)
    email = models.EmailField(
        unique=True,
        db_index=True,
        max_length=255,
        error_messages={
            "unique": "A user with this email already exists.",
        },
    )

    # Public identifier (auto-generated, user-changeable)
    username = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
        help_text="Unique public identifier. Auto-generated on creation, changeable later.",
    )

    # Status flags
    is_active = models.BooleanField(
        default=True, help_text="Designates whether this user can log in."
    )
    is_verified = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Designates whether email has been verified.",
    )
    is_staff = models.BooleanField(
        default=False, help_text="Designates whether user can access admin site."
    )
    can_create_business = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Designates whether user has been approved to create business accounts.",
    )

    # Account lockout (progressive lockout after failed login attempts)
    failed_login_attempts = models.PositiveSmallIntegerField(
        default=0, help_text="Number of consecutive failed login attempts."
    )
    locked_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Account locked until this time due to too many failed login attempts.",
    )

    # is_superuser is inherited from PermissionsMixin

    # Referral tracking
    referred_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals",
        help_text="User who referred this user.",
    )

    # Timestamps
    # last_login is inherited from AbstractBaseUser
    date_joined = models.DateTimeField(
        auto_now_add=True, help_text="Account creation timestamp."
    )

    # AbstractBaseUser requirements
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []  # Email is already required as USERNAME_FIELD

    # Custom manager
    objects = CustomUserManager()

    class Meta:
        db_table = "users"
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["-date_joined"]
        indexes = [
            models.Index(fields=["email", "is_active"], name="users_email_active_idx"),
            models.Index(
                fields=["is_verified", "is_active"], name="users_verified_active_idx"
            ),
            models.Index(fields=["date_joined"], name="users_date_joined_idx"),
            models.Index(fields=["last_login"], name="users_last_login_idx"),
            models.Index(fields=["referred_by"], name="users_referred_by_idx"),
        ]
        constraints = [
            # Business rule: Cannot refer yourself
            models.CheckConstraint(
                check=~models.Q(id=models.F("referred_by_id")), name="no_self_referral"
            ),
        ]

    def __str__(self):
        return self.email

    def __repr__(self):
        return f"<User id={self.id} email={self.email}>"

    @property
    def is_complete(self):
        """
        Check if user has completed their profile.

        A complete profile means:
            - Email is verified
            - Profile exists
            - First name is set
        """
        return (
            self.is_verified
            and hasattr(self, "profile")
            and bool(self.profile.first_name)
        )

    def get_full_name(self):
        """
        Return the full name from profile, or email if no profile.

        Required by Django admin.
        """
        if hasattr(self, "profile"):
            return self.profile.full_name
        return self.email

    def get_short_name(self):
        """
        Return the short name from profile, or email prefix.

        Required by Django admin.
        """
        if hasattr(self, "profile"):
            return self.profile.display_name
        return self.email.split("@")[0]


class UserProfile(TimeStampedModel):
    """
    Extended user profile for non-authentication data.

    Created automatically when User is created (via signal).
    One-to-one relationship with User - uses User's PK as its own PK.

    Fields:
        user: Reference to User (OneToOne, also the primary key)
        first_name: User's first name
        last_name: User's last name
        phone: Phone number with country code
        avatar: Profile picture
        timezone: User's preferred timezone
        language: User's preferred language

    Properties:
        full_name: Combined first + last name, or email
        display_name: First name, or email prefix
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, primary_key=True, related_name="profile"
    )

    # Personal information
    first_name = models.CharField(
        max_length=150, blank=True, help_text="User's first name"
    )
    last_name = models.CharField(
        max_length=150, blank=True, help_text="User's last name"
    )

    # Contact information
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Phone number with country code (e.g., +1234567890)",
    )

    # Media
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/", blank=True, null=True, help_text="Profile picture"
    )
    cover_image = models.ImageField(
        upload_to="covers/%Y/%m/",
        blank=True,
        null=True,
        help_text="Profile cover photo",
    )

    # Preferences
    timezone = models.CharField(
        max_length=50,
        default="UTC",
        help_text="User's preferred timezone (e.g., 'America/New_York')",
    )
    language = models.CharField(
        max_length=10,
        default="en",
        help_text="User's preferred language code (e.g., 'en', 'fr')",
    )

    # Explore / Discovery fields
    bio = models.TextField(
        max_length=500,
        blank=True,
        default="",
        help_text="Short bio for profile discovery.",
    )
    country = models.CharField(
        max_length=2,
        blank=True,
        default="",
        db_index=True,
        help_text="ISO 3166-1 alpha-2 country code.",
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        default="",
        db_index=True,
        help_text="City name (validated against predefined city list).",
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="User tags for discovery (e.g., developer, designer).",
    )
    is_public = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this profile is publicly visible to other users.",
    )
    visibility_overrides = models.JSONField(
        default=dict,
        blank=True,
        help_text="Per-field visibility level overrides for T2 fields.",
    )

    class Meta:
        db_table = "user_profiles"
        verbose_name = "user profile"
        verbose_name_plural = "user profiles"
        indexes = [
            GinIndex(fields=["tags"], name="userprofile_tags_gin"),
        ]

    def __str__(self):
        return f"Profile: {self.user.email}"

    def __repr__(self):
        return f"<UserProfile user_id={self.user_id}>"

    @property
    def full_name(self):
        """
        Return full name or email if no name set.

        Returns:
            str: "First Last" or user's email
        """
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.user.email

    @property
    def display_name(self):
        """
        Return display name for UI.

        Returns:
            str: First + last name, first name only, or email prefix as fallback
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.first_name or self.user.email.split("@")[0]

    @property
    def has_avatar(self):
        """Check if user has uploaded an avatar."""
        return bool(self.avatar)

    @property
    def has_cover_image(self):
        """Check if user has uploaded a cover image."""
        return bool(self.cover_image)
