# apps/users/tests/test_services.py
"""
Tests for UserService.

Covers all write operations:
    - create_user
    - verify_email / unverify_email
    - update_profile
    - update_avatar / remove_avatar
    - deactivate_user / reactivate_user
    - change_username
    - change_email
    - update_last_login
"""

import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone

from apps.core.exceptions import ConflictError, ValidationError
from apps.users.services import UserService
from apps.users.models import User


# =============================================================================
# CREATE USER TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserServiceCreateUser:
    """Tests for UserService.create_user."""

    def test_create_user_success(self):
        """Can create user with valid data."""
        user = UserService.create_user(
            email="newuser@example.com",
            password="ValidPass123!"
        )

        assert user.email == "newuser@example.com"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.check_password("ValidPass123!")
        # Note: Profile is created via signal with transaction.on_commit()
        # which doesn't run in tests, so we don't check for profile here

    def test_create_user_email_normalized(self):
        """Email is normalized and lowercased."""
        user = UserService.create_user(
            email="  TEST@EXAMPLE.COM  ",
            password="ValidPass123!"
        )

        assert user.email == "test@example.com"

    def test_create_user_duplicate_email_raises(self, user_factory):
        """Creating user with duplicate email raises ConflictError."""
        user_factory(email="existing@example.com")

        with pytest.raises(ConflictError) as exc_info:
            UserService.create_user(
                email="existing@example.com",
                password="ValidPass123!"
            )

        assert "email already exists" in str(exc_info.value)

    def test_create_user_duplicate_email_case_insensitive(self, user_factory):
        """Email uniqueness is case-insensitive."""
        user_factory(email="existing@example.com")

        with pytest.raises(ConflictError):
            UserService.create_user(
                email="EXISTING@example.com",
                password="ValidPass123!"
            )

    def test_create_user_weak_password_raises(self):
        """Creating user with weak password raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            UserService.create_user(
                email="test@example.com",
                password="weak"
            )

        assert exc_info.value.details["field"] == "password"

    def test_create_user_with_referrer(self, user_factory):
        """Can create user with valid referrer."""
        referrer = user_factory()

        user = UserService.create_user(
            email="referred@example.com",
            password="ValidPass123!",
            referred_by_id=referrer.id
        )

        assert user.referred_by == referrer

    def test_create_user_with_invalid_referrer(self):
        """Invalid referrer ID is silently ignored."""
        user = UserService.create_user(
            email="referred@example.com",
            password="ValidPass123!",
            referred_by_id=99999
        )

        assert user.referred_by is None

    @patch("apps.users.services.AuditService.log")
    def test_create_user_logs_audit(self, mock_audit):
        """User creation is logged to audit."""
        user = UserService.create_user(
            email="audit@example.com",
            password="ValidPass123!"
        )

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert call_kwargs["actor"] == user
        assert call_kwargs["resource"] == user


# =============================================================================
# VERIFY/UNVERIFY EMAIL TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserServiceVerifyEmail:
    """Tests for UserService.verify_email."""

    def test_verify_email_success(self, user_factory):
        """Can verify user email."""
        user = user_factory(is_verified=False)

        result = UserService.verify_email(user=user)

        assert result.is_verified is True
        user.refresh_from_db()
        assert user.is_verified is True

    def test_verify_email_already_verified(self, user_factory):
        """Already verified user remains verified."""
        user = user_factory(is_verified=True)

        result = UserService.verify_email(user=user)

        assert result.is_verified is True


@pytest.mark.django_db
class TestUserServiceUnverifyEmail:
    """Tests for UserService.unverify_email."""

    def test_unverify_email_success(self, user_factory):
        """Can unverify user email."""
        user = user_factory(is_verified=True)

        result = UserService.unverify_email(user=user)

        assert result.is_verified is False
        user.refresh_from_db()
        assert user.is_verified is False


# =============================================================================
# UPDATE PROFILE TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserServiceUpdateProfile:
    """Tests for UserService.update_profile."""

    def test_update_profile_first_name(self, user_factory):
        """Can update first name."""
        user = user_factory()

        profile = UserService.update_profile(
            user=user,
            first_name="John"
        )

        assert profile.first_name == "John"

    def test_update_profile_last_name(self, user_factory):
        """Can update last name."""
        user = user_factory()

        profile = UserService.update_profile(
            user=user,
            last_name="Doe"
        )

        assert profile.last_name == "Doe"

    def test_update_profile_phone(self, user_factory):
        """Can update phone."""
        user = user_factory()

        profile = UserService.update_profile(
            user=user,
            phone="+1234567890"
        )

        assert profile.phone == "+1234567890"

    def test_update_profile_timezone(self, user_factory):
        """Can update timezone."""
        user = user_factory()

        profile = UserService.update_profile(
            user=user,
            timezone="America/New_York"
        )

        assert profile.timezone == "America/New_York"

    def test_update_profile_language(self, user_factory):
        """Can update language."""
        user = user_factory()

        profile = UserService.update_profile(
            user=user,
            language="es"
        )

        assert profile.language == "es"

    def test_update_profile_multiple_fields(self, user_factory):
        """Can update multiple fields at once."""
        user = user_factory()

        profile = UserService.update_profile(
            user=user,
            first_name="John",
            last_name="Doe",
            phone="+1234567890"
        )

        assert profile.first_name == "John"
        assert profile.last_name == "Doe"
        assert profile.phone == "+1234567890"

    def test_update_profile_strips_whitespace(self, user_factory):
        """Profile fields are stripped of whitespace."""
        user = user_factory()

        profile = UserService.update_profile(
            user=user,
            first_name="  John  ",
            last_name="  Doe  "
        )

        assert profile.first_name == "John"
        assert profile.last_name == "Doe"

    def test_update_profile_none_ignored(self, user_factory):
        """None values don't update fields."""
        user = user_factory()
        user.profile.first_name = "Original"
        user.profile.save()

        profile = UserService.update_profile(
            user=user,
            first_name=None,
            last_name="Doe"
        )

        assert profile.first_name == "Original"
        assert profile.last_name == "Doe"

    def test_update_profile_empty_string_allowed(self, user_factory):
        """Empty string can clear a field."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.save()

        profile = UserService.update_profile(
            user=user,
            first_name=""
        )

        assert profile.first_name == ""

    @patch("apps.users.services.AuditService.log")
    def test_update_profile_logs_audit_on_change(self, mock_audit, user_factory):
        """Profile update with changes is logged to audit."""
        user = user_factory()

        UserService.update_profile(
            user=user,
            first_name="John"
        )

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert "first_name" in call_kwargs["changes"]

    @patch("apps.users.services.AuditService.log")
    def test_update_profile_no_audit_without_changes(self, mock_audit, user_factory):
        """Profile update without changes is not logged to audit."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.save()

        # Update with same value
        UserService.update_profile(
            user=user,
            first_name="John"
        )

        mock_audit.assert_not_called()


