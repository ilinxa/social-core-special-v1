# apps/rbac/views.py
"""
RBAC Views - API endpoints for role and membership management.

Contexts:
- Platform: /api/v1/platform/members/, /api/v1/platform/roles/
- Business: /api/v1/business/{slug}/members/, /api/v1/business/{slug}/roles/
- User: /api/v1/me/memberships/
"""

from uuid import UUID

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.core.constants import AccountType, MembershipStatus
from apps.core.exceptions import NotFound, PermissionDenied
from apps.core.pagination import StandardPagination
from apps.core.views import PermissionInjectMixin
from apps.organization.business.models import BusinessAccount
from apps.organization.platform.models import PlatformAccount

from apps.rbac.models import Permission
from apps.rbac.policies import MembershipPolicy, RolePolicy
from apps.rbac.selectors import (
    PermissionSelector,
    RoleSelector,
    MembershipSelector,
)
from apps.rbac.services import RBACService
from apps.rbac.serializers import (
    PermissionOutputSerializer,
    RoleOutputSerializer,
    RoleDetailOutputSerializer,
    MembershipOutputSerializer,
    MembershipListOutputSerializer,
    MyMembershipOutputSerializer,
    RoleCreateInputSerializer,
    RoleUpdateInputSerializer,
    RolePermissionAddInputSerializer,
    RolePermissionRemoveInputSerializer,
    MembershipRoleChangeInputSerializer,
    MembershipStatusChangeInputSerializer,
    MemberActionReasonInputSerializer,
)


# =============================================================================
# MIXINS
# =============================================================================

class AccountContextMixin:
    """
    Mixin to resolve account context and build actor context.

    Subclasses must implement:
    - get_account_type() -> str
    - get_account_id() -> UUID
    """

    def get_account_type(self) -> str:
        raise NotImplementedError

    def get_account_id(self) -> UUID:
        raise NotImplementedError

    def get_actor_context(self):
        """Get the actor's context for this account."""
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=self.request.user,
            account_type=self.get_account_type(),
            account_id=self.get_account_id(),
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a member of this account",
            )
        return RBACService.build_actor_context(
            membership=membership,
            request=self.request,
        )


class BusinessContextMixin(AccountContextMixin):
    """Mixin for business context views."""

    _business = None

    def get_business(self) -> BusinessAccount:
        """Get the business from the URL slug."""
        if self._business is None:
            slug = self.kwargs.get("business_slug")
            try:
                self._business = BusinessAccount.objects.get(slug=slug)
            except BusinessAccount.DoesNotExist:
                raise NotFound(
                    message="Business not found",
                    resource="BusinessAccount",
                    resource_id=slug,
                )
        return self._business

    def get_account_type(self) -> str:
        return AccountType.BUSINESS

    def get_account_id(self) -> UUID:
        return self.get_business().id


class PlatformContextMixin(AccountContextMixin):
    """Mixin for platform context views."""

    _platform = None

    def get_platform(self) -> PlatformAccount:
        """Get the platform singleton."""
        if self._platform is None:
            self._platform = PlatformAccount.objects.first()
            if not self._platform:
                raise NotFound(
                    message="Platform not configured",
                    resource="PlatformAccount",
                )
        return self._platform

    def get_account_type(self) -> str:
        return AccountType.PLATFORM

    def get_account_id(self) -> UUID:
        return self.get_platform().id


# =============================================================================
# PERMISSION VIEWS
# =============================================================================

