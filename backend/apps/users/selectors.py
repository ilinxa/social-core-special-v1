"""
User Selectors
==============
Read-only queries for users.

All read operations for User and UserProfile SHOULD go through this
selector layer. This ensures consistent query optimization and
separation of concerns.

Governance Rules:
    - All read queries MUST go through UserSelector
    - Other systems can import UserSelector for read operations
    - Direct User.objects.filter() is allowed only in UserSelector

Usage:
    from apps.users.selectors import UserSelector

    # Get user by ID (raises NotFound if not found)
    user = UserSelector.get_by_id(user_id=123)

    # Get user by email (returns None if not found)
    user = UserSelector.get_by_email_or_none(email='user@example.com')

    # Get active users
    users = UserSelector.get_active_users()
"""

from typing import Optional

from django.db.models import Count, QuerySet

from apps.core.exceptions import NotFound
from apps.users.models import User, UserProfile


class UserSelector:
    """
    Read-only queries for users.

    All methods are static to emphasize that this is a stateless service.
    Methods that can fail to find a user have two variants:
        - get_by_X: Raises NotFound if not found
        - get_by_X_or_none: Returns None if not found
    """

    # =========================================================================
    # SINGLE USER QUERIES
    # =========================================================================

    @staticmethod
    def get_by_id(*, user_id: int, with_profile: bool = False) -> User:
        """
        Get user by ID.

        Args:
            user_id: User's primary key
            with_profile: Include profile in query (reduces N+1)

        Returns:
            User instance

        Raises:
            NotFound: If user doesn't exist
        """
        queryset = User.objects.all()
        if with_profile:
            queryset = queryset.select_related('profile')

        user = queryset.filter(id=user_id).first()
        if not user:
            raise NotFound(resource='User', resource_id=user_id)

        return user

    @staticmethod
    def get_by_id_or_none(
        *,
        user_id: int,
        with_profile: bool = False
    ) -> Optional[User]:
        """
        Get user by ID, returns None if not found.

        Args:
            user_id: User's primary key
            with_profile: Include profile in query

        Returns:
            User instance or None
        """
        queryset = User.objects.all()
        if with_profile:
            queryset = queryset.select_related('profile')

        return queryset.filter(id=user_id).first()

    @staticmethod
    def get_by_email(*, email: str, with_profile: bool = False) -> User:
        """
        Get user by email (case-insensitive).

        Args:
            email: User's email address
            with_profile: Include profile in query

        Returns:
            User instance

        Raises:
            NotFound: If user doesn't exist
        """
        queryset = User.objects.all()
        if with_profile:
            queryset = queryset.select_related('profile')

        user = queryset.filter(email__iexact=email.strip()).first()
        if not user:
            raise NotFound(resource='User', resource_id=email)

        return user

    @staticmethod
    def get_by_email_or_none(
        *,
        email: str,
        with_profile: bool = False
    ) -> Optional[User]:
        """
        Get user by email, returns None if not found.

        Args:
            email: User's email address
            with_profile: Include profile in query

        Returns:
            User instance or None
        """
        queryset = User.objects.all()
        if with_profile:
            queryset = queryset.select_related('profile')

        return queryset.filter(email__iexact=email.strip()).first()

    @staticmethod
    def get_by_username(*, username: str, with_profile: bool = False) -> User:
        """
        Get user by username (case-insensitive).

        Args:
            username: User's username
            with_profile: Include profile in query

        Returns:
            User instance

        Raises:
            NotFound: If user doesn't exist
        """
        queryset = User.objects.all()
        if with_profile:
            queryset = queryset.select_related('profile')

        user = queryset.filter(username__iexact=username.strip()).first()
        if not user:
            raise NotFound(resource='User', resource_id=username)

        return user

    @staticmethod
    def get_by_username_or_none(
        *,
        username: str,
        with_profile: bool = False
    ) -> Optional[User]:
        """
        Get user by username, returns None if not found.

        Args:
            username: User's username
            with_profile: Include profile in query

        Returns:
            User instance or None
        """
        queryset = User.objects.all()
        if with_profile:
            queryset = queryset.select_related('profile')

        return queryset.filter(username__iexact=username.strip()).first()

    @staticmethod
    def get_active_by_email(*, email: str, with_profile: bool = False) -> User:
        """
        Get active user by email.

        Useful for login flows where inactive users should not authenticate.

        Args:
            email: User's email address
            with_profile: Include profile in query

        Returns:
            Active User instance

        Raises:
            NotFound: If user doesn't exist or is inactive
        """
        queryset = User.objects.active()
        if with_profile:
            queryset = queryset.with_profile()

        user = queryset.filter(email__iexact=email.strip()).first()
        if not user:
            raise NotFound(resource='User', resource_id=email)

        return user

    # =========================================================================
    # QUERYSET BUILDERS
    # =========================================================================

    @staticmethod
    def get_active_users() -> QuerySet[User]:
        """
        Get all active users.

        Returns:
            QuerySet of active users with profiles
        """
        return User.objects.active().with_profile()

    @staticmethod
    def get_verified_users() -> QuerySet[User]:
        """
        Get all verified users (active and email verified).

        Returns:
            QuerySet of verified users with profiles
        """
        return User.objects.verified().with_profile()

    @staticmethod
    def get_unverified_users() -> QuerySet[User]:
        """
        Get active users who haven't verified their email.

        Useful for sending reminder emails.

        Returns:
            QuerySet of unverified users
        """
        return User.objects.unverified()

    @staticmethod
    def get_staff_users() -> QuerySet[User]:
        """
        Get all staff users.

        Returns:
            QuerySet of staff users with profiles
        """
        return User.objects.staff().with_profile()

    # =========================================================================
    # REFERRAL QUERIES
    # =========================================================================

    @staticmethod
    def get_referrals(*, user: User) -> QuerySet[User]:
        """
        Get users referred by this user.

        Args:
            user: The referrer user

        Returns:
            QuerySet of referred users with profiles
        """
        return User.objects.filter(
            referred_by=user
        ).select_related('profile')

    @staticmethod
    def count_referrals(*, user: User) -> int:
        """
        Count users referred by this user.

        Args:
            user: The referrer user

        Returns:
            Number of referred users
        """
        return User.objects.filter(referred_by=user).count()

    @staticmethod
    def get_top_referrers(*, limit: int = 10) -> QuerySet[User]:
        """
        Get users with most referrals.

        Args:
            limit: Maximum number of users to return

        Returns:
            QuerySet of users ordered by referral count
        """
        return User.objects.annotate(
            referral_count=Count('referrals')
        ).filter(
            referral_count__gt=0
        ).order_by('-referral_count')[:limit]

    # =========================================================================
    # PROFILE QUERIES
    # =========================================================================

    @staticmethod
    def get_profile(*, user: User) -> UserProfile:
        """
        Get user's profile.

        Args:
            user: User instance

        Returns:
            UserProfile instance

        Raises:
            NotFound: If profile doesn't exist (should never happen)
        """
        try:
            return user.profile
        except UserProfile.DoesNotExist:
            raise NotFound(
                resource='UserProfile',
                resource_id=user.id
            )

    # =========================================================================
    # EXISTENCE CHECKS
    # =========================================================================

    @staticmethod
    def email_exists(*, email: str) -> bool:
        """
        Check if email is already registered.

        Args:
            email: Email to check (case-insensitive)

        Returns:
            True if email exists, False otherwise
        """
        return User.objects.filter(email__iexact=email.strip()).exists()

    @staticmethod
    def username_exists(*, username: str) -> bool:
        """
        Check if username is already taken.

        Args:
            username: Username to check (case-insensitive)

        Returns:
            True if username exists, False otherwise
        """
        return User.objects.filter(username__iexact=username.strip()).exists()