# =============================================================================
# AVATAR TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserServiceUpdateAvatar:
    """Tests for UserService.update_avatar."""

    def test_update_avatar_success(self, user_factory, sample_image):
        """Can update user avatar."""
        user = user_factory()

        profile = UserService.update_avatar(
            user=user,
            avatar=sample_image
        )

        assert profile.avatar is not None
        assert profile.has_avatar is True

    @patch("apps.users.services.AuditService.log")
    def test_update_avatar_logs_audit(self, mock_audit, user_factory, sample_image):
        """Avatar update is logged to audit."""
        user = user_factory()

        UserService.update_avatar(user=user, avatar=sample_image)

        mock_audit.assert_called_once()


@pytest.mark.django_db
class TestUserServiceRemoveAvatar:
    """Tests for UserService.remove_avatar."""

    def test_remove_avatar_success(self, user_factory, sample_image):
        """Can remove user avatar."""
        user = user_factory()
        # First add an avatar
        UserService.update_avatar(user=user, avatar=sample_image)

        profile = UserService.remove_avatar(user=user)

        assert not profile.avatar  # Empty ImageField is falsy
        assert profile.has_avatar is False

    def test_remove_avatar_when_none(self, user_factory):
        """Removing non-existent avatar succeeds silently."""
        user = user_factory()

        profile = UserService.remove_avatar(user=user)

        assert profile.has_avatar is False


# =============================================================================
# DEACTIVATE/REACTIVATE USER TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserServiceDeactivateUser:
    """Tests for UserService.deactivate_user."""

    def test_deactivate_user_success(self, user_factory):
        """Can deactivate active user."""
        user = user_factory(is_active=True, is_verified=True)

        result = UserService.deactivate_user(user=user)

        assert result.is_active is False
        assert result.is_verified is False  # Constraint: inactive = not verified

    @patch("apps.users.services.AuditService.log")
    def test_deactivate_user_logs_audit(self, mock_audit, user_factory):
        """User deactivation is logged to audit."""
        user = user_factory(is_active=True)

        UserService.deactivate_user(user=user)

        mock_audit.assert_called_once()


@pytest.mark.django_db
class TestUserServiceReactivateUser:
    """Tests for UserService.reactivate_user."""

    def test_reactivate_user_success(self, user_factory):
        """Can reactivate inactive user."""
        user = user_factory(is_active=False, is_verified=False)

        result = UserService.reactivate_user(user=user)

        assert result.is_active is True
        # User must re-verify after reactivation
        assert result.is_verified is False

    @patch("apps.users.services.AuditService.log")
    def test_reactivate_user_logs_audit(self, mock_audit, user_factory):
        """User reactivation is logged to audit."""
        user = user_factory(is_active=False)

        UserService.reactivate_user(user=user)

        mock_audit.assert_called_once()


