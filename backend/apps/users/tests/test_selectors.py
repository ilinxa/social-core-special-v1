# apps/users/tests/test_selectors.py
"""
Tests for UserSelector.

Covers all read operations:
    - Single user queries (get_by_id, get_by_email, get_by_username)
    - QuerySet builders (get_active_users, get_verified_users, etc.)
    - Referral queries
    - Profile queries
    - Existence checks
"""

import pytest

from apps.core.exceptions import NotFound
from apps.users.selectors import UserSelector

# =============================================================================
# SINGLE USER QUERY TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserSelectorGetById:
    """Tests for UserSelector.get_by_id."""

    def test_get_by_id_success(self, user_factory):
        """Can get user by ID."""
        user = user_factory()

        result = UserSelector.get_by_id(user_id=user.id)

        assert result.id == user.id
        assert result.email == user.email

    def test_get_by_id_not_found(self):
        """Non-existent ID raises NotFound."""
        with pytest.raises(NotFound) as exc_info:
            UserSelector.get_by_id(user_id=99999)

        assert exc_info.value.details["resource"] == "User"
        assert exc_info.value.details["resource_id"] == "99999"

    def test_get_by_id_with_profile(self, user_factory):
        """Can include profile with select_related."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.save()

        result = UserSelector.get_by_id(user_id=user.id, with_profile=True)

        # Profile should be prefetched
        assert result.profile.first_name == "John"


@pytest.mark.django_db
class TestUserSelectorGetByIdOrNone:
    """Tests for UserSelector.get_by_id_or_none."""

    def test_get_by_id_or_none_success(self, user_factory):
        """Can get user by ID."""
        user = user_factory()

        result = UserSelector.get_by_id_or_none(user_id=user.id)

        assert result is not None
        assert result.id == user.id

    def test_get_by_id_or_none_not_found(self):
        """Non-existent ID returns None."""
        result = UserSelector.get_by_id_or_none(user_id=99999)
        assert result is None


@pytest.mark.django_db
class TestUserSelectorGetByEmail:
    """Tests for UserSelector.get_by_email."""

    def test_get_by_email_success(self, user_factory):
        """Can get user by email."""
        user = user_factory(email="test@example.com")

        result = UserSelector.get_by_email(email="test@example.com")

        assert result.id == user.id
        assert result.email == "test@example.com"

    def test_get_by_email_case_insensitive(self, user_factory):
        """Email lookup is case-insensitive."""
        user = user_factory(email="test@example.com")

        result = UserSelector.get_by_email(email="TEST@EXAMPLE.COM")

        assert result.id == user.id

    def test_get_by_email_strips_whitespace(self, user_factory):
        """Email lookup strips whitespace."""
        user = user_factory(email="test@example.com")

        result = UserSelector.get_by_email(email="  test@example.com  ")

        assert result.id == user.id

    def test_get_by_email_not_found(self):
        """Non-existent email raises NotFound."""
        with pytest.raises(NotFound) as exc_info:
            UserSelector.get_by_email(email="nonexistent@example.com")

        assert exc_info.value.details["resource"] == "User"


@pytest.mark.django_db
class TestUserSelectorGetByEmailOrNone:
    """Tests for UserSelector.get_by_email_or_none."""

    def test_get_by_email_or_none_success(self, user_factory):
        """Can get user by email."""
        user = user_factory(email="test@example.com")

        result = UserSelector.get_by_email_or_none(email="test@example.com")

        assert result is not None
        assert result.id == user.id

    def test_get_by_email_or_none_not_found(self):
        """Non-existent email returns None."""
        result = UserSelector.get_by_email_or_none(email="nonexistent@example.com")
        assert result is None


@pytest.mark.django_db
class TestUserSelectorGetByUsername:
    """Tests for UserSelector.get_by_username."""

    def test_get_by_username_success(self, user_factory):
        """Can get user by username."""
        user = user_factory(username="testuser")

        result = UserSelector.get_by_username(username="testuser")

        assert result.id == user.id
        assert result.username == "testuser"

    def test_get_by_username_case_insensitive(self, user_factory):
        """Username lookup is case-insensitive."""
        user = user_factory(username="testuser")

        result = UserSelector.get_by_username(username="TESTUSER")

        assert result.id == user.id

    def test_get_by_username_not_found(self):
        """Non-existent username raises NotFound."""
        with pytest.raises(NotFound):
            UserSelector.get_by_username(username="nonexistent")


@pytest.mark.django_db
class TestUserSelectorGetByUsernameOrNone:
    """Tests for UserSelector.get_by_username_or_none."""

    def test_get_by_username_or_none_success(self, user_factory):
        """Can get user by username."""
        user = user_factory(username="testuser")

        result = UserSelector.get_by_username_or_none(username="testuser")

        assert result is not None
        assert result.id == user.id

    def test_get_by_username_or_none_not_found(self):
        """Non-existent username returns None."""
        result = UserSelector.get_by_username_or_none(username="nonexistent")
        assert result is None


@pytest.mark.django_db
class TestUserSelectorGetActiveByEmail:
    """Tests for UserSelector.get_active_by_email."""

    def test_get_active_by_email_success(self, user_factory):
        """Can get active user by email."""
        user = user_factory(email="active@example.com", is_active=True)

        result = UserSelector.get_active_by_email(email="active@example.com")

        assert result.id == user.id

    def test_get_active_by_email_inactive_not_found(self, user_factory):
        """Inactive user raises NotFound."""
        user_factory(email="inactive@example.com", is_active=False)

        with pytest.raises(NotFound):
            UserSelector.get_active_by_email(email="inactive@example.com")


# =============================================================================
# QUERYSET BUILDER TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserSelectorQuerySetBuilders:
    """Tests for QuerySet builder methods."""

    def test_get_active_users(self, user_factory):
        """get_active_users returns only active users."""
        active_user = user_factory(is_active=True)
        user_factory(is_active=False)

        result = UserSelector.get_active_users()

        assert active_user in result
        assert result.count() == 1

    def test_get_verified_users(self, user_factory):
        """get_verified_users returns only verified and active users."""
        verified_user = user_factory(is_active=True, is_verified=True)
        user_factory(is_active=True, is_verified=False)
        user_factory(is_active=False, is_verified=False)

        result = UserSelector.get_verified_users()

        assert verified_user in result
        assert result.count() == 1

    def test_get_unverified_users(self, user_factory):
        """get_unverified_users returns active unverified users."""
        user_factory(is_active=True, is_verified=True)
        unverified_user = user_factory(is_active=True, is_verified=False)
        user_factory(is_active=False, is_verified=False)

        result = UserSelector.get_unverified_users()

        assert unverified_user in result
        assert result.count() == 1

    def test_get_staff_users(self, user_factory):
        """get_staff_users returns only staff users."""
        staff_user = user_factory(is_active=True, is_staff=True)
        user_factory(is_active=True, is_staff=False)

        result = UserSelector.get_staff_users()

        assert staff_user in result
        assert result.count() == 1


# =============================================================================
# REFERRAL QUERY TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserSelectorReferralQueries:
    """Tests for referral query methods."""

    def test_get_referrals(self, user_factory):
        """get_referrals returns users referred by this user."""
        referrer = user_factory()
        referred1 = user_factory(referred_by=referrer)
        referred2 = user_factory(referred_by=referrer)
        user_factory()  # Not referred

        result = UserSelector.get_referrals(user=referrer)

        assert referred1 in result
        assert referred2 in result
        assert result.count() == 2

    def test_get_referrals_empty(self, user_factory):
        """get_referrals returns empty queryset when no referrals."""
        user = user_factory()

        result = UserSelector.get_referrals(user=user)

        assert result.count() == 0

    def test_count_referrals(self, user_factory):
        """count_referrals returns correct count."""
        referrer = user_factory()
        user_factory(referred_by=referrer)
        user_factory(referred_by=referrer)
        user_factory(referred_by=referrer)

        result = UserSelector.count_referrals(user=referrer)

        assert result == 3

    def test_count_referrals_zero(self, user_factory):
        """count_referrals returns zero when no referrals."""
        user = user_factory()

        result = UserSelector.count_referrals(user=user)

        assert result == 0

    def test_get_top_referrers(self, user_factory):
        """get_top_referrers returns users ordered by referral count."""
        top_referrer = user_factory()
        for _ in range(5):
            user_factory(referred_by=top_referrer)

        second_referrer = user_factory()
        for _ in range(3):
            user_factory(referred_by=second_referrer)

        user_factory()  # No referrals

        result = list(UserSelector.get_top_referrers(limit=10))

        assert len(result) == 2
        assert result[0].id == top_referrer.id
        assert result[1].id == second_referrer.id

    def test_get_top_referrers_limit(self, user_factory):
        """get_top_referrers respects limit."""
        for i in range(5):
            referrer = user_factory()
            for _ in range(5 - i):
                user_factory(referred_by=referrer)

        result = list(UserSelector.get_top_referrers(limit=3))

        assert len(result) == 3


# =============================================================================
# PROFILE QUERY TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserSelectorProfileQueries:
    """Tests for profile query methods."""

    def test_get_profile(self, user_factory):
        """get_profile returns user's profile."""
        user = user_factory()
        user.profile.first_name = "John"
        user.profile.save()

        result = UserSelector.get_profile(user=user)

        assert result.first_name == "John"
        assert result.user_id == user.id


