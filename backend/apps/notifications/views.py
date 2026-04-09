"""
Notification Views
==================
API views for notification preferences and history.
"""

from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.views import PermissionInjectMixin
from apps.notifications.models import NotificationLog
from apps.notifications.policies import NotificationPolicy
from apps.notifications.selectors import (
    NotificationLogSelector,
    NotificationPreferenceSelector,
)
from apps.notifications.serializers import (
    AllPreferencesSerializer,
    ConfigurableTypeSerializer,
    NotificationHistorySerializer,
    NotificationLogSerializer,
    NotificationPreferenceSerializer,
    NotificationPreferenceUpdateSerializer,
)
from apps.notifications.services import PreferenceService
from apps.notifications.types import get_configurable_types


class PreferencesView(APIView):
    """
    GET: Get all notification preferences for current user.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="notifications_preferences_list",
        summary="Get all notification preferences",
        description="""
        Retrieve all notification preferences for the authenticated user,
        grouped by category.

        **Categories:**
        - `account`: Account-related notifications (verification, security)
        - `activity`: Activity notifications (login alerts, etc.)
        - `marketing`: Marketing and promotional notifications

        **Response structure:**
        Each preference shows:
        - Notification type and display name
        - Description of what triggers this notification
        - Current channel settings (email, push, SMS)
        - Whether user can modify this preference
        """,
        tags=["Notifications"],
        responses={
            200: OpenApiResponse(
                response=AllPreferencesSerializer,
                description="Preferences grouped by category",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """Get all preferences grouped by category."""
        preferences = NotificationPreferenceSelector.get_user_preferences(
            user=request.user
        )
        serializer = AllPreferencesSerializer(preferences)
        return Response(serializer.data)


class PreferenceDetailView(APIView):
    """
    GET: Get specific notification preference.
    PATCH: Update notification preference.
    DELETE: Reset preference to defaults.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="notifications_preference_retrieve",
        summary="Get notification preference",
        description="""
        Retrieve preference settings for a specific notification type.

        **Response includes:**
        - Current channel settings (email_enabled, push_enabled, sms_enabled)
        - Notification type metadata
        - Whether user can configure this type
        """,
        tags=["Notifications"],
        parameters=[
            OpenApiParameter(
                name="notification_type",
                type=str,
                location=OpenApiParameter.PATH,
                description="Notification type identifier (e.g., 'welcome', 'new_login')",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=NotificationPreferenceSerializer,
                description="Preference details",
            ),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Unknown notification type"),
        },
    )
    def get(self, request, notification_type):
        """Get preference for a specific notification type."""
        preference = PreferenceService.get_preference(
            user=request.user, notification_type=notification_type
        )
        serializer = NotificationPreferenceSerializer(preference)
        return Response(serializer.data)

    @extend_schema(
        summary="Update notification preference",
        description="""
        Update channel settings for a specific notification type.

        **Updatable fields:**
        - `email_enabled`: Enable/disable email notifications
        - `push_enabled`: Enable/disable push notifications
        - `sms_enabled`: Enable/disable SMS notifications

        At least one field must be provided. Only provided fields are updated.

        **Note:** Some notification types (marked as non-configurable) cannot be disabled
        for security reasons (e.g., password reset confirmations).
        """,
        tags=["Notifications"],
        parameters=[
            OpenApiParameter(
                name="notification_type",
                type=str,
                location=OpenApiParameter.PATH,
                description="Notification type identifier",
            )
        ],
        request=NotificationPreferenceUpdateSerializer,
        responses={
            200: OpenApiResponse(
                response=NotificationPreferenceSerializer,
                description="Updated preference",
            ),
            400: OpenApiResponse(
                description="No fields provided or type not configurable"
            ),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Unknown notification type"),
        },
    )
    def patch(self, request, notification_type):
        """Update preference for a notification type."""
        serializer = NotificationPreferenceUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        PreferenceService.update_preference(
            user=request.user,
            notification_type=notification_type,
            request=request,
            **serializer.validated_data,
        )

        # Return updated preference
        result = PreferenceService.get_preference(
            user=request.user, notification_type=notification_type
        )
        return Response(NotificationPreferenceSerializer(result).data)

    @extend_schema(
        summary="Reset notification preference",
        description="""
        Reset a notification preference to system defaults.

        This removes any customizations the user has made for this notification type,
        reverting to the default channel settings defined by the system.
        """,
        tags=["Notifications"],
        parameters=[
            OpenApiParameter(
                name="notification_type",
                type=str,
                location=OpenApiParameter.PATH,
                description="Notification type identifier",
            )
        ],
        responses={
            204: OpenApiResponse(description="Preference reset to defaults"),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Unknown notification type"),
        },
    )
    def delete(self, request, notification_type):
        """Reset preference to defaults."""
        PreferenceService.reset_preference(
            user=request.user, notification_type=notification_type
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationHistoryView(PermissionInjectMixin, APIView):
    """
    GET: Get notification history for current user, optionally filtered by scope.
    Tier 1.5: injects _permissions for org-scoped requests.
    """

    permission_classes = [IsAuthenticated]
    policy_class = NotificationPolicy

    def _build_policy_kwargs(self):
        return {
            "user": self.request.user,
            "scope_type": self._scope_type,
            "scope_id": self._scope_id,
        }

    @extend_schema(
        summary="Get notification history",
        description="""
        Retrieve notification history for the authenticated user.

        **Query Parameters:**
        - `notification_type`: Filter by type (e.g., 'welcome', 'new_login')
        - `status`: Filter by status ('pending', 'sent', 'failed', 'partial')
        - `limit`: Maximum results (default: 50, max: 100)
        - `offset`: Number of results to skip (default: 0)
        - `scope_type`: Filter by scope ('user', 'business', 'platform')
        - `scope_id`: Filter by org UUID (required with business/platform scope)

        **Response includes:**
        - Notification type, scope, and status
        - Channels used (email, push, SMS)
        - Channel-specific results (success/failure per channel)
        - Timestamp
        - `_permissions` (only for org-scoped requests)
        """,
        tags=["Notifications"],
        parameters=[
            OpenApiParameter(
                name="notification_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by notification type",
                required=False,
            ),
            OpenApiParameter(
                name="status",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by status (pending, sent, failed, partial)",
                required=False,
            ),
            OpenApiParameter(
                name="limit",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Maximum results to return (default: 50, max: 100)",
                required=False,
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Number of results to skip (default: 0)",
                required=False,
            ),
            OpenApiParameter(
                name="scope_type",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by scope (user, business, platform)",
                required=False,
            ),
            OpenApiParameter(
                name="scope_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Filter by org UUID (required with business/platform scope)",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=NotificationHistorySerializer,
                description="Notification history",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """Get notification history with optional scope filtering."""
        notification_type = request.query_params.get("notification_type")

        # Validate status against valid choices
        valid_statuses = {s.value for s in NotificationLog.Status}
        status_filter = request.query_params.get("status")
        if status_filter and status_filter not in valid_statuses:
            status_filter = None

        # Parse and clamp limit (1-100, default 50)
        try:
            limit = min(max(int(request.query_params.get("limit", 50)), 1), 100)
        except (ValueError, TypeError):
            limit = 50

        # Parse and clamp offset (>= 0, default 0)
        try:
            offset = max(int(request.query_params.get("offset", 0)), 0)
        except (ValueError, TypeError):
            offset = 0

        # Parse scope params
        scope_type = request.query_params.get("scope_type")
        scope_id_str = request.query_params.get("scope_id")
        scope_id = None
        if scope_id_str:
            try:
                scope_id = UUID(scope_id_str)
            except (ValueError, TypeError):
                scope_id_str = None

        # Store for PermissionInjectMixin
        self._scope_type = scope_type or "user"
        self._scope_id = scope_id
        self._inject_permissions = scope_id is not None

        # RBAC: if org-scoped, verify membership (return empty, not 403)
        if scope_type and scope_type != "user" and scope_id:
            if not NotificationPolicy.can_view_scoped_notifications(
                user=request.user, scope_type=scope_type, scope_id=scope_id
            ):
                return Response({"notifications": [], "count": 0})

        notifications = NotificationLogSelector.get_user_history(
            user=request.user,
            notification_type=notification_type,
            status=status_filter,
            limit=limit,
            offset=offset,
            scope_type=scope_type,
            scope_id=scope_id,
        )

        serializer = NotificationLogSerializer(notifications, many=True)
        return Response(
            {
                "notifications": serializer.data,
                "count": len(serializer.data),
            }
        )


class NotificationScopesView(APIView):
    """
    GET: Get notification scopes summary for current user.
    Returns distinct scopes with notification counts.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get notification scopes summary",
        description="""
        Get distinct scopes where the user has notifications, with counts.
        Used by the frontend to show per-org notification badges.
        """,
        tags=["Notifications"],
        responses={
            200: OpenApiResponse(description="Scopes with counts"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """Get notification scopes with counts."""
        scopes = NotificationLogSelector.get_user_notification_scopes(user=request.user)
        return Response(
            {
                "scopes": list(scopes),
                "count": len(scopes),
            }
        )


class ConfigurableTypesView(APIView):
    """
    GET: Get list of configurable notification types.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List configurable notification types",
        description="""
        Get a list of all notification types that users can configure.

        **Response includes:**
        - Type name (identifier for API calls)
        - Display name (human-readable)
        - Description
        - Category
        - Default channels

        Use this to build a notification settings UI.
        """,
        tags=["Notifications"],
        responses={
            200: OpenApiResponse(description="List of configurable notification types"),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """Get all configurable notification types."""
        types = get_configurable_types()
        serializer = ConfigurableTypeSerializer(types, many=True)
        return Response(
            {
                "types": serializer.data,
                "count": len(serializer.data),
            }
        )