# =============================================================================
# CHANGE USERNAME TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserServiceChangeUsername:
    """Tests for UserService.change_username."""

    def test_change_username_success(self, user_factory):
        """Can change username."""
        user = user_factory()

        result = UserService.change_username(
            user=user,
            new_username="newusername"
        )

        assert result.username == "newusername"

    def test_change_username_lowercased(self, user_factory):
        """Username is lowercased."""
        user = user_factory()

        result = UserService.change_username(
            user=user,
            new_username="MyUsername"
        )

        assert result.username == "myusername"

    def test_change_username_stripped(self, user_factory):
        """Username is stripped of whitespace."""
        user = user_factory()

        result = UserService.change_username(
            user=user,
            new_username="  newusername  "
        )

        assert result.username == "newusername"

    def test_change_username_invalid_format_raises(self, user_factory):
        """Invalid username format raises ValidationError."""
        user = user_factory()

        with pytest.raises(ValidationError) as exc_info:
            UserService.change_username(
                user=user,
                new_username="ab"  # Too short
            )

        assert exc_info.value.details["field"] == "username"

    def test_change_username_invalid_characters_raises(self, user_factory):
        """Username with invalid characters raises ValidationError."""
        user = user_factory()

        with pytest.raises(ValidationError):
            UserService.change_username(
                user=user,
                new_username="user@name"  # Invalid character
            )

    def test_change_username_too_long_raises(self, user_factory):
        """Username too long raises ValidationError."""
        user = user_factory()

        with pytest.raises(ValidationError):
            UserService.change_username(
                user=user,
                new_username="a" * 31  # Max is 30
            )

    def test_change_username_duplicate_raises(self, user_factory):
        """Duplicate username raises ConflictError."""
        existing_user = user_factory(username="taken")
        user = user_factory()

        with pytest.raises(ConflictError) as exc_info:
            UserService.change_username(
                user=user,
                new_username="taken"
            )

        assert "already taken" in str(exc_info.value)

    def test_change_username_case_insensitive_duplicate(self, user_factory):
        """Username uniqueness is case-insensitive."""
        user_factory(username="taken")
        user = user_factory()

        with pytest.raises(ConflictError):
            UserService.change_username(
                user=user,
                new_username="TAKEN"
            )

    def test_change_username_same_user_allowed(self, user_factory):
        """User can change to same username (case change)."""
        user = user_factory(username="myname")

        # This should work - same user
        result = UserService.change_username(
            user=user,
            new_username="myname"
        )

        assert result.username == "myname"

    @patch("apps.users.services.AuditService.log")
    def test_change_username_logs_audit(self, mock_audit, user_factory):
        """Username change is logged to audit."""
        user = user_factory(username="oldname")

        UserService.change_username(user=user, new_username="newname")

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert "username" in call_kwargs["changes"]


# =============================================================================
# CHANGE EMAIL TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserServiceChangeEmail:
    """Tests for UserService.change_email."""

    def test_change_email_success(self, user_factory):
        """Can change email."""
        user = user_factory(email="old@example.com", is_verified=True)

        result = UserService.change_email(
            user=user,
            new_email="new@example.com"
        )

        assert result.email == "new@example.com"

    def test_change_email_unverifies_user(self, user_factory):
        """Email change unverifies the user."""
        user = user_factory(is_verified=True)

        result = UserService.change_email(
            user=user,
            new_email="new@example.com"
        )

        assert result.is_verified is False

    def test_change_email_normalized(self, user_factory):
        """New email is normalized and lowercased."""
        user = user_factory()

        result = UserService.change_email(
            user=user,
            new_email="  NEW@EXAMPLE.COM  "
        )

        assert result.email == "new@example.com"

    def test_change_email_duplicate_raises(self, user_factory):
        """Duplicate email raises ConflictError."""
        user_factory(email="existing@example.com")
        user = user_factory()

        with pytest.raises(ConflictError) as exc_info:
            UserService.change_email(
                user=user,
                new_email="existing@example.com"
            )

        assert "email already exists" in str(exc_info.value)

    def test_change_email_case_insensitive_duplicate(self, user_factory):
        """Email uniqueness is case-insensitive."""
        user_factory(email="existing@example.com")
        user = user_factory()

        with pytest.raises(ConflictError):
            UserService.change_email(
                user=user,
                new_email="EXISTING@example.com"
            )

    def test_change_email_same_user_allowed(self, user_factory):
        """User can change to same email."""
        user = user_factory(email="same@example.com")

        # This should work - same user
        result = UserService.change_email(
            user=user,
            new_email="same@example.com"
        )

        assert result.email == "same@example.com"

    @patch("apps.users.services.AuditService.log")
    def test_change_email_logs_audit(self, mock_audit, user_factory):
        """Email change is logged to audit."""
        user = user_factory(email="old@example.com")

        UserService.change_email(user=user, new_email="new@example.com")

        mock_audit.assert_called_once()
        call_kwargs = mock_audit.call_args.kwargs
        assert "email" in call_kwargs["changes"]


# =============================================================================
# UPDATE LAST LOGIN TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserServiceUpdateLastLogin:
    """Tests for UserService.update_last_login."""

    def test_update_last_login_success(self, user_factory):
        """Can update last login timestamp."""
        user = user_factory()
        original_login = user.last_login

        result = UserService.update_last_login(user=user)

        assert result.last_login is not None
        assert result.last_login != original_login

    def test_update_last_login_sets_current_time(self, user_factory):
        """Last login is set to current time."""
        user = user_factory()
        before = timezone.now()

        result = UserService.update_last_login(user=user)

        after = timezone.now()
        assert before <= result.last_login <= after