class PermissionListView(APIView):
    """List all available permissions."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List permissions",
        description="List all available RBAC permissions.",
        tags=["RBAC"],
        responses={200: PermissionOutputSerializer(many=True)},
    )
    def get(self, request):
        """Get all permissions."""
        permissions = PermissionSelector.get_all_permissions()
        serializer = PermissionOutputSerializer(permissions, many=True)
        return Response(serializer.data)


# =============================================================================
# ROLE VIEWS - BUSINESS CONTEXT
# =============================================================================

class BusinessRoleListView(BusinessContextMixin, APIView):
    """List and create roles for a business."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List business roles",
        description="List all roles for a business.",
        tags=["RBAC - Business"],
        responses={200: RoleOutputSerializer(many=True)},
    )
    def get(self, request, business_slug):
        """List all roles for this business."""
        business = self.get_business()

        # Check if user is a member
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a member of this business",
            )

        roles = RoleSelector.get_roles_for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        serializer = RoleOutputSerializer(roles, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create business role",
        description="Create a new custom role for a business.",
        tags=["RBAC - Business"],
        request=RoleCreateInputSerializer,
        responses={201: RoleDetailOutputSerializer},
    )
    def post(self, request, business_slug):
        """Create a new custom role."""
        actor_context = self.get_actor_context()
        input_serializer = RoleCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        role = RBACService.create_custom_role(
            account_type=AccountType.BUSINESS,
            account_id=self.get_account_id(),
            name=input_serializer.validated_data["name"],
            level=input_serializer.validated_data["level"],
            description=input_serializer.validated_data.get("description", ""),
            actor_context=actor_context,
            request=request,
        )

        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BusinessRoleDetailView(BusinessContextMixin, PermissionInjectMixin, APIView):
    """Retrieve, update, delete a business role."""

    permission_classes = [IsAuthenticated]
    policy_class = RolePolicy

    def _build_policy_kwargs(self) -> dict:
        return {
            "actor_context": self._actor_context,
            "role": self._role,
        }

    @extend_schema(
        summary="Get business role",
        description="Get details of a business role including its permissions.",
        tags=["RBAC - Business"],
        responses={200: RoleDetailOutputSerializer},
    )
    def get(self, request, business_slug, role_id):
        """Get role details."""
        business = self.get_business()

        # Check if user is a member
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a member of this business",
            )

        role = RoleSelector.get_role_by_id(role_id=role_id)
        self._role = role
        self._actor_context = RBACService.build_actor_context(
            membership=membership, request=request,
        )
        self._inject_permissions = True
        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data)

    @extend_schema(
        summary="Update business role",
        description="Update a custom business role's name or description.",
        tags=["RBAC - Business"],
        request=RoleUpdateInputSerializer,
        responses={200: RoleDetailOutputSerializer},
    )
    def patch(self, request, business_slug, role_id):
        """Update a custom role."""
        actor_context = self.get_actor_context()
        input_serializer = RoleUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        role = RBACService.update_role(
            role_id=role_id,
            name=input_serializer.validated_data.get("name"),
            description=input_serializer.validated_data.get("description"),
            actor_context=actor_context,
            request=request,
        )

        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data)

    @extend_schema(
        summary="Delete business role",
        description="Delete a custom business role.",
        tags=["RBAC - Business"],
        responses={204: OpenApiResponse(description="Role deleted")},
    )
    def delete(self, request, business_slug, role_id):
        """Delete a custom role."""
        actor_context = self.get_actor_context()

        RBACService.delete_role(
            role_id=role_id,
            actor_context=actor_context,
            request=request,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class BusinessRolePermissionView(BusinessContextMixin, APIView):
    """Add/remove permissions from a business role."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add permission to business role",
        description="Add a permission to a business role.",
        tags=["RBAC - Business"],
        request=RolePermissionAddInputSerializer,
        responses={201: RoleDetailOutputSerializer},
    )
    def post(self, request, business_slug, role_id):
        """Add a permission to the role."""
        actor_context = self.get_actor_context()
        input_serializer = RolePermissionAddInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        role_permission = RBACService.add_permission_to_role(
            role_id=role_id,
            permission_id=input_serializer.validated_data["permission_id"],
            scope=input_serializer.validated_data["scope"],
            actor_context=actor_context,
            request=request,
        )

        role = RoleSelector.get_role_by_id(role_id=role_id)
        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Remove permission from business role",
        description="Remove a permission from a business role.",
        tags=["RBAC - Business"],
        request=RolePermissionRemoveInputSerializer,
        responses={200: RoleDetailOutputSerializer},
    )
    def delete(self, request, business_slug, role_id):
        """Remove a permission from the role."""
        actor_context = self.get_actor_context()
        input_serializer = RolePermissionRemoveInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        RBACService.remove_permission_from_role(
            role_id=role_id,
            permission_id=input_serializer.validated_data["permission_id"],
            actor_context=actor_context,
            request=request,
        )

        role = RoleSelector.get_role_by_id(role_id=role_id)
        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data)


# =============================================================================
# MEMBERSHIP VIEWS - BUSINESS CONTEXT
# =============================================================================

class BusinessMemberListView(BusinessContextMixin, APIView):
    """List members for a business."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List business members",
        description="List all members of a business. Supports search, filter, and pagination.",
        tags=["RBAC - Business"],
        responses={200: MembershipListOutputSerializer(many=True)},
    )
    def get(self, request, business_slug):
        """List all members of this business."""
        business = self.get_business()

        # Check if user is a member (for permission check)
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a member of this business",
            )

        # Extract query params
        params = request.query_params
        include_all = params.get("include_all", "false").lower() == "true"
        status_filter = params.get("status")
        search = params.get("search")
        role_id = params.get("role_id")
        ordering = params.get("ordering")

        members = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            include_all_statuses=include_all,
            status=status_filter,
            search=search,
            role_id=role_id,
            ordering=ordering,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(members, request, view=self)
        if page is not None:
            serializer = MembershipListOutputSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = MembershipListOutputSerializer(members, many=True)
        return Response(serializer.data)


