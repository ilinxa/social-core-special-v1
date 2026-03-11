"""
User Views
==========
API views for user and profile management.

Most views require authentication. Users can only access their own data,
except UserPublicDetailView which lets authenticated users view other profiles.
"""

import re

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import NotFound, ValidationError
from apps.core.permissions import IsAuthenticated
from apps.core.views import PermissionInjectMixin, RelationshipInjectMixin
from apps.core.visibility.resolver import VisibilityResolver
from apps.core.visibility.serializers import VisibilityOverrideInput
from apps.users.policies import UserPolicy
from apps.users.selectors import UserSelector
from apps.users.serializers import (
    AvatarUploadInputSerializer,
    CoverImageUploadInputSerializer,
    ProfileUpdateInputSerializer,
    UserOutputSerializer,
    UserProfileOutputSerializer,
    UserPublicOutput,
    UserLimitedOutput,
    UserUpdateInputSerializer,
)
from apps.users.services import UserService


class CurrentUserView(APIView):
    """
    API endpoint for current user operations.

    GET /api/v1/users/me/
        Get current user's data with profile

    PATCH /api/v1/users/me/
        Update current user's basic data (username)

    DELETE /api/v1/users/me/
        Deactivate current user's account
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get current user",
        description="""
        Retrieve the authenticated user's profile and account information.

        **Response includes:**
        - User account data (email, username, verification status)
        - Nested profile data (name, phone, avatar, preferences)
        - Account completion status
        """,
        tags=["User"],
        responses={
            200: OpenApiResponse(
                response=UserOutputSerializer,
                description="Current user data with profile"
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """Get current user data."""
        user = UserSelector.get_by_id(
            user_id=request.user.id,
            with_profile=True
        )
        serializer = UserOutputSerializer(user, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Update current user",
        description="""
        Update the authenticated user's basic account data.

        **Updatable fields:**
        - `username`: Unique username (3-30 alphanumeric characters or underscores)

        For profile data (name, phone, etc.), use PATCH /api/v1/users/me/profile/
        """,
        tags=["User"],
        request=UserUpdateInputSerializer,
        responses={
            200: OpenApiResponse(
                response=UserOutputSerializer,
                description="Updated user data"
            ),
            400: OpenApiResponse(description="Validation error (invalid username format)"),
            401: OpenApiResponse(description="Not authenticated"),
            409: OpenApiResponse(description="Username already taken"),
        },
    )
    def patch(self, request):
        """Update current user data."""
        serializer = UserUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        # Update username if provided
        if 'username' in serializer.validated_data:
            user = UserService.change_username(
                user=user,
                new_username=serializer.validated_data['username'],
                request=request,
            )

        # Re-fetch with profile for response
        user = UserSelector.get_by_id(user_id=user.id, with_profile=True)
        output = UserOutputSerializer(user, context={'request': request})
        return Response(output.data)

    @extend_schema(
        summary="Deactivate account",
        description="""
        Deactivate the authenticated user's account.

        **This action:**
        - Sets account to inactive (cannot login)
        - Preserves data for potential reactivation
        - Does NOT delete the account permanently

        To permanently delete, contact support.
        """,
        tags=["User"],
        responses={
            204: OpenApiResponse(description="Account deactivated"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def delete(self, request):
        """Deactivate current user account."""
        UserService.deactivate_user(user=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProfileView(APIView):
    """
    API endpoint for profile operations.

    GET /api/v1/users/me/profile/
        Get current user's profile

    PATCH /api/v1/users/me/profile/
        Update current user's profile
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get user profile",
        description="""
        Retrieve the authenticated user's profile information.

        **Response includes:**
        - Personal info (first_name, last_name, phone)
        - Avatar URL (if set)
        - Preferences (timezone, language)
        - Computed fields (full_name, display_name)
        """,
        tags=["User Profile"],
        responses={
            200: OpenApiResponse(
                response=UserProfileOutputSerializer,
                description="User profile data"
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """Get current user's profile."""
        profile = UserSelector.get_profile(user=request.user)
        serializer = UserProfileOutputSerializer(
            profile,
            context={'request': request}
        )
        return Response(serializer.data)

    @extend_schema(
        summary="Update user profile",
        description="""
        Update the authenticated user's profile information.

        **Updatable fields:**
        - `first_name`: User's first name
        - `last_name`: User's last name
        - `phone`: Phone number
        - `timezone`: User's timezone (e.g., "America/New_York")
        - `language`: Preferred language code (e.g., "en", "es")

        All fields are optional. Only provided fields are updated.
        """,
        tags=["User Profile"],
        request=ProfileUpdateInputSerializer,
        responses={
            200: OpenApiResponse(
                response=UserProfileOutputSerializer,
                description="Updated profile data"
            ),
            400: OpenApiResponse(description="Validation error (invalid timezone, etc.)"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def patch(self, request):
        """Update current user's profile."""
        serializer = ProfileUpdateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = UserService.update_profile(
            user=request.user,
            request=request,
            **serializer.validated_data
        )

        output = UserProfileOutputSerializer(
            profile,
            context={'request': request}
        )
        return Response(output.data)


class AvatarView(APIView):
    """
    API endpoint for avatar operations.

    POST /api/v1/users/me/avatar/
        Upload new avatar

    DELETE /api/v1/users/me/avatar/
        Remove avatar
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload avatar",
        description="""
        Upload a new avatar image for the authenticated user.

        **Requirements:**
        - File must be an image (JPEG, PNG, GIF, or WebP)
        - Maximum file size: 5MB
        - Images are automatically resized/optimized

        **Request:**
        Use multipart/form-data with the image in an `avatar` field.
        """,
        tags=["User Profile"],
        request=AvatarUploadInputSerializer,
        responses={
            201: OpenApiResponse(
                response=UserProfileOutputSerializer,
                description="Avatar uploaded successfully"
            ),
            400: OpenApiResponse(description="Invalid file (wrong type, too large, etc.)"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        """Upload new avatar."""
        serializer = AvatarUploadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = UserService.update_avatar(
            user=request.user,
            avatar=serializer.validated_data['avatar'],
            request=request,
        )

        output = UserProfileOutputSerializer(
            profile,
            context={'request': request}
        )
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Remove avatar",
        description="""
        Remove the authenticated user's avatar image.

        The avatar file is deleted and the user will have no avatar until
        a new one is uploaded.
        """,
        tags=["User Profile"],
        responses={
            204: OpenApiResponse(description="Avatar removed"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def delete(self, request):
        """Remove avatar."""
        UserService.remove_avatar(user=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CoverImageView(APIView):
    """
    API endpoint for cover image operations.

    POST /api/v1/users/me/cover-image/   Upload new cover image
    DELETE /api/v1/users/me/cover-image/  Remove cover image
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        summary="Upload cover image",
        description="Upload a new cover image. Max 5MB. JPEG, PNG, GIF, WebP.",
        tags=["User Profile"],
        request=CoverImageUploadInputSerializer,
        responses={
            201: OpenApiResponse(
                response=UserProfileOutputSerializer,
                description="Cover image uploaded successfully"
            ),
            400: OpenApiResponse(description="Invalid file"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        """Upload new cover image."""
        serializer = CoverImageUploadInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = UserService.update_cover_image(
            user=request.user,
            cover_image=serializer.validated_data['cover_image'],
            request=request,
        )

        output = UserProfileOutputSerializer(profile, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Remove cover image",
        description="Remove the authenticated user's cover image.",
        tags=["User Profile"],
        responses={
            204: OpenApiResponse(description="Cover image removed"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def delete(self, request):
        """Remove cover image."""
        UserService.remove_cover_image(user=request.user, request=request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class CheckUsernameView(APIView):
    """
    API endpoint for username availability check.

    GET /api/v1/users/check-username/?username=xxx
        Check if a username is available
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Check username availability",
        description="""
        Check if a username is available for the authenticated user.

        Returns whether the username is available and whether it is the
        user's current username.
        """,
        tags=["User"],
        parameters=[
            OpenApiParameter(
                name="username",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="Username to check (3-30 alphanumeric characters or underscores)",
            ),
        ],
        responses={
            200: OpenApiResponse(description="Username availability result"),
            400: OpenApiResponse(description="Invalid username format"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """Check username availability."""
        username = request.query_params.get("username", "").strip()

        if not username:
            raise ValidationError(
                message="Username is required",
                field="username",
            )

        if not re.match(r'^[a-zA-Z0-9_]{5,30}$', username):
            raise ValidationError(
                message="Username must be 5-30 alphanumeric characters or underscores",
                field="username",
            )

        if request.user.username.lower() == username.lower():
            return Response({"available": True, "is_current": True})

        taken = UserSelector.username_exists(username=username)
        return Response({"available": not taken, "is_current": False})


class UserPublicDetailView(RelationshipInjectMixin, PermissionInjectMixin, APIView):
    """
    API endpoint for viewing another user's public profile.

    GET /api/v1/users/<username>/
        Get a user's public profile by username.

    Privacy rules:
        - Own profile: always full
        - Staff/superuser: can view any profile in full
        - Other users with is_public=True: full profile
        - Private profiles (is_public=False): limited response (username, avatar, display_name)
        - Inactive users or non-existent: 404
    """
    permission_classes = [IsAuthenticated]
    policy_class = UserPolicy

    def _build_policy_kwargs(self):
        return {"viewer": self.request.user, "target": self._target_user}

    def _build_relationship_data(self):
        from apps.network.selectors import ConnectionSelector
        from apps.transaction.selectors import TransactionSelector

        viewer = self.request.user
        target = self._target_user

        connection = ConnectionSelector.get_connection_between_users(
            user_a_id=viewer.id,
            user_b_id=target.id,
        )

        active_conn_txn = TransactionSelector.has_active_in_conflict_group(
            conflict_group="user_connection",
            user_id=viewer.id,
            context_type="user",
            context_id=None,
        )
        # Filter: only show txn if it involves this specific target user
        if active_conn_txn:
            involves_target = (
                active_conn_txn.target_id == target.id
                or active_conn_txn.initiator_id == target.id
            )
            if not involves_target:
                active_conn_txn = None

        return {
            "connection_status": connection.status if connection else None,
            "connection_id": str(connection.id) if connection else None,
            "active_connection_transaction": {
                "id": str(active_conn_txn.id),
                "type": active_conn_txn.transaction_type,
                "status": active_conn_txn.status,
                "mode": active_conn_txn.mode,
                "viewer_role": "initiator" if active_conn_txn.initiator_id == viewer.id else "target",
            } if active_conn_txn else None,
        }

    @extend_schema(
        summary="Get user public profile",
        description="""
        Retrieve a user's public profile by username.

        **Privacy:**
        - Only shows public discovery fields (no email, phone, timezone, language)
        - Private profiles return limited data (username, avatar, display_name) with `is_limited: true`
        - Own profile is always fully visible
        - Inactive users return 404

        **Response includes:**
        - User data (username, verification status, date joined)
        - Nested profile (name, bio, avatar, location, tags)
        - `_permissions` dict for UI gating (is_own_profile, can_edit_profile)
        """,
        tags=["User"],
        responses={
            200: OpenApiResponse(
                response=UserPublicOutput,
                description="User public profile with permissions"
            ),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="User not found or inactive"),
        },
    )
    def get(self, request, username):
        """Get user's public profile by username."""
        user = UserSelector.get_by_username(username=username, with_profile=True)

        # Always inject _permissions and _relationship for all response types
        self._target_user = user
        self._inject_permissions = True
        self._inject_relationship = True

        if not UserPolicy.can_view_profile(viewer=request.user, target=user):
            # User exists but is inactive — 404
            if not user.is_active:
                raise NotFound(resource="User", resource_id=username)
            # User is active but profile is private — return limited data
            serializer = UserLimitedOutput(user, context={"request": request})
            return Response(serializer.data)

        serializer = UserPublicOutput(user, context={"request": request})
        return Response(serializer.data)


class UserProfileVisibilityView(APIView):
    """
    API endpoint for user profile visibility settings.

    GET /api/v1/users/me/profile/visibility/
        Get T2 field visibility settings (empty for now — future-ready).

    PATCH /api/v1/users/me/profile/visibility/
        Update visibility overrides for T2 fields (empty for now — future-ready).
    """

    permission_classes = [IsAuthenticated]

    REGISTRY_KEY = "user_profile"

    @extend_schema(
        summary="Get user visibility settings",
        description="""
        Get the configurable visibility settings for the user's profile.

        Currently returns an empty list as users have no T2 (conditional)
        fields yet. This endpoint is future-ready for when user-configurable
        visibility fields are added.
        """,
        tags=["User Profile"],
        responses={
            200: OpenApiResponse(description="Visibility settings"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """Get visibility settings for user profile."""
        profile = request.user.profile
        settings = VisibilityResolver.get_visibility_settings(
            registry_key=self.REGISTRY_KEY,
            visibility_overrides=profile.visibility_overrides,
        )
        return Response(settings)

    @extend_schema(
        summary="Update user visibility settings",
        description="""
        Update the visibility overrides for T2 fields on the user's profile.

        Currently no T2 fields exist for users, so any field name in the
        overrides will be rejected. This endpoint is future-ready.
        """,
        tags=["User Profile"],
        request=VisibilityOverrideInput,
        responses={
            200: OpenApiResponse(description="Updated visibility settings"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def patch(self, request):
        """Update visibility overrides for user profile."""
        serializer = VisibilityOverrideInput(
            data=request.data,
            context={"registry_key": self.REGISTRY_KEY},
        )
        serializer.is_valid(raise_exception=True)

        profile = request.user.profile
        current_overrides = profile.visibility_overrides or {}
        current_overrides.update(serializer.validated_data["overrides"])
        profile.visibility_overrides = current_overrides
        profile.save(update_fields=["visibility_overrides", "updated_at"])

        settings = VisibilityResolver.get_visibility_settings(
            registry_key=self.REGISTRY_KEY,
            visibility_overrides=profile.visibility_overrides,
        )
        return Response(settings)
