"""
User Managers
=============
Custom manager and queryset for the User model.

The manager provides:
    - Email normalization and validation
    - Auto-generated unique usernames
    - Superuser creation with proper defaults

The queryset provides chainable filters for common queries.
"""

import secrets
import string
from django.contrib.auth.models import BaseUserManager
from django.db import models


class UserQuerySet(models.QuerySet):
    """
    Custom QuerySet for User model with common filters.

    Provides chainable query methods for filtering users
    by their status flags.

    Usage:
        User.objects.active().verified()
        User.objects.with_profile().filter(...)
    """

    def active(self):
        """Return only active users."""
        return self.filter(is_active=True)

    def inactive(self):
        """Return only inactive users."""
        return self.filter(is_active=False)

    def verified(self):
        """Return only verified and active users."""
        return self.filter(is_verified=True, is_active=True)
    # def verified(self):
    #     """Return only verified and active users."""
    #     return self.filter(is_verified=True)

    def unverified(self):
        """Return active users who haven't verified their email."""
        return self.filter(is_verified=False, is_active=True)

    # def unverified(self):
    #     """Return active users who haven't verified their email."""
    #     return self.filter(is_verified=False)

    def with_profile(self):
        """Include profile in query (reduces N+1 queries)."""
        return self.select_related('profile')

    def with_referrer(self):
        """Include referrer user in query."""
        return self.select_related('referred_by')

    def staff(self):
        """Return staff users only."""
        return self.filter(is_staff=True, is_active=True)


class CustomUserManager(BaseUserManager):
    """
    Custom manager for User model with email as the unique identifier.

    This manager replaces Django's default UserManager to support
    email-based authentication instead of username-based.

    Methods:
        create_user: Create a regular user
        create_superuser: Create a superuser with elevated permissions
        generate_unique_username: Generate a unique username

    Usage:
        User.objects.create_user(email='user@example.com', password='secret')
        User.objects.create_superuser(email='admin@example.com', password='secret')
    """

    def get_queryset(self):
        """Return custom QuerySet with helper methods."""
        return UserQuerySet(self.model, using=self._db)

    # Delegate QuerySet methods to the manager
    def active(self):
        """Return only active users."""
        return self.get_queryset().active()

    def inactive(self):
        """Return only inactive users."""
        return self.get_queryset().inactive()

    def verified(self):
        """Return only verified users."""
        return self.get_queryset().verified()

    def unverified(self):
        """Return unverified users."""
        return self.get_queryset().unverified()

    def with_profile(self):
        """Include profile in query."""
        return self.get_queryset().with_profile()

    def staff(self):
        """Return staff users."""
        return self.get_queryset().staff()

    @staticmethod
    def generate_unique_username():
        """
        Generate a unique username.

        Format: user_<8 random alphanumeric chars>
        Example: user_a1b2c3d4

        The username is guaranteed to be unique at generation time.
        Uses cryptographically secure random generation.

        Returns:
            str: A unique username like 'user_x7k9m2p4'
        """
        # Import here to avoid circular import
        from apps.users.models import User

        chars = string.ascii_lowercase + string.digits
        max_attempts = 100  # Prevent infinite loop in edge cases

        for _ in range(max_attempts):
            random_part = ''.join(secrets.choice(chars) for _ in range(8))
            username = f"user_{random_part}"

            if not User.objects.filter(username=username).exists():
                return username

        # Fallback: use longer random string if somehow all short ones taken
        random_part = ''.join(secrets.choice(chars) for _ in range(16))
        return f"user_{random_part}"

    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user.

        Args:
            email: User's email address (will be normalized and lowercased)
            password: Plain text password (will be hashed)
            **extra_fields: Additional fields for the User model

        Returns:
            User: The created user instance

        Raises:
            ValueError: If email is not provided
        """
        if not email:
            raise ValueError('Email is required')

        # Normalize and lowercase email
        email = self.normalize_email(email).lower()

        # Auto-generate username if not provided
        if 'username' not in extra_fields or not extra_fields.get('username'):
            extra_fields['username'] = self.generate_unique_username()

        # Create user instance
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser.

        Superusers are automatically:
            - Active (is_active=True)
            - Verified (is_verified=True)
            - Staff (is_staff=True)
            - Superuser (is_superuser=True)

        Args:
            email: Admin's email address
            password: Plain text password (will be hashed)
            **extra_fields: Additional fields for the User model

        Returns:
            User: The created superuser instance

        Raises:
            ValueError: If is_staff or is_superuser is explicitly False
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)