class BusinessMemberDetailView(BusinessContextMixin, PermissionInjectMixin, APIView):
    """Retrieve a business member."""

    permission_classes = [IsAuthenticated]
    policy_class = MembershipPolicy

    def _build_policy_kwargs(self) -> dict:
        return {
            "actor_context": self._actor_context,
            "target_membership": self._target_membership,
        }

    @extend_schema(
        summary="Get business member",
        description="Get details of a business member.",
        tags=["RBAC - Business"],
        responses={200: MembershipOutputSerializer},
    )
    def get(self, request, business_slug, membership_id):
        """Get member details."""
        business = self.get_business()
        actor_membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        if not actor_membership:
            raise PermissionDenied(
                message="You are not a member of this business",
            )

        membership = MembershipSelector.get_membership_by_id(
            membership_id=membership_id
        )
        self._target_membership = membership
        self._actor_context = RBACService.build_actor_context(
            membership=actor_membership, request=request,
        )
        self._inject_permissions = True
        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class BusinessMemberRoleView(BusinessContextMixin, APIView):
    """Change a member's role."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change business member role",
        description="Change a business member's role.",
        tags=["RBAC - Business"],
        request=MembershipRoleChangeInputSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def patch(self, request, business_slug, membership_id):
        """Change member's role."""
        actor_context = self.get_actor_context()
        input_serializer = MembershipRoleChangeInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        membership = RBACService.change_member_role(
            membership_id=membership_id,
            new_role_id=input_serializer.validated_data["role_id"],
            actor_context=actor_context,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class BusinessMemberSuspendView(BusinessContextMixin, APIView):
    """Suspend a member."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Suspend business member",
        description="Suspend a business member with an optional reason.",
        tags=["RBAC - Business"],
        request=MemberActionReasonInputSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, business_slug, membership_id):
        """Suspend a member."""
        serializer = MemberActionReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        reason = serializer.validated_data["reason"]

        membership = RBACService.update_membership_status(
            membership_id=membership_id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
            reason=reason,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class BusinessMemberRemoveView(BusinessContextMixin, APIView):
    """Remove a member."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove business member",
        description="Remove a member from a business with an optional reason.",
        tags=["RBAC - Business"],
        request=MemberActionReasonInputSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, business_slug, membership_id):
        """Remove a member."""
        serializer = MemberActionReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        reason = serializer.validated_data["reason"]

        membership = RBACService.update_membership_status(
            membership_id=membership_id,
            new_status=MembershipStatus.REMOVED,
            actor_context=actor_context,
            reason=reason,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class BusinessMemberBanView(BusinessContextMixin, APIView):
    """Ban a member."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Ban business member",
        description="Ban a member from a business with an optional reason.",
        tags=["RBAC - Business"],
        request=MemberActionReasonInputSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, business_slug, membership_id):
        """Ban a member."""
        serializer = MemberActionReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        reason = serializer.validated_data["reason"]

        membership = RBACService.update_membership_status(
            membership_id=membership_id,
            new_status=MembershipStatus.BANNED,
            actor_context=actor_context,
            reason=reason,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class BusinessMemberReactivateView(BusinessContextMixin, APIView):
    """Reactivate a suspended or removed member."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Reactivate business member",
        description="Reactivate a suspended or removed business member.",
        tags=["RBAC - Business"],
        request=None,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, business_slug, membership_id):
        """Reactivate a member."""
        actor_context = self.get_actor_context()

        membership = RBACService.update_membership_status(
            membership_id=membership_id,
            new_status=MembershipStatus.ACTIVE,
            actor_context=actor_context,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class BusinessMemberLeaveView(BusinessContextMixin, APIView):
    """Leave a business (for the current user)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Leave business",
        description="Leave a business. The current user's membership will be set to removed.",
        tags=["RBAC - Business"],
        request=None,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, business_slug):
        """Leave the business."""
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.BUSINESS,
            account_id=self.get_account_id(),
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a member of this business",
            )

        membership = RBACService.member_leave(
            membership_id=membership.id,
            user=request.user,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


# =============================================================================
# ROLE VIEWS - PLATFORM CONTEXT
# =============================================================================

class PlatformRoleListView(PlatformContextMixin, APIView):
    """List and create roles for the platform."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List platform roles",
        description="List all roles for the platform.",
        tags=["RBAC - Platform"],
        responses={200: RoleOutputSerializer(many=True)},
    )
    def get(self, request):
        """List all platform roles."""
        platform = self.get_platform()

        # Check if user is a platform member
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a platform member",
            )

        roles = RoleSelector.get_roles_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        serializer = RoleOutputSerializer(roles, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create platform role",
        description="Create a new custom role for the platform.",
        tags=["RBAC - Platform"],
        request=RoleCreateInputSerializer,
        responses={201: RoleDetailOutputSerializer},
    )
    def post(self, request):
        """Create a new custom role."""
        actor_context = self.get_actor_context()
        input_serializer = RoleCreateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        role = RBACService.create_custom_role(
            account_type=AccountType.PLATFORM,
            account_id=self.get_account_id(),
            name=input_serializer.validated_data["name"],
            level=input_serializer.validated_data["level"],
            description=input_serializer.validated_data.get("description", ""),
            actor_context=actor_context,
            request=request,
        )

        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PlatformRoleDetailView(PlatformContextMixin, PermissionInjectMixin, APIView):
    """Retrieve, update, delete a platform role."""

    permission_classes = [IsAuthenticated]
    policy_class = RolePolicy

    def _build_policy_kwargs(self) -> dict:
        return {
            "actor_context": self._actor_context,
            "role": self._role,
        }

    @extend_schema(
        summary="Get platform role",
        description="Get details of a platform role including its permissions.",
        tags=["RBAC - Platform"],
        responses={200: RoleDetailOutputSerializer},
    )
    def get(self, request, role_id):
        """Get role details."""
        platform = self.get_platform()
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a platform member",
            )

        role = RoleSelector.get_role_by_id(role_id=role_id)
        self._role = role
        self._actor_context = RBACService.build_actor_context(
            membership=membership, request=request,
        )
        self._inject_permissions = True
        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data)

    @extend_schema(
        summary="Update platform role",
        description="Update a custom platform role's name or description.",
        tags=["RBAC - Platform"],
        request=RoleUpdateInputSerializer,
        responses={200: RoleDetailOutputSerializer},
    )
    def patch(self, request, role_id):
        """Update a custom role."""
        actor_context = self.get_actor_context()
        input_serializer = RoleUpdateInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        role = RBACService.update_role(
            role_id=role_id,
            name=input_serializer.validated_data.get("name"),
            description=input_serializer.validated_data.get("description"),
            actor_context=actor_context,
            request=request,
        )

        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data)

    @extend_schema(
        summary="Delete platform role",
        description="Delete a custom platform role.",
        tags=["RBAC - Platform"],
        responses={204: OpenApiResponse(description="Role deleted")},
    )
    def delete(self, request, role_id):
        """Delete a custom role."""
        actor_context = self.get_actor_context()

        RBACService.delete_role(
            role_id=role_id,
            actor_context=actor_context,
            request=request,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class PlatformRolePermissionView(PlatformContextMixin, APIView):
    """Add/remove permissions from a platform role."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Add permission to platform role",
        description="Add a permission to a platform role.",
        tags=["RBAC - Platform"],
        request=RolePermissionAddInputSerializer,
        responses={201: RoleDetailOutputSerializer},
    )
    def post(self, request, role_id):
        """Add a permission to the role."""
        actor_context = self.get_actor_context()
        input_serializer = RolePermissionAddInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        RBACService.add_permission_to_role(
            role_id=role_id,
            permission_id=input_serializer.validated_data["permission_id"],
            scope=input_serializer.validated_data["scope"],
            actor_context=actor_context,
            request=request,
        )

        role = RoleSelector.get_role_by_id(role_id=role_id)
        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Remove permission from platform role",
        description="Remove a permission from a platform role.",
        tags=["RBAC - Platform"],
        request=RolePermissionRemoveInputSerializer,
        responses={200: RoleDetailOutputSerializer},
    )
    def delete(self, request, role_id):
        """Remove a permission from the role."""
        actor_context = self.get_actor_context()
        input_serializer = RolePermissionRemoveInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        RBACService.remove_permission_from_role(
            role_id=role_id,
            permission_id=input_serializer.validated_data["permission_id"],
            actor_context=actor_context,
            request=request,
        )

        role = RoleSelector.get_role_by_id(role_id=role_id)
        serializer = RoleDetailOutputSerializer(role)
        return Response(serializer.data)


# =============================================================================
# MEMBERSHIP VIEWS - PLATFORM CONTEXT
# =============================================================================

class PlatformMemberListView(PlatformContextMixin, APIView):
    """List platform members."""

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List platform members",
        description="List all members of the platform. Supports search, filter, and pagination.",
        tags=["RBAC - Platform"],
        responses={200: MembershipListOutputSerializer(many=True)},
    )
    def get(self, request):
        """List all platform members."""
        platform = self.get_platform()

        # Check if user is a platform member
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a platform member",
            )

        params = request.query_params
        include_all = params.get("include_all", "false").lower() == "true"
        status_filter = params.get("status")
        search = params.get("search")
        role_id = params.get("role_id")
        ordering = params.get("ordering")

        members = MembershipSelector.get_memberships_for_account(
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            include_all_statuses=include_all,
            status=status_filter,
            search=search,
            role_id=role_id,
            ordering=ordering,
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(members, request, view=self)
        if page is not None:
            serializer = MembershipListOutputSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = MembershipListOutputSerializer(members, many=True)
        return Response(serializer.data)


class PlatformMemberDetailView(PlatformContextMixin, PermissionInjectMixin, APIView):
    """Retrieve a platform member."""

    permission_classes = [IsAuthenticated]
    policy_class = MembershipPolicy

    def _build_policy_kwargs(self) -> dict:
        return {
            "actor_context": self._actor_context,
            "target_membership": self._target_membership,
        }

    @extend_schema(
        summary="Get platform member",
        description="Get details of a platform member.",
        tags=["RBAC - Platform"],
        responses={200: MembershipOutputSerializer},
    )
    def get(self, request, membership_id):
        """Get member details."""
        platform = self.get_platform()
        actor_membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
        )
        if not actor_membership:
            raise PermissionDenied(
                message="You are not a platform member",
            )

        membership = MembershipSelector.get_membership_by_id(
            membership_id=membership_id
        )
        self._target_membership = membership
        self._actor_context = RBACService.build_actor_context(
            membership=actor_membership, request=request,
        )
        self._inject_permissions = True
        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class PlatformMemberRoleView(PlatformContextMixin, APIView):
    """Change a platform member's role."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change platform member role",
        description="Change a platform member's role.",
        tags=["RBAC - Platform"],
        request=MembershipRoleChangeInputSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def patch(self, request, membership_id):
        """Change member's role."""
        actor_context = self.get_actor_context()
        input_serializer = MembershipRoleChangeInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        membership = RBACService.change_member_role(
            membership_id=membership_id,
            new_role_id=input_serializer.validated_data["role_id"],
            actor_context=actor_context,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class PlatformMemberSuspendView(PlatformContextMixin, APIView):
    """Suspend a platform member."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Suspend platform member",
        description="Suspend a platform member with an optional reason.",
        tags=["RBAC - Platform"],
        request=MemberActionReasonInputSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, membership_id):
        """Suspend a member."""
        serializer = MemberActionReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        reason = serializer.validated_data["reason"]

        membership = RBACService.update_membership_status(
            membership_id=membership_id,
            new_status=MembershipStatus.SUSPENDED,
            actor_context=actor_context,
            reason=reason,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class PlatformMemberRemoveView(PlatformContextMixin, APIView):
    """Remove a platform member."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Remove platform member",
        description="Remove a member from the platform with an optional reason.",
        tags=["RBAC - Platform"],
        request=MemberActionReasonInputSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, membership_id):
        """Remove a member."""
        serializer = MemberActionReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        reason = serializer.validated_data["reason"]

        membership = RBACService.update_membership_status(
            membership_id=membership_id,
            new_status=MembershipStatus.REMOVED,
            actor_context=actor_context,
            reason=reason,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class PlatformMemberBanView(PlatformContextMixin, APIView):
    """Ban a platform member."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Ban platform member",
        description="Ban a member from the platform with an optional reason.",
        tags=["RBAC - Platform"],
        request=MemberActionReasonInputSerializer,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, membership_id):
        """Ban a member."""
        serializer = MemberActionReasonInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor_context = self.get_actor_context()
        reason = serializer.validated_data["reason"]

        membership = RBACService.update_membership_status(
            membership_id=membership_id,
            new_status=MembershipStatus.BANNED,
            actor_context=actor_context,
            reason=reason,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class PlatformMemberReactivateView(PlatformContextMixin, APIView):
    """Reactivate a suspended or removed platform member."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Reactivate platform member",
        description="Reactivate a suspended or removed platform member.",
        tags=["RBAC - Platform"],
        request=None,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request, membership_id):
        """Reactivate a member."""
        actor_context = self.get_actor_context()

        membership = RBACService.update_membership_status(
            membership_id=membership_id,
            new_status=MembershipStatus.ACTIVE,
            actor_context=actor_context,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


class PlatformMemberLeaveView(PlatformContextMixin, APIView):
    """Leave the platform (for the current user)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Leave platform",
        description="Leave the platform. The current user's membership will be set to removed.",
        tags=["RBAC - Platform"],
        request=None,
        responses={200: MembershipOutputSerializer},
    )
    def post(self, request):
        """Leave the platform."""
        membership = MembershipSelector.get_active_membership_for_user_account(
            user=request.user,
            account_type=AccountType.PLATFORM,
            account_id=self.get_account_id(),
        )
        if not membership:
            raise PermissionDenied(
                message="You are not a platform member",
            )

        membership = RBACService.member_leave(
            membership_id=membership.id,
            user=request.user,
            request=request,
        )

        serializer = MembershipOutputSerializer(membership)
        return Response(serializer.data)


# =============================================================================
# USER CONTEXT VIEWS
# =============================================================================

class MyMembershipsListView(APIView):
    """List current user's memberships."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List my memberships",
        description="List all active memberships for the authenticated user.",
        tags=["RBAC - User"],
        responses={200: MyMembershipOutputSerializer(many=True)},
    )
    def get(self, request):
        """Get all memberships for the current user."""
        memberships = MembershipSelector.get_memberships_for_user(
            user=request.user,
            include_pending_approval=True,
        )
        serializer = MyMembershipOutputSerializer(memberships, many=True)
        return Response(serializer.data)


class MyMembershipDetailView(APIView):
    """Get details of a specific membership for current user."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Get my membership",
        description="Get details of a specific membership for the authenticated user.",
        tags=["RBAC - User"],
        responses={200: MyMembershipOutputSerializer},
    )
    def get(self, request, membership_id):
        """Get membership details."""
        membership = MembershipSelector.get_membership_by_id(
            membership_id=membership_id
        )

        # Verify ownership
        if membership.user_id != request.user.id:
            raise PermissionDenied(
                message="This is not your membership",
            )

        serializer = MyMembershipOutputSerializer(membership)
        return Response(serializer.data)