# =============================================================================
# EXISTENCE CHECK TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserSelectorExistenceChecks:
    """Tests for existence check methods."""

    def test_email_exists_true(self, user_factory):
        """email_exists returns True when email exists."""
        user_factory(email="exists@example.com")

        result = UserSelector.email_exists(email="exists@example.com")

        assert result is True

    def test_email_exists_false(self):
        """email_exists returns False when email doesn't exist."""
        result = UserSelector.email_exists(email="nonexistent@example.com")
        assert result is False

    def test_email_exists_case_insensitive(self, user_factory):
        """email_exists is case-insensitive."""
        user_factory(email="exists@example.com")

        result = UserSelector.email_exists(email="EXISTS@EXAMPLE.COM")

        assert result is True

    def test_email_exists_strips_whitespace(self, user_factory):
        """email_exists strips whitespace."""
        user_factory(email="exists@example.com")

        result = UserSelector.email_exists(email="  exists@example.com  ")

        assert result is True

    def test_username_exists_true(self, user_factory):
        """username_exists returns True when username exists."""
        user_factory(username="existinguser")

        result = UserSelector.username_exists(username="existinguser")

        assert result is True

    def test_username_exists_false(self):
        """username_exists returns False when username doesn't exist."""
        result = UserSelector.username_exists(username="nonexistent")
        assert result is False

    def test_username_exists_case_insensitive(self, user_factory):
        """username_exists is case-insensitive."""
        user_factory(username="existinguser")

        result = UserSelector.username_exists(username="EXISTINGUSER")

        assert result is True

    def test_username_exists_strips_whitespace(self, user_factory):
        """username_exists strips whitespace."""
        user_factory(username="existinguser")

        result = UserSelector.username_exists(username="  existinguser  ")

        assert result is True
