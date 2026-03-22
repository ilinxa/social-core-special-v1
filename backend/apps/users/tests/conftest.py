# apps/users/tests/conftest.py
"""
Pytest configuration and fixtures for Users app tests.

These fixtures are available to all tests in the users app.
"""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.users.tests.factories import (  # User factories; Profile factories
    CompleteProfileFactory,
    InactiveUserFactory,
    ReferredUserFactory,
    StaffUserFactory,
    SuperuserFactory,
    UserFactory,
    UserProfileFactory,
    UserWithProfileFactory,
    VerifiedUserFactory,
)

# =============================================================================
# API CLIENT FIXTURES
# =============================================================================


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF APIClient instance."""
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an APIClient authenticated as a regular user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def verified_client(api_client, verified_user):
    """Return an APIClient authenticated as a verified user."""
    api_client.force_authenticate(user=verified_user)
    return api_client


@pytest.fixture
def staff_client(api_client, staff_user):
    """Return an APIClient authenticated as a staff user."""
    api_client.force_authenticate(user=staff_user)
    return api_client


@pytest.fixture
def admin_client(api_client, superuser):
    """Return an APIClient authenticated as a superuser."""
    api_client.force_authenticate(user=superuser)
    return api_client


# =============================================================================
# USER FIXTURES
# =============================================================================


@pytest.fixture
def user(db):
    """Create and return a regular test user."""
    return UserFactory()


@pytest.fixture
def verified_user(db):
    """Create and return a verified user."""
    return VerifiedUserFactory()


@pytest.fixture
def staff_user(db):
    """Create and return a staff user."""
    return StaffUserFactory()


@pytest.fixture
def superuser(db):
    """Create and return a superuser."""
    return SuperuserFactory()


@pytest.fixture
def inactive_user(db):
    """Create and return an inactive user."""
    return InactiveUserFactory()


@pytest.fixture
def referred_user(db):
    """Create and return a user with a referrer."""
    return ReferredUserFactory()


@pytest.fixture
def another_user(db):
    """Create and return another user (for permission tests)."""
    return UserFactory(username="another_user", email="another@example.com")


# =============================================================================
# FACTORY FIXTURES
# =============================================================================


@pytest.fixture
def user_factory(db):
    """Return the UserFactory for creating users in tests."""
    return UserFactory


@pytest.fixture
def verified_user_factory(db):
    """Return the VerifiedUserFactory."""
    return VerifiedUserFactory


@pytest.fixture
def user_profile_factory(db):
    """Return the UserProfileFactory."""
    return UserProfileFactory


@pytest.fixture
def complete_profile_factory(db):
    """Return the CompleteProfileFactory."""
    return CompleteProfileFactory


@pytest.fixture
def user_with_profile_factory(db):
    """Return the UserWithProfileFactory."""
    return UserWithProfileFactory


@pytest.fixture
def referred_user_factory(db):
    """Return the ReferredUserFactory."""
    return ReferredUserFactory


# =============================================================================
# PROFILE FIXTURES
# =============================================================================


@pytest.fixture
def user_with_complete_profile(db):
    """Create a verified user with a complete profile."""
    user = VerifiedUserFactory()
    user.profile.first_name = "John"
    user.profile.last_name = "Doe"
    user.profile.phone = "+1234567890"
    user.profile.timezone = "America/New_York"
    user.profile.language = "en"
    user.profile.save()
    return user


# =============================================================================
# FILE UPLOAD FIXTURES
# =============================================================================


@pytest.fixture
def sample_image():
    """
    Create and return a sample image file for avatar upload tests.

    Returns:
        SimpleUploadedFile: A valid PNG image file.
    """
    # Create a simple red 100x100 image
    image = Image.new("RGB", (100, 100), color="red")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return SimpleUploadedFile(
        name="test_avatar.png", content=buffer.read(), content_type="image/png"
    )


@pytest.fixture
def sample_jpeg_image():
    """Create and return a JPEG image file."""
    image = Image.new("RGB", (100, 100), color="blue")
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    return SimpleUploadedFile(
        name="test_avatar.jpg", content=buffer.read(), content_type="image/jpeg"
    )


@pytest.fixture
def oversized_image():
    """
    Create an oversized image file (over 5MB limit).

    Returns:
        SimpleUploadedFile: An image file larger than allowed.
    """
    # Create a large image (this creates ~6MB file)
    image = Image.new("RGB", (3000, 3000), color="green")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    return SimpleUploadedFile(
        name="large_avatar.png", content=buffer.read(), content_type="image/png"
    )


@pytest.fixture
def invalid_file():
    """
    Create an invalid file (not an image).

    Returns:
        SimpleUploadedFile: A text file pretending to be an image.
    """
    return SimpleUploadedFile(
        name="not_an_image.txt",
        content=b"This is not an image file",
        content_type="text/plain",
    )


# =============================================================================
# URL FIXTURES
# =============================================================================


@pytest.fixture
def me_url():
    """Return the current user endpoint URL."""
    return "/api/v1/users/me/"


@pytest.fixture
def profile_url():
    """Return the profile endpoint URL."""
    return "/api/v1/users/me/profile/"


@pytest.fixture
def avatar_url():
    """Return the avatar endpoint URL."""
    return "/api/v1/users/me/avatar/"


@pytest.fixture
def check_username_url():
    """Return the check-username endpoint URL."""
    return "/api/v1/users/check-username/"


@pytest.fixture
def public_profile_url():
    """Return a URL builder for public user profile endpoint."""

    def _url(username):
        return f"/api/v1/users/{username}/"

    return _url
