# apps/users/tests/test_views.py
"""
Tests for User and Profile API views.

Covers:
    - CurrentUserView (GET, PATCH, DELETE /api/v1/users/me/)
    - ProfileView (GET, PATCH /api/v1/users/me/profile/)
    - AvatarView (POST, DELETE /api/v1/users/me/avatar/)
    - CheckUsernameView (GET /api/v1/users/check-username/)
"""

import pytest
from django.urls import reverse
from rest_framework import status

# =============================================================================
# CURRENT USER VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestCurrentUserViewGet:
    """Tests for GET /api/v1/users/me/."""

    def test_get_current_user_requires_auth(self, api_client, me_url):
        """Unauthenticated request returns 401."""
        response = api_client.get(me_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_success(self, authenticated_client, user, me_url):
        """Authenticated user can get their own data."""
        response = authenticated_client.get(me_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(user.id)
        assert response.data["email"] == user.email
        assert response.data["username"] == user.username
        assert "profile" in response.data

    def test_get_current_user_includes_profile(
        self, authenticated_client, user, me_url
    ):
        """Response includes nested profile data."""
        user.profile.first_name = "John"
        user.profile.last_name = "Doe"
        user.profile.save()

        response = authenticated_client.get(me_url)

        assert response.status_code == status.HTTP_200_OK
        profile = response.data["profile"]
        assert profile["first_name"] == "John"
        assert profile["last_name"] == "Doe"
        assert profile["full_name"] == "John Doe"
        assert profile["display_name"] == "John Doe"

    def test_get_current_user_includes_status_flags(
        self, authenticated_client, user, me_url
    ):
        """Response includes status flags."""
        response = authenticated_client.get(me_url)

        assert response.status_code == status.HTTP_200_OK
        assert "is_active" in response.data
        assert "is_verified" in response.data
        assert "is_complete" in response.data
        assert "can_create_business" in response.data
        assert "is_staff" in response.data
        assert "is_superuser" in response.data

    def test_get_current_user_includes_timestamps(
        self, authenticated_client, user, me_url
    ):
        """Response includes timestamps."""
        response = authenticated_client.get(me_url)

        assert response.status_code == status.HTTP_200_OK
        assert "date_joined" in response.data
        assert "last_login" in response.data


@pytest.mark.django_db
class TestCurrentUserViewPatch:
    """Tests for PATCH /api/v1/users/me/."""

    def test_patch_current_user_requires_auth(self, api_client, me_url):
        """Unauthenticated request returns 401."""
        response = api_client.patch(me_url, {"username": "newname"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_username_success(self, authenticated_client, user, me_url):
        """Can update username."""
        response = authenticated_client.patch(me_url, {"username": "newusername"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == "newusername"
        user.refresh_from_db()
        assert user.username == "newusername"

    def test_patch_username_invalid_format(self, authenticated_client, me_url):
        """Invalid username format returns 400."""
        response = authenticated_client.patch(me_url, {"username": "ab"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data.get("error", {}).get("details", {})

    def test_patch_username_invalid_characters(self, authenticated_client, me_url):
        """Username with invalid characters returns 400."""
        response = authenticated_client.patch(me_url, {"username": "user@name"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_patch_username_duplicate(self, authenticated_client, user_factory, me_url):
        """Duplicate username returns 409."""
        user_factory(username="taken")

        response = authenticated_client.patch(me_url, {"username": "taken"})

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_patch_empty_body(self, authenticated_client, user, me_url):
        """Empty body returns 200 with unchanged data."""
        original_username = user.username

        response = authenticated_client.patch(me_url, {})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == original_username


@pytest.mark.django_db
class TestCurrentUserViewDelete:
    """Tests for DELETE /api/v1/users/me/."""

    def test_delete_current_user_requires_auth(self, api_client, me_url):
        """Unauthenticated request returns 401."""
        response = api_client.delete(me_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_current_user_deactivates(self, authenticated_client, user, me_url):
        """DELETE deactivates the user account."""
        response = authenticated_client.delete(me_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        user.refresh_from_db()
        assert user.is_active is False


# =============================================================================
# PROFILE VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestProfileViewGet:
    """Tests for GET /api/v1/users/me/profile/."""

    def test_get_profile_requires_auth(self, api_client, profile_url):
        """Unauthenticated request returns 401."""
        response = api_client.get(profile_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_profile_success(self, authenticated_client, user, profile_url):
        """Authenticated user can get their profile."""
        user.profile.first_name = "John"
        user.profile.last_name = "Doe"
        user.profile.save()

        response = authenticated_client.get(profile_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "John"
        assert response.data["last_name"] == "Doe"

    def test_get_profile_includes_computed_fields(
        self, authenticated_client, user, profile_url
    ):
        """Response includes computed fields."""
        user.profile.first_name = "John"
        user.profile.save()

        response = authenticated_client.get(profile_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["full_name"] == "John"
        assert response.data["display_name"] == "John"
        assert "has_avatar" in response.data

    def test_get_profile_includes_preferences(self, authenticated_client, profile_url):
        """Response includes preferences."""
        response = authenticated_client.get(profile_url)

        assert response.status_code == status.HTTP_200_OK
        assert "timezone" in response.data
        assert "language" in response.data


@pytest.mark.django_db
class TestProfileViewPatch:
    """Tests for PATCH /api/v1/users/me/profile/."""

    def test_patch_profile_requires_auth(self, api_client, profile_url):
        """Unauthenticated request returns 401."""
        response = api_client.patch(profile_url, {"first_name": "John"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_profile_first_name(self, authenticated_client, user, profile_url):
        """Can update first name."""
        response = authenticated_client.patch(profile_url, {"first_name": "John"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "John"
        user.profile.refresh_from_db()
        assert user.profile.first_name == "John"

    def test_patch_profile_last_name(self, authenticated_client, user, profile_url):
        """Can update last name."""
        response = authenticated_client.patch(profile_url, {"last_name": "Doe"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["last_name"] == "Doe"

    def test_patch_profile_phone(self, authenticated_client, user, profile_url):
        """Can update phone."""
        response = authenticated_client.patch(profile_url, {"phone": "+1234567890"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["phone"] == "+1234567890"

    def test_patch_profile_timezone(self, authenticated_client, user, profile_url):
        """Can update timezone."""
        response = authenticated_client.patch(
            profile_url, {"timezone": "America/New_York"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["timezone"] == "America/New_York"

    def test_patch_profile_invalid_timezone(self, authenticated_client, profile_url):
        """Invalid timezone returns 400."""
        response = authenticated_client.patch(profile_url, {"timezone": "Invalid/Zone"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "timezone" in response.data.get("error", {}).get("details", {})

    def test_patch_profile_language(self, authenticated_client, user, profile_url):
        """Can update language."""
        response = authenticated_client.patch(profile_url, {"language": "es"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["language"] == "es"

    def test_patch_profile_multiple_fields(
        self, authenticated_client, user, profile_url
    ):
        """Can update multiple fields."""
        response = authenticated_client.patch(
            profile_url,
            {"first_name": "John", "last_name": "Doe", "phone": "+1234567890"},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "John"
        assert response.data["last_name"] == "Doe"
        assert response.data["phone"] == "+1234567890"

    def test_patch_profile_empty_body(self, authenticated_client, user, profile_url):
        """Empty body returns 200 with unchanged data."""
        user.profile.first_name = "Original"
        user.profile.save()

        response = authenticated_client.patch(profile_url, {})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Original"


# =============================================================================
# AVATAR VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestAvatarViewPost:
    """Tests for POST /api/v1/users/me/avatar/."""

    def test_upload_avatar_requires_auth(self, api_client, avatar_url, sample_image):
        """Unauthenticated request returns 401."""
        response = api_client.post(
            avatar_url, {"avatar": sample_image}, format="multipart"
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_avatar_success(
        self, authenticated_client, user, avatar_url, sample_image
    ):
        """Can upload avatar."""
        response = authenticated_client.post(
            avatar_url, {"avatar": sample_image}, format="multipart"
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["has_avatar"] is True
        assert response.data["avatar_url"] is not None

    def test_upload_avatar_jpeg(
        self, authenticated_client, avatar_url, sample_jpeg_image
    ):
        """Can upload JPEG avatar."""
        response = authenticated_client.post(
            avatar_url, {"avatar": sample_jpeg_image}, format="multipart"
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_upload_avatar_invalid_file(
        self, authenticated_client, avatar_url, invalid_file
    ):
        """Invalid file type returns 400."""
        response = authenticated_client.post(
            avatar_url, {"avatar": invalid_file}, format="multipart"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "avatar" in response.data.get("error", {}).get("details", {})

    def test_upload_avatar_no_file(self, authenticated_client, avatar_url):
        """Missing file returns 400."""
        response = authenticated_client.post(avatar_url, {}, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "avatar" in response.data.get("error", {}).get("details", {})

    def test_upload_avatar_replaces_existing(
        self, authenticated_client, user, avatar_url, sample_image, sample_jpeg_image
    ):
        """Uploading new avatar replaces existing."""
        # Upload first avatar
        authenticated_client.post(
            avatar_url, {"avatar": sample_image}, format="multipart"
        )

        # Upload second avatar
        response = authenticated_client.post(
            avatar_url, {"avatar": sample_jpeg_image}, format="multipart"
        )

        assert response.status_code == status.HTTP_201_CREATED
        user.profile.refresh_from_db()
        assert user.profile.has_avatar is True


@pytest.mark.django_db
class TestAvatarViewDelete:
    """Tests for DELETE /api/v1/users/me/avatar/."""

    def test_delete_avatar_requires_auth(self, api_client, avatar_url):
        """Unauthenticated request returns 401."""
        response = api_client.delete(avatar_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_avatar_success(
        self, authenticated_client, user, avatar_url, sample_image
    ):
        """Can delete avatar."""
        # First upload an avatar
        authenticated_client.post(
            avatar_url, {"avatar": sample_image}, format="multipart"
        )

        response = authenticated_client.delete(avatar_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        user.profile.refresh_from_db()
        assert user.profile.has_avatar is False

    def test_delete_avatar_when_none(self, authenticated_client, avatar_url):
        """Deleting non-existent avatar returns 204."""
        response = authenticated_client.delete(avatar_url)

        assert response.status_code == status.HTTP_204_NO_CONTENT


# =============================================================================
# PERMISSION TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserViewPermissions:
    """Tests for view permissions."""

    def test_verified_user_can_access(self, verified_client, me_url):
        """Verified user can access endpoints."""
        response = verified_client.get(me_url)
        assert response.status_code == status.HTTP_200_OK

    def test_staff_user_can_access(self, staff_client, me_url):
        """Staff user can access their own data."""
        response = staff_client.get(me_url)
        assert response.status_code == status.HTTP_200_OK

    def test_admin_user_can_access(self, admin_client, me_url):
        """Admin user can access their own data."""
        response = admin_client.get(me_url)
        assert response.status_code == status.HTTP_200_OK


# =============================================================================
# SERIALIZER OUTPUT TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserOutputSerializer:
    """Tests for UserOutputSerializer."""

    def test_user_output_has_expected_fields(self, authenticated_client, me_url):
        """User output has all expected fields."""
        response = authenticated_client.get(me_url)

        expected_fields = [
            "id",
            "email",
            "username",
            "is_active",
            "is_verified",
            "is_complete",
            "can_create_business",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "profile",
        ]

        for field in expected_fields:
            assert field in response.data

    def test_profile_output_has_expected_fields(
        self, authenticated_client, profile_url
    ):
        """Profile output has all expected fields."""
        response = authenticated_client.get(profile_url)

        expected_fields = [
            "first_name",
            "last_name",
            "full_name",
            "display_name",
            "phone",
            "avatar_url",
            "has_avatar",
            "timezone",
            "language",
        ]

        for field in expected_fields:
            assert field in response.data

    def test_avatar_url_is_absolute(
        self, authenticated_client, user, avatar_url, sample_image, profile_url
    ):
        """Avatar URL is absolute when avatar exists."""
        # Upload avatar
        authenticated_client.post(
            avatar_url, {"avatar": sample_image}, format="multipart"
        )

        response = authenticated_client.get(profile_url)

        avatar_url_value = response.data["avatar_url"]
        assert avatar_url_value.startswith("http")

    def test_avatar_url_is_none_without_avatar(self, authenticated_client, profile_url):
        """Avatar URL is None when no avatar."""
        response = authenticated_client.get(profile_url)

        assert response.data["avatar_url"] is None


# =============================================================================
# CHECK USERNAME VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestCheckUsernameView:
    """Tests for GET /api/v1/users/check-username/."""

    def test_requires_authentication(self, api_client, check_username_url):
        """Unauthenticated request returns 401."""
        response = api_client.get(check_username_url, {"username": "testname"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_available_username(self, authenticated_client, check_username_url):
        """Available username returns available=True, is_current=False."""
        response = authenticated_client.get(
            check_username_url, {"username": "uniquename123"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["available"] is True
        assert response.data["is_current"] is False

    def test_taken_username(
        self, authenticated_client, user_factory, check_username_url
    ):
        """Taken username returns available=False."""
        user_factory(username="taken_name")

        response = authenticated_client.get(
            check_username_url, {"username": "taken_name"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["available"] is False
        assert response.data["is_current"] is False

    def test_own_username(self, authenticated_client, user, check_username_url):
        """Own username returns available=True, is_current=True."""
        response = authenticated_client.get(
            check_username_url, {"username": user.username}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["available"] is True
        assert response.data["is_current"] is True

    def test_case_insensitive_taken(
        self, authenticated_client, user_factory, check_username_url
    ):
        """Username check is case-insensitive."""
        user_factory(username="takenname")

        response = authenticated_client.get(
            check_username_url, {"username": "TakenName"}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["available"] is False

    def test_case_insensitive_own(self, authenticated_client, user, check_username_url):
        """Own username check is case-insensitive."""
        response = authenticated_client.get(
            check_username_url,
            {"username": user.username.upper()},
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data["available"] is True
        assert response.data["is_current"] is True

    def test_invalid_format_too_short(self, authenticated_client, check_username_url):
        """Username shorter than 3 characters returns 400."""
        response = authenticated_client.get(check_username_url, {"username": "ab"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_format_special_chars(
        self, authenticated_client, check_username_url
    ):
        """Username with special characters returns 400."""
        response = authenticated_client.get(
            check_username_url, {"username": "user@name"}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_username_param(self, authenticated_client, check_username_url):
        """Missing username parameter returns 400."""
        response = authenticated_client.get(check_username_url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_empty_username_param(self, authenticated_client, check_username_url):
        """Empty username parameter returns 400."""
        response = authenticated_client.get(check_username_url, {"username": ""})
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# PUBLIC USER PROFILE VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserPublicDetailViewAuth:
    """Auth and access control tests for GET /api/v1/users/<username>/."""

    def test_requires_auth(self, api_client, public_profile_url, another_user):
        """Unauthenticated request returns 401."""
        response = api_client.get(public_profile_url(another_user.username))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_active_public_user_success(
        self, authenticated_client, public_profile_url, another_user
    ):
        """Authenticated user can view another active public user's profile."""
        response = authenticated_client.get(public_profile_url(another_user.username))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == another_user.username

    def test_nonexistent_user_returns_404(
        self, authenticated_client, public_profile_url
    ):
        """Non-existent username returns 404."""
        response = authenticated_client.get(public_profile_url("nonexistent_user_xyz"))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_inactive_user_returns_404(
        self, authenticated_client, public_profile_url, inactive_user
    ):
        """Inactive user returns 404 for regular users."""
        response = authenticated_client.get(public_profile_url(inactive_user.username))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_private_profile_returns_limited(
        self, authenticated_client, public_profile_url, another_user
    ):
        """User with is_public=False returns limited data (not 404)."""
        another_user.profile.is_public = False
        another_user.profile.save(update_fields=["is_public"])

        response = authenticated_client.get(public_profile_url(another_user.username))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_limited"] is True
        assert response.data["username"] == another_user.username
        assert "profile" in response.data
        # T1 fields are visible even on limited profiles
        assert "display_name" in response.data["profile"]
        assert "avatar_url" in response.data["profile"]
        assert "bio" in response.data["profile"]
        assert "tags" in response.data["profile"]
        assert "is_public" in response.data["profile"]
        # T3 fields still excluded on limited profiles
        assert "phone" not in response.data["profile"]
        assert "timezone" not in response.data["profile"]
        assert "language" not in response.data["profile"]
        # _permissions always injected
        assert "_permissions" in response.data

    def test_own_private_profile_visible(
        self, authenticated_client, user, public_profile_url
    ):
        """User can always view own profile even if is_public=False."""
        user.profile.is_public = False
        user.profile.save(update_fields=["is_public"])

        response = authenticated_client.get(public_profile_url(user.username))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == user.username

    def test_staff_can_view_private_profile(
        self, staff_client, public_profile_url, another_user
    ):
        """Staff can view private profiles."""
        another_user.profile.is_public = False
        another_user.profile.save(update_fields=["is_public"])

        response = staff_client.get(public_profile_url(another_user.username))
        assert response.status_code == status.HTTP_200_OK

    def test_staff_can_view_inactive_user(
        self, staff_client, public_profile_url, inactive_user
    ):
        """Staff can view inactive users."""
        response = staff_client.get(public_profile_url(inactive_user.username))
        assert response.status_code == status.HTTP_200_OK

    def test_case_insensitive_username(
        self, authenticated_client, public_profile_url, another_user
    ):
        """Username lookup is case-insensitive."""
        response = authenticated_client.get(
            public_profile_url(another_user.username.upper())
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == another_user.username


@pytest.mark.django_db
class TestUserPublicDetailViewResponse:
    """Response structure tests for GET /api/v1/users/<username>/."""

    def test_response_includes_profile(
        self, authenticated_client, public_profile_url, another_user
    ):
        """Response includes nested profile with discovery fields."""
        another_user.profile.first_name = "Jane"
        another_user.profile.last_name = "Smith"
        another_user.profile.bio = "A developer"
        another_user.profile.country = "US"
        another_user.profile.city = "New York"
        another_user.profile.tags = ["developer"]
        another_user.profile.save()

        response = authenticated_client.get(public_profile_url(another_user.username))

        assert response.status_code == status.HTTP_200_OK
        profile = response.data["profile"]
        assert profile["first_name"] == "Jane"
        assert profile["last_name"] == "Smith"
        assert profile["bio"] == "A developer"
        assert profile["country"] == "US"
        assert profile["city"] == "New York"
        assert profile["tags"] == ["developer"]
        assert "display_name" in profile
        assert "full_name" in profile
        assert "avatar_url" in profile
        assert "has_avatar" in profile

    def test_response_excludes_private_fields(
        self, authenticated_client, public_profile_url, another_user
    ):
        """Response does not contain email, phone, timezone, language."""
        response = authenticated_client.get(public_profile_url(another_user.username))

        assert response.status_code == status.HTTP_200_OK
        # User-level private fields
        assert "email" not in response.data
        assert "is_staff" not in response.data
        assert "is_superuser" not in response.data
        assert "is_active" not in response.data
        assert "can_create_business" not in response.data
        assert "last_login" not in response.data
        # Profile-level private fields
        profile = response.data["profile"]
        assert "phone" not in profile
        assert "timezone" not in profile
        assert "language" not in profile

    def test_is_verified_included(
        self, authenticated_client, public_profile_url, another_user
    ):
        """Response includes is_verified flag."""
        response = authenticated_client.get(public_profile_url(another_user.username))
        assert "is_verified" in response.data

    def test_date_joined_included(
        self, authenticated_client, public_profile_url, another_user
    ):
        """Response includes date_joined."""
        response = authenticated_client.get(public_profile_url(another_user.username))
        assert "date_joined" in response.data

    def test_is_public_field_in_profile(
        self, authenticated_client, public_profile_url, another_user
    ):
        """Response profile contains is_public field."""
        response = authenticated_client.get(public_profile_url(another_user.username))
        assert "is_public" in response.data["profile"]
        assert response.data["profile"]["is_public"] is True


@pytest.mark.django_db
class TestUserPublicDetailViewPermissions:
    """Permission injection tests for GET /api/v1/users/<username>/."""

    def test_permissions_for_own_profile(
        self, authenticated_client, user, public_profile_url
    ):
        """Viewing own profile returns is_own_profile=True, can_edit_profile=True."""
        response = authenticated_client.get(public_profile_url(user.username))

        assert response.status_code == status.HTTP_200_OK
        perms = response.data["_permissions"]
        assert perms["is_own_profile"] is True
        assert perms["can_edit_profile"] is True

    def test_permissions_for_other_profile(
        self, authenticated_client, public_profile_url, another_user
    ):
        """Viewing another user's profile returns is_own_profile=False, can_edit_profile=False."""
        response = authenticated_client.get(public_profile_url(another_user.username))

        assert response.status_code == status.HTTP_200_OK
        perms = response.data["_permissions"]
        assert perms["is_own_profile"] is False
        assert perms["can_edit_profile"] is False

    def test_user_without_profile_returns_limited(
        self, authenticated_client, public_profile_url, db
    ):
        """User without a profile record returns limited data (active but no profile)."""
        from apps.users.tests.factories import UserFactory

        target = UserFactory()
        # Delete profile if auto-created
        from apps.users.models import UserProfile

        UserProfile.objects.filter(user=target).delete()

        response = authenticated_client.get(public_profile_url(target.username))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_limited"] is True
        assert response.data["username"] == target.username

    def test_own_profile_without_profile_record(
        self, authenticated_client, user, public_profile_url, db
    ):
        """Viewing own profile without profile record still returns 200 (self-bypass)."""
        from apps.users.models import UserProfile

        UserProfile.objects.filter(user=user).delete()

        response = authenticated_client.get(public_profile_url(user.username))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["profile"] is None


# =============================================================================
# VISIBILITY + CONNECTION-BASED ACCESS TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserVisibilityAccess:
    """Tests for visibility-based access control on user profiles."""

    def test_connected_user_can_view_private_profile(
        self, api_client, public_profile_url, db
    ):
        """Connected user can view a private profile in full (not limited)."""
        from unittest.mock import patch

        from apps.users.tests.factories import UserFactory

        viewer = UserFactory()
        target = UserFactory()
        target.profile.is_public = False
        target.profile.save(update_fields=["is_public"])

        api_client.force_authenticate(user=viewer)

        with patch(
            "apps.network.selectors.ConnectionSelector.is_connected",
            return_value=True,
        ):
            response = api_client.get(public_profile_url(target.username))

        assert response.status_code == status.HTTP_200_OK
        assert "is_limited" not in response.data
        assert response.data["username"] == target.username
        assert "profile" in response.data
        assert "bio" in response.data["profile"]
        assert "tags" in response.data["profile"]

    def test_non_connected_user_sees_limited_private_profile(
        self, api_client, public_profile_url, db
    ):
        """Non-connected user sees limited view of private profile."""
        from unittest.mock import patch

        from apps.users.tests.factories import UserFactory

        viewer = UserFactory()
        target = UserFactory()
        target.profile.is_public = False
        target.profile.save(update_fields=["is_public"])

        api_client.force_authenticate(user=viewer)

        with patch(
            "apps.network.selectors.ConnectionSelector.is_connected",
            return_value=False,
        ):
            response = api_client.get(public_profile_url(target.username))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_limited"] is True

    def test_limited_profile_always_has_permissions(
        self, api_client, public_profile_url, db
    ):
        """_permissions is injected even on limited profile responses."""
        from unittest.mock import patch

        from apps.users.tests.factories import UserFactory

        viewer = UserFactory()
        target = UserFactory()
        target.profile.is_public = False
        target.profile.save(update_fields=["is_public"])

        api_client.force_authenticate(user=viewer)

        with patch(
            "apps.network.selectors.ConnectionSelector.is_connected",
            return_value=False,
        ):
            response = api_client.get(public_profile_url(target.username))

        assert response.status_code == status.HTTP_200_OK
        assert "_permissions" in response.data
        assert response.data["_permissions"]["is_own_profile"] is False
        assert response.data["_permissions"]["can_edit_profile"] is False

    def test_limited_profile_always_has_relationship(
        self, api_client, public_profile_url, db
    ):
        """_relationship is injected even on limited profile responses."""
        from unittest.mock import patch

        from apps.users.tests.factories import UserFactory

        viewer = UserFactory()
        target = UserFactory()
        target.profile.is_public = False
        target.profile.save(update_fields=["is_public"])

        api_client.force_authenticate(user=viewer)

        with (
            patch(
                "apps.network.selectors.ConnectionSelector.is_connected",
                return_value=False,
            ),
            patch(
                "apps.network.selectors.ConnectionSelector.get_connection_between_users",
                return_value=None,
            ),
            patch(
                "apps.transaction.selectors.TransactionSelector.has_active_in_conflict_group",
                return_value=None,
            ),
        ):
            response = api_client.get(public_profile_url(target.username))

        assert response.status_code == status.HTTP_200_OK
        assert "_relationship" in response.data

    def test_relationship_includes_connection_id_when_connected(
        self, api_client, public_profile_url, db
    ):
        """Connected users see connection_id in _relationship."""
        from unittest.mock import MagicMock, patch

        from apps.users.tests.factories import UserFactory

        viewer = UserFactory()
        target = UserFactory()

        mock_connection = MagicMock()
        mock_connection.status = "active"
        mock_connection.id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

        api_client.force_authenticate(user=viewer)

        with (
            patch(
                "apps.network.selectors.ConnectionSelector.is_connected",
                return_value=True,
            ),
            patch(
                "apps.network.selectors.ConnectionSelector.get_connection_between_users",
                return_value=mock_connection,
            ),
            patch(
                "apps.transaction.selectors.TransactionSelector.has_active_in_conflict_group",
                return_value=None,
            ),
        ):
            response = api_client.get(public_profile_url(target.username))

        assert response.status_code == status.HTTP_200_OK
        rel = response.data["_relationship"]
        assert rel["connection_status"] == "active"
        assert rel["connection_id"] == "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    def test_pending_connection_request_includes_viewer_role(
        self, api_client, public_profile_url, db
    ):
        """Pending connection request shows viewer_role in _relationship."""
        from unittest.mock import MagicMock, patch

        from apps.users.tests.factories import UserFactory

        viewer = UserFactory()
        target = UserFactory()

        mock_txn = MagicMock()
        mock_txn.id = "11111111-2222-3333-4444-555555555555"
        mock_txn.transaction_type = "user_connection_request"
        mock_txn.status = "pending"
        mock_txn.mode = "request"
        mock_txn.initiator_id = viewer.id
        mock_txn.target_id = target.id

        api_client.force_authenticate(user=viewer)

        with (
            patch(
                "apps.network.selectors.ConnectionSelector.is_connected",
                return_value=False,
            ),
            patch(
                "apps.network.selectors.ConnectionSelector.get_connection_between_users",
                return_value=None,
            ),
            patch(
                "apps.transaction.selectors.TransactionSelector.has_active_in_conflict_group",
                return_value=mock_txn,
            ),
        ):
            response = api_client.get(public_profile_url(target.username))

        assert response.status_code == status.HTTP_200_OK
        rel = response.data["_relationship"]
        assert rel["active_connection_transaction"] is not None
        assert rel["active_connection_transaction"]["viewer_role"] == "initiator"

    def test_limited_profile_includes_all_t1_fields(
        self, api_client, public_profile_url, db
    ):
        """Limited profile includes all T1 user profile fields."""
        from unittest.mock import patch

        from apps.users.tests.factories import UserFactory

        viewer = UserFactory()
        target = UserFactory()
        target.profile.first_name = "Jane"
        target.profile.last_name = "Smith"
        target.profile.bio = "A developer"
        target.profile.country = "US"
        target.profile.city = "New York"
        target.profile.tags = ["developer"]
        target.profile.is_public = False
        target.profile.save()

        api_client.force_authenticate(user=viewer)

        with patch(
            "apps.network.selectors.ConnectionSelector.is_connected",
            return_value=False,
        ):
            response = api_client.get(public_profile_url(target.username))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_limited"] is True
        profile = response.data["profile"]
        # All T1 fields present
        assert profile["first_name"] == "Jane"
        assert profile["last_name"] == "Smith"
        assert profile["display_name"] == "Jane Smith"
        assert profile["full_name"] == "Jane Smith"
        assert profile["bio"] == "A developer"
        assert profile["country"] == "US"
        assert profile["city"] == "New York"
        assert profile["tags"] == ["developer"]
        assert profile["is_public"] is False
        assert "avatar_url" in profile
        assert "has_avatar" in profile
        assert "cover_image_url" in profile
        assert "has_cover_image" in profile
        # T3 fields excluded
        assert "phone" not in profile
        assert "timezone" not in profile
        assert "language" not in profile


# =============================================================================
# USER PROFILE VISIBILITY SETTINGS TESTS
# =============================================================================


@pytest.mark.django_db
class TestUserProfileVisibilityView:
    """Tests for GET/PATCH /api/v1/users/me/profile/visibility/"""

    URL = "/api/v1/users/me/profile/visibility/"

    def test_get_returns_empty_list(self, authenticated_client):
        """GET returns empty list (no T2 fields for users currently)."""
        response = authenticated_client.get(self.URL)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_unauthenticated_cannot_access(self, api_client):
        """Unauthenticated users cannot access visibility settings."""
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_rejects_any_field(self, authenticated_client):
        """PATCH rejects any field name (no T2 fields exist for users)."""
        response = authenticated_client.patch(
            self.URL,
            {"overrides": {"bio": 1}},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# APPROVED BUSINESS CREATORS LIST VIEW TESTS
# =============================================================================


@pytest.mark.django_db
class TestApprovedBusinessCreatorsListView:
    """Tests for GET /api/v1/platform/approved-creators/."""

    URL = "/api/v1/platform/approved-creators/"

    @pytest.fixture
    def platform(self, db):
        from apps.organization.platform.models import PlatformAccount
        from apps.organization.tests.factories import PlatformAccountFactory

        try:
            return PlatformAccount.objects.get()
        except PlatformAccount.DoesNotExist:
            return PlatformAccountFactory()

    @pytest.fixture
    def platform_owner_role(self, db, platform):
        from apps.core.constants import AccountType
        from apps.rbac.models import Role

        return Role.objects.create(
            name="Platform Owner",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=0,
            is_system_role=True,
        )

    @pytest.fixture
    def platform_admin_role(self, db, platform):
        from apps.core.constants import AccountType
        from apps.rbac.models import Role

        return Role.objects.create(
            name="Platform Admin",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=2,
            is_system_role=False,
        )

    @pytest.fixture
    def platform_base_member_role(self, db, platform):
        from apps.core.constants import AccountType
        from apps.rbac.models import Role

        return Role.objects.create(
            name="Global Moderator",
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            level=5,
            is_system_role=False,
        )

    @pytest.fixture
    def approve_perm(self, db):
        from apps.rbac.models import Permission

        perm, _ = Permission.objects.get_or_create(
            code="can_approve_business_creation",
            defaults={
                "name": "Approve Business Creation",
                "description": "Approve new business account creation requests",
                "category": "platform",
            },
        )
        return perm

    @pytest.fixture
    def platform_owner_membership(
        self, db, user, platform, platform_owner_role, approve_perm
    ):
        from apps.core.constants import MembershipStatus
        from apps.rbac.models import Membership, RolePermission

        membership = Membership.objects.create(
            user=user,
            account_type=platform_owner_role.account_type,
            account_id=platform_owner_role.account_id,
            role=platform_owner_role,
            is_owner=True,
            status=MembershipStatus.ACTIVE,
        )
        RolePermission.objects.get_or_create(
            role=platform_owner_role,
            permission=approve_perm,
            defaults={"scope": "platform_only"},
        )
        return membership

    @pytest.fixture
    def platform_base_membership(
        self, db, another_user, platform, platform_base_member_role
    ):
        from apps.core.constants import MembershipStatus
        from apps.rbac.models import Membership

        return Membership.objects.create(
            user=another_user,
            account_type=platform_base_member_role.account_type,
            account_id=platform_base_member_role.account_id,
            role=platform_base_member_role,
            is_owner=False,
            status=MembershipStatus.ACTIVE,
        )

    @pytest.fixture
    def approved_creators(self, db):
        """Create users with can_create_business=True."""
        from apps.users.tests.factories import UserFactory

        u1 = UserFactory(
            email="alice_creator@test.com",
            username="alice_creator",
            can_create_business=True,
        )
        u1.profile.first_name = "Alice"
        u1.profile.last_name = "Creator"
        u1.profile.save()

        u2 = UserFactory(
            email="bob_creator@test.com",
            username="bob_creator",
            can_create_business=True,
        )
        u2.profile.first_name = "Bob"
        u2.profile.last_name = "Builder"
        u2.profile.save()

        return [u1, u2]

    # --- Access control ---

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated request returns 401."""
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_non_platform_member_returns_403(self, authenticated_client):
        """User without platform membership gets 403."""
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_platform_member_without_permission_returns_403(
        self, api_client, platform_base_membership
    ):
        """Platform member without can_approve_business_creation gets 403."""
        api_client.force_authenticate(user=platform_base_membership.user)
        response = api_client.get(self.URL)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_platform_owner_with_permission_returns_200(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Platform owner with permission gets 200 and results."""
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2

    # --- Filtering ---

    def test_only_approved_creators_returned(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Only users with can_create_business=True are returned."""
        from apps.users.tests.factories import UserFactory

        # Create a user without permission
        UserFactory(
            email="noperm@test.com",
            username="noperm_user",
            can_create_business=False,
        )

        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2  # Only the 2 approved creators

        usernames = [r["username"] for r in response.data["results"]]
        assert "noperm_user" not in usernames

    def test_search_by_name(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Search filters by name."""
        response = authenticated_client.get(self.URL, {"search": "Alice"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["username"] == "alice_creator"

    def test_search_by_email(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Search filters by email."""
        response = authenticated_client.get(self.URL, {"search": "bob_creator@"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1
        assert response.data["results"][0]["username"] == "bob_creator"

    def test_search_by_username(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Search filters by username."""
        response = authenticated_client.get(self.URL, {"search": "alice_creator"})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    # --- Ordering ---

    def test_ordering_by_name(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Ordering=name sorts by first_name."""
        response = authenticated_client.get(self.URL, {"ordering": "name"})
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert results[0]["display_name"] == "Alice Creator"
        assert results[1]["display_name"] == "Bob Builder"

    def test_ordering_by_email(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Ordering=email sorts by email."""
        response = authenticated_client.get(self.URL, {"ordering": "email"})
        assert response.status_code == status.HTTP_200_OK
        results = response.data["results"]
        assert results[0]["email"] == "alice_creator@test.com"
        assert results[1]["email"] == "bob_creator@test.com"

    # --- Response structure ---

    def test_response_structure(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Response contains expected fields."""
        response = authenticated_client.get(self.URL)
        assert response.status_code == status.HTTP_200_OK

        result = response.data["results"][0]
        expected_fields = [
            "id",
            "email",
            "username",
            "display_name",
            "avatar_url",
            "can_create_business",
            "date_joined",
        ]
        for field in expected_fields:
            assert field in result, f"Missing field: {field}"

        assert result["can_create_business"] is True

    # --- Pagination ---

    def test_pagination_works(
        self, authenticated_client, platform_owner_membership, approved_creators
    ):
        """Pagination limits results."""
        response = authenticated_client.get(self.URL, {"page_size": 1})
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        assert len(response.data["results"]) == 1
        assert response.data["next"] is not None
