# apps/organization/platform/views.py
"""
Platform Views - API endpoints for platform operations.

Endpoints:
    /api/v1/platform/account/     - Platform account management
    /api/v1/platform/profile/     - Platform profile management
    /api/v1/platform/settings/    - Platform settings management
"""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import PermissionDenied
from apps.core.permissions import AllowAny, IsAuthenticated
from apps.core.views import PermissionInjectMixin, RelationshipInjectMixin
from apps.organization.platform.policies import PlatformPolicy
from apps.organization.platform.selectors import (
    PlatformAccountSelector,
    PlatformProfileSelector,
)
from apps.organization.platform.serializers import (
    PlatformAccountOutput,
    PlatformConfigureInput,
    PlatformProfileOutput,
    PlatformProfileUpdateInput,
    PlatformSettingsUpdateInput,
)
from apps.organization.platform.services import (
    PlatformAccountService,
    PlatformProfileService,
)


def _build_platform_relationship(user, platform) -> dict:
    """Compute _relationship data for an authenticated user + platform."""
    from apps.core.constants import AccountType
    from apps.network.selectors import FollowSelector
    from apps.rbac.selectors import MembershipSelector
    from apps.transaction.selectors import TransactionSelector

    membership = MembershipSelector.get_membership_for_user_account(
        user=user,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
    )

    active_txn = TransactionSelector.has_active_in_conflict_group(
        conflict_group="platform_membership",
        user_id=user.id,
        context_type="platform",
        context_id=platform.id,
    )

    follow = FollowSelector.get_follow_for_user(
        follower_id=user.id,
        followee_type="platform",
        followee_id=platform.id,
    )

    active_follow_txn = TransactionSelector.has_active_in_conflict_group(
        conflict_group="platform_follow",
        user_id=user.id,
        context_type="platform",
        context_id=platform.id,
    )

    return {
        "membership_status": membership.status if membership else None,
        "active_transaction": (
            {
                "id": str(active_txn.id),
                "type": active_txn.transaction_type,
                "status": active_txn.status,
                "mode": active_txn.mode,
                "viewer_role": (
                    "initiator" if active_txn.initiator_id == user.id else "target"
                ),
            }
            if active_txn
            else None
        ),
        "follow_status": follow.status if follow else None,
        "follow_id": str(follow.id) if follow else None,
        "active_follow_transaction": (
            {
                "id": str(active_follow_txn.id),
                "type": active_follow_txn.transaction_type,
                "status": active_follow_txn.status,
                "mode": active_follow_txn.mode,
                "viewer_role": (
                    "initiator"
                    if active_follow_txn.initiator_id == user.id
                    else "target"
                ),
            }
            if active_follow_txn
            else None
        ),
    }


