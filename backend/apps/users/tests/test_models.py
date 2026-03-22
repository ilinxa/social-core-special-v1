# apps/users/tests/test_models.py
"""
Tests for User and UserProfile models.

Covers:
    - User model creation and validation
    - User model constraints
    - User model properties and methods
    - UserProfile model
    - Custom manager and queryset methods
    - Signal-based profile creation
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.users.models import UserProfile

User = get_user_model()


# =============================================================================
# USER MODEL TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserModel:
    """Tests for the User model."""

    def test_create_user_with_email(self, user_factory):
        """Can create user with email as identifier."""
        user = user_factory(email="test@example.com")

        assert user.email == "test@example.com"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_staff is False
        assert user.is_superuser is False

    def test_user_email_is_unique(self, user_factory):
        """Email must be unique (case-insensitive enforced at DB level)."""
        user_factory(email="unique@example.com")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                user_factory(email="unique@example.com")

    def test_user_username_is_unique(self, user_factory):
        """Username must be unique."""
        user_factory(username="testuser")

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                user_factory(username="testuser")

    def test_user_str_representation(self, user_factory):
        """String representation uses email."""
        user = user_factory(email="test@example.com")
        assert str(user) == "test@example.com"

    def test_user_repr(self, user_factory):
        """Repr includes id and email."""
        user = user_factory(email="test@example.com")
        assert f"<User id={user.id} email=test@example.com>" == repr(user)

    def test_user_check_password(self, user_factory):
        """Password is properly hashed and can be verified."""
        user = user_factory(password="mypassword123")
        assert user.check_password("mypassword123") is True
        assert user.check_password("wrongpassword") is False

    def test_user_date_joined_auto_set(self, user_factory):
        """Date joined is automatically set on creation."""
        user = user_factory()
        assert user.date_joined is not None

    def test_user_timestamps(self, user_factory):
        """User has created_at and updated_at from TimeStampedModel."""
        user = user_factory()
        assert user.created_at is not None
        assert user.updated_at is not None


@pytest.mark.django_db
class TestUserModelConstraints:
    """Tests for User model constraints."""

    # NOTE: test_verified_only_if_active_constraint removed because the DB-level
    # CheckConstraint 'verified_only_if_active' was removed in favor of service-layer
    # enforcement in UserService.deactivate_user. This allows cleaner reactivation flows.

    def test_no_self_referral_constraint(self, user_factory):
        """Cannot refer yourself."""
        user = user_factory()

        with pytest.raises(IntegrityError):
            with transaction.atomic():
                user.referred_by = user
                user.save()

    def test_valid_referral(self, user_factory):
        """Can have a valid referrer (different user)."""
        referrer = user_factory()
        user = user_factory(referred_by=referrer)

        assert user.referred_by == referrer
        assert user in referrer.referrals.all()


@pytest.mark.django_db
class TestUserModelProperties:
    """Tests for User model properties."""

    def test_is_complete_with_verified_and_name(self, user_with_complete_profile):
        """User is complete when verified and has first name."""
        user = user_with_complete_profile
        assert user.is_complete is True

    def test_is_complete_without_verification(self, user_factory):
        """User is not complete if not verified."""
        user = user_factory(is_verified=False)
        user.profile.first_name = "John"
        user.profile.save()

        assert user.is_complete is False

    def test_is_complete_without_first_name(self, verified_user_factory):
        """User is not complete if no first name."""
        user = verified_user_factory()
        user.profile.first_name = ""
        user.profile.save()

        assert user.is_complete is False

    def test_get_full_name_with_profile(self, user_factory):
        """get_full_name returns profile full name."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.last_name = "Doe"
        user.profile.save()

        assert user.get_full_name() == "John Doe"

    def test_get_full_name_without_names(self, user_factory):
        """get_full_name returns email if no name set."""
        user = user_factory(email="noname@example.com")
        assert user.get_full_name() == "noname@example.com"

    def test_get_short_name_with_first_name(self, user_factory):
        """get_short_name returns first name from profile."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.save()

        assert user.get_short_name() == "John"

    def test_get_short_name_without_first_name(self, user_factory):
        """get_short_name returns email prefix if no first name."""
        user = user_factory(email="prefix@example.com")
        assert user.get_short_name() == "prefix"


# =============================================================================
# USER PROFILE MODEL TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserProfileModel:
    """Tests for the UserProfile model."""

    def test_profile_created_via_signal(self, user_factory):
        """Profile is automatically created when user is created."""
        user = user_factory()

        assert hasattr(user, "profile")
        assert user.profile is not None
        assert isinstance(user.profile, UserProfile)

    def test_profile_str_representation(self, user_factory):
        """String representation includes user email."""
        user = user_factory(email="test@example.com")
        assert str(user.profile) == "Profile: test@example.com"

    def test_profile_repr(self, user_factory):
        """Repr includes user_id."""
        user = user_factory()
        assert repr(user.profile) == f"<UserProfile user_id={user.id}>"

    def test_profile_defaults(self, user_factory):
        """Profile has correct default values."""
        user = user_factory()
        profile = user.profile

        assert profile.first_name == ""
        assert profile.last_name == ""
        assert profile.phone == ""
        assert profile.timezone == "UTC"
        assert profile.language == "en"
        assert not profile.avatar  # Empty ImageField is falsy

    def test_profile_full_name_with_names(self, user_factory):
        """full_name property returns combined name."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.last_name = "Doe"
        user.profile.save()

        assert user.profile.full_name == "John Doe"

    def test_profile_full_name_first_only(self, user_factory):
        """full_name with only first name."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.save()

        assert user.profile.full_name == "John"

    def test_profile_full_name_empty(self, user_factory):
        """full_name returns email when no name set."""
        user = user_factory(email="noname@example.com")
        assert user.profile.full_name == "noname@example.com"

    def test_profile_display_name_with_full_name(self, user_factory):
        """display_name returns first + last name when both set."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.last_name = "Doe"
        user.profile.save()

        assert user.profile.display_name == "John Doe"

    def test_profile_display_name_with_first_name_only(self, user_factory):
        """display_name returns first name when only first name set."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.save()

        assert user.profile.display_name == "John"

    def test_profile_display_name_without_first_name(self, user_factory):
        """display_name returns email prefix when no first name."""
        user = user_factory(email="display@example.com")
        assert user.profile.display_name == "display"

    def test_profile_has_avatar_false(self, user_factory):
        """has_avatar is False when no avatar."""
        user = user_factory()
        assert user.profile.has_avatar is False

    def test_profile_cascade_delete(self, user_factory):
        """Profile is deleted when user is deleted."""
        user = user_factory()
        user_id = user.id

        user.delete()

        assert not UserProfile.objects.filter(user_id=user_id).exists()


# =============================================================================
# CUSTOM MANAGER TESTS
# =============================================================================


@pytest.mark.django_db
class TestCustomUserManager:
    """Tests for CustomUserManager."""

    def test_create_user(self):
        """create_user creates a regular user."""
        user = User.objects.create_user(
            email="newuser@example.com", password="testpass123"
        )

        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_staff is False
        assert user.is_superuser is False
        assert user.check_password("testpass123")

    def test_create_user_email_normalized(self):
        """Email is normalized and lowercased."""
        user = User.objects.create_user(
            email="  TEST@EXAMPLE.COM  ", password="testpass123"
        )

        assert user.email == "test@example.com"

    def test_create_user_without_email_raises(self):
        """create_user without email raises ValueError."""
        with pytest.raises(ValueError, match="Email is required"):
            User.objects.create_user(email="", password="testpass123")

    def test_create_user_auto_generates_username(self):
        """Username is auto-generated if not provided."""
        user = User.objects.create_user(
            email="noname@example.com", password="testpass123"
        )

        assert user.username.startswith("user_")
        assert len(user.username) == 13  # "user_" + 8 chars

    def test_create_superuser(self):
        """create_superuser creates a superuser."""
        user = User.objects.create_superuser(
            email="admin@example.com", password="adminpass123"
        )

        assert user.email == "admin@example.com"
        assert user.is_active is True
        assert user.is_verified is True
        assert user.is_staff is True
        assert user.is_superuser is True

    def test_create_superuser_with_is_staff_false_raises(self):
        """create_superuser with is_staff=False raises ValueError."""
        with pytest.raises(ValueError, match="is_staff=True"):
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass123", is_staff=False
            )

    def test_create_superuser_with_is_superuser_false_raises(self):
        """create_superuser with is_superuser=False raises ValueError."""
        with pytest.raises(ValueError, match="is_superuser=True"):
            User.objects.create_superuser(
                email="admin@example.com", password="adminpass123", is_superuser=False
            )


@pytest.mark.django_db
class TestUserQuerySet:
    """Tests for UserQuerySet methods."""

    def test_active_filter(self, user_factory):
        """active() returns only active users."""
        active_user = user_factory(is_active=True)
        user_factory(is_active=False)

        active_users = User.objects.active()

        assert active_user in active_users
        assert active_users.count() == 1

    def test_inactive_filter(self, user_factory):
        """inactive() returns only inactive users."""
        user_factory(is_active=True)
        inactive_user = user_factory(is_active=False)

        inactive_users = User.objects.inactive()

        assert inactive_user in inactive_users
        assert inactive_users.count() == 1

    def test_verified_filter(self, user_factory):
        """verified() returns only verified and active users."""
        verified_user = user_factory(is_active=True, is_verified=True)
        user_factory(is_active=True, is_verified=False)
        user_factory(is_active=False, is_verified=False)

        verified_users = User.objects.verified()

        assert verified_user in verified_users
        assert verified_users.count() == 1

    def test_unverified_filter(self, user_factory):
        """unverified() returns active users who haven't verified."""
        user_factory(is_active=True, is_verified=True)
        unverified_user = user_factory(is_active=True, is_verified=False)
        user_factory(
            is_active=False, is_verified=False
        )  # Inactive, shouldn't be included

        unverified_users = User.objects.unverified()

        assert unverified_user in unverified_users
        assert unverified_users.count() == 1

    def test_staff_filter(self, user_factory):
        """staff() returns only active staff users."""
        staff_user = user_factory(is_active=True, is_staff=True)
        user_factory(is_active=True, is_staff=False)
        user_factory(is_active=False, is_staff=True)  # Inactive staff

        staff_users = User.objects.staff()

        assert staff_user in staff_users
        assert staff_users.count() == 1

    def test_with_profile_select_related(self, user_factory):
        """with_profile() includes profile in query."""
        user = user_factory()

        # This should return user with profile prefetched
        users = User.objects.with_profile().filter(id=user.id)
        fetched_user = users.first()

        # Verify it returns the right user with profile
        assert fetched_user is not None
        assert fetched_user.profile is not None
        assert fetched_user.id == user.id

    def test_with_referrer_select_related(self, user_factory):
        """with_referrer() includes referrer in query via QuerySet."""
        referrer = user_factory()
        user = user_factory(referred_by=referrer)

        # with_referrer is only available on QuerySet, not delegated to manager
        users = User.objects.all().with_referrer().filter(id=user.id)
        fetched_user = users.first()

        assert fetched_user.referred_by == referrer

    def test_queryset_chaining(self, user_factory):
        """QuerySet methods can be chained."""
        user = user_factory(is_active=True, is_verified=True, is_staff=True)

        # Chain multiple filters
        result = User.objects.active().verified().staff()

        assert user in result
