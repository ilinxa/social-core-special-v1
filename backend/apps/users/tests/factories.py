# apps/users/tests/factories.py
"""
Factory-boy factories for Users app tests.

Usage:
    from apps.users.tests.factories import UserFactory, UserProfileFactory

    # Create a user (profile created automatically)
    user = UserFactory()

    # Create with specific attributes
    user = UserFactory(email="custom@example.com", is_verified=True)

    # Build without saving to DB
    user = UserFactory.build()
"""

import factory
from factory.django import DjangoModelFactory
from django.contrib.auth import get_user_model

from apps.users.models import UserProfile

User = get_user_model()


# =============================================================================
# USER FACTORIES
# =============================================================================


class UserFactory(DjangoModelFactory):
    """
    Factory for creating test users.

    Note: UserProfile is created explicitly via post_generation hook since
    the signal uses transaction.on_commit() which doesn't run in tests.
    """

    class Meta:
        model = User
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user_{n:08d}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    is_active = True
    is_verified = False
    is_staff = False
    is_superuser = False
    referred_by = None

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        """Set password after user creation."""
        password = extracted or "testpass123"
        self.set_password(password)
        if create:
            self.save(update_fields=["password"])

    @factory.post_generation
    def create_profile(self, create, extracted, **kwargs):
        """
        Create profile for user in tests.

        The signal uses transaction.on_commit() which doesn't execute in tests,
        so we create the profile explicitly here.
        """
        if create and not UserProfile.objects.filter(user=self).exists():
            UserProfile.objects.create(user=self)


class VerifiedUserFactory(UserFactory):
    """Factory for creating verified users."""

    is_verified = True


class StaffUserFactory(UserFactory):
    """Factory for creating staff users."""

    is_staff = True
    is_verified = True


class SuperuserFactory(UserFactory):
    """Factory for creating superusers."""

    is_staff = True
    is_superuser = True
    is_verified = True


class InactiveUserFactory(UserFactory):
    """Factory for creating inactive users."""

    is_active = False
    is_verified = False  # Constraint: inactive users cannot be verified


# =============================================================================
# USER PROFILE FACTORIES
# =============================================================================


class UserProfileFactory(DjangoModelFactory):
    """
    Factory for UserProfile.

    Note: Normally profiles are created via signal. Use this factory
    only when you need explicit control over profile fields.
    """

    class Meta:
        model = UserProfile
        django_get_or_create = ("user",)

    user = factory.SubFactory(UserFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone = ""
    timezone = "UTC"
    language = "en"
    bio = ""
    country = ""
    city = ""
    tags = factory.LazyFunction(list)


class CompleteProfileFactory(UserProfileFactory):
    """Factory for creating a complete user profile."""

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone = "+1234567890"
    timezone = "America/New_York"
    language = "en"


# =============================================================================
# COMPOSITE FACTORIES
# =============================================================================


class UserWithProfileFactory(UserFactory):
    """
    Factory that creates User and updates profile with data.

    Usage:
        user = UserWithProfileFactory(
            profile__first_name="John",
            profile__last_name="Doe"
        )
    """

    @factory.post_generation
    def profile(self, create, extracted, **kwargs):
        """Update profile with provided kwargs."""
        if not create:
            return

        # Profile is auto-created by signal, update it with kwargs
        if kwargs:
            for key, value in kwargs.items():
                setattr(self.profile, key, value)
            self.profile.save()


class ReferredUserFactory(UserFactory):
    """Factory for creating a user with a referrer."""

    referred_by = factory.SubFactory(UserFactory)