class PlatformAccountView(RelationshipInjectMixin, PermissionInjectMixin, APIView):
    """
    API endpoint for platform account operations.

    GET /api/v1/platform/account/
        Get the platform account (public).

    POST /api/v1/platform/account/
        Initial platform configuration (superuser only).
    """

    permission_classes = [AllowAny]
    policy_class = PlatformPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user}

    def _build_relationship_data(self):
        return _build_platform_relationship(self.request.user, self._resource)

    @extend_schema(
        summary="Get platform account",
        description="""
        Retrieve the platform account information.

        **Response includes:**
        - Platform ID and configuration status
        - Platform settings
        - Nested profile data (name, branding, contact)
        """,
        tags=["Platform"],
        responses={
            200: OpenApiResponse(
                response=PlatformAccountOutput,
                description="Platform account data",
            ),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Platform not configured"),
        },
    )
    def get(self, request):
        """Get platform account."""
        if not PlatformPolicy.can_view(user=request.user):
            raise PermissionDenied(
                message="You don't have permission to view platform information",
                action="view",
                resource="PlatformAccount",
            )

        platform = PlatformAccountSelector.get()
        self._resource = platform
        self._inject_permissions = True
        self._inject_relationship = True

        serializer = PlatformAccountOutput(platform, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        summary="Configure platform",
        description="""
        Initial platform configuration. Can only be done once.

        **Superuser only.**

        **Request body:**
        - `name`: Platform name (required)
        - `settings`: Platform-wide settings (optional)
        """,
        tags=["Platform"],
        request=PlatformConfigureInput,
        responses={
            201: OpenApiResponse(
                response=PlatformAccountOutput,
                description="Platform configured successfully",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized (superuser required)"),
            409: OpenApiResponse(description="Platform already configured"),
        },
    )
    def post(self, request):
        """Configure platform (one-time setup)."""
        if not PlatformPolicy.can_configure(user=request.user):
            raise PermissionDenied(
                message="Only superusers can configure the platform",
                action="configure",
                resource="PlatformAccount",
            )

        serializer = PlatformConfigureInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        platform = PlatformAccountService.configure(
            name=serializer.validated_data["name"],
            settings=serializer.validated_data.get("settings"),
            actor=request.user,
            request=request,
        )

        output = PlatformAccountOutput(platform, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class PlatformProfileView(PermissionInjectMixin, APIView):
    """
    API endpoint for platform profile operations.

    GET /api/v1/platform/profile/
        Get the platform profile.

    PATCH /api/v1/platform/profile/
        Update the platform profile (staff or RBAC members).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    policy_class = PlatformPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user}

    @extend_schema(
        summary="Get platform profile",
        description="""
        Retrieve the platform's public profile and branding information.

        **Response includes:**
        - Platform name and tagline
        - Branding (logo, colors)
        - Contact information
        - Social links
        """,
        tags=["Platform"],
        responses={
            200: OpenApiResponse(
                response=PlatformProfileOutput,
                description="Platform profile data",
            ),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Platform profile not found"),
        },
    )
    def get(self, request):
        """Get platform profile."""
        if not PlatformPolicy.can_view(user=request.user):
            raise PermissionDenied(
                message="You don't have permission to view platform information",
                action="view",
                resource="PlatformProfile",
            )

        profile = PlatformProfileSelector.get()
        self._resource = profile
        self._inject_permissions = True

        serializer = PlatformProfileOutput(profile, context={"request": request})
        return Response(serializer.data)

    @extend_schema(
        summary="Update platform profile",
        description="""
        Update the platform's profile and branding.

        **Staff or superuser only.**

        **Updatable fields:**
        - `name`, `tagline`, `description`
        - `logo`, `favicon` (image files)
        - `primary_color`, `secondary_color` (hex codes)
        - `contact_email`, `contact_phone`, `address`
        - `social_links` (JSON object)

        All fields are optional. Only provided fields are updated.
        """,
        tags=["Platform"],
        request=PlatformProfileUpdateInput,
        responses={
            200: OpenApiResponse(
                response=PlatformProfileOutput,
                description="Updated platform profile",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized (staff required)"),
        },
    )
    def patch(self, request):
        """Update platform profile."""
        if not PlatformPolicy.can_update_profile(user=request.user):
            raise PermissionDenied(
                message="Only staff can update the platform profile",
                action="update",
                resource="PlatformProfile",
            )

        serializer = PlatformProfileUpdateInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = PlatformProfileService.update(
            actor=request.user,
            request=request,
            **serializer.validated_data,
        )

        output = PlatformProfileOutput(profile, context={"request": request})
        return Response(output.data)


class PlatformSettingsView(APIView):
    """
    API endpoint for platform settings.

    PATCH /api/v1/platform/settings/
        Update platform settings (superuser only).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Update platform settings",
        description="""
        Update platform-wide settings.

        **Superuser only.**

        Settings are merged with existing values (not replaced).

        **Request body:**
        - `settings`: JSON object with settings to update/add
        """,
        tags=["Platform"],
        request=PlatformSettingsUpdateInput,
        responses={
            200: OpenApiResponse(
                response=PlatformAccountOutput,
                description="Updated platform account with new settings",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized (superuser required)"),
        },
    )
    def patch(self, request):
        """Update platform settings."""
        if not PlatformPolicy.can_update_settings(user=request.user):
            raise PermissionDenied(
                message="Only superusers can update platform settings",
                action="update_settings",
                resource="PlatformAccount",
            )

        serializer = PlatformSettingsUpdateInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        platform = PlatformAccountService.update_settings(
            settings=serializer.validated_data.get("settings"),
            open_member_request=serializer.validated_data.get("open_member_request"),
            actor=request.user,
            request=request,
        )

        output = PlatformAccountOutput(platform, context={"request": request})
        return Response(output.data)
