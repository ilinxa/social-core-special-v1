# apps/organization/business/views.py
"""
Business Views - API endpoints for business operations.

Endpoints:
    /api/v1/business/                       GET, POST
    /api/v1/business/my/                    GET
    /api/v1/business/id/{uuid}/             GET
    /api/v1/business/{slug}/                GET, PATCH, DELETE
    /api/v1/business/{slug}/profile/        GET, PATCH
    /api/v1/business/{slug}/slug/           PATCH
    /api/v1/business/{slug}/suspend/        POST
    /api/v1/business/{slug}/reactivate/     POST
    /api/v1/business/{slug}/archive/        POST
    /api/v1/business/{slug}/profile/visibility/  GET, PATCH
"""

from uuid import UUID

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import PermissionDenied
from apps.core.permissions import AllowAny, IsAuthenticated
from apps.core.pagination import StandardPagination
from apps.core.views import PermissionInjectMixin, RelationshipInjectMixin
from apps.core.visibility.resolver import VisibilityResolver
from apps.core.visibility.serializers import VisibilityOverrideInput
from apps.organization.business.policies import BusinessPolicy
from apps.organization.business.selectors import (
    BusinessAccountSelector,
    BusinessProfileSelector,
)
from apps.organization.business.serializers import (
    BusinessAccountListOutput,
    BusinessAccountOutput,
    BusinessCreateInput,
    BusinessProfileOutput,
    BusinessProfileUpdateInput,
    BusinessSlugUpdateInput,
    BusinessSuspendInput,
    BusinessUpdateInput,
)
from apps.organization.business.services import (
    BusinessAccountService,
    BusinessProfileService,
)


def _build_business_relationship(user, business) -> dict:
    """Compute _relationship data for an authenticated user + business."""
    from apps.core.constants import AccountType
    from apps.rbac.selectors import MembershipSelector
    from apps.transaction.selectors import TransactionSelector
    from apps.network.selectors import FollowSelector

    membership = MembershipSelector.get_membership_for_user_account(
        user=user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
    )

    active_txn = TransactionSelector.has_active_in_conflict_group(
        conflict_group="business_membership",
        user_id=user.id,
        context_type="business",
        context_id=business.id,
    )

    follow = FollowSelector.get_follow_for_user(
        follower_id=user.id,
        followee_type="business",
        followee_id=business.id,
    )

    active_follow_txn = TransactionSelector.has_active_in_conflict_group(
        conflict_group="business_follow",
        user_id=user.id,
        context_type="business",
        context_id=business.id,
    )

    return {
        "membership_status": membership.status if membership else None,
        "active_transaction": {
            "id": str(active_txn.id),
            "type": active_txn.transaction_type,
            "status": active_txn.status,
            "mode": active_txn.mode,
            "viewer_role": "initiator" if active_txn.initiator_id == user.id else "target",
        } if active_txn else None,
        "follow_status": follow.status if follow else None,
        "follow_id": str(follow.id) if follow else None,
        "active_follow_transaction": {
            "id": str(active_follow_txn.id),
            "type": active_follow_txn.transaction_type,
            "status": active_follow_txn.status,
            "mode": active_follow_txn.mode,
            "viewer_role": "initiator" if active_follow_txn.initiator_id == user.id else "target",
        } if active_follow_txn else None,
    }


class BusinessListCreateView(APIView):
    """
    API endpoint for listing and creating businesses.

    GET /api/v1/business/
        List active businesses.

    POST /api/v1/business/
        Create a new business (authenticated user becomes owner).
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List businesses",
        description="""
        List all active businesses.

        **Pagination:**
        - Default: 20 items per page
        - Query params: `page`, `page_size` (max 100)
        """,
        tags=["Business"],
        responses={
            200: OpenApiResponse(
                response=BusinessAccountListOutput(many=True),
                description="List of businesses",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """List active businesses."""
        businesses = BusinessAccountSelector.list_active()

        # Apply pagination
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(businesses, request)

        if page is not None:
            serializer = BusinessAccountListOutput(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = BusinessAccountListOutput(businesses, many=True, context={'request': request})
        return Response(serializer.data)

    @extend_schema(
        summary="Create business",
        description="""
        Create a new business account.

        The authenticated user becomes the initial owner.

        **Required fields:**
        - `legal_name`: Legal business name
        - `country`: ISO 3166-1 alpha-2 country code

        **Optional fields:**
        - `slug`: URL slug (auto-generated from legal_name if not provided)
        - `business_type`: Type of business
        - `registration_number`, `tax_id`, `legal_address`
        - `display_name`: Display name for profile
        """,
        tags=["Business"],
        request=BusinessCreateInput,
        responses={
            201: OpenApiResponse(
                response=BusinessAccountOutput,
                description="Business created",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Business creation requires platform approval"),
            409: OpenApiResponse(description="Slug already in use"),
        },
    )
    def post(self, request):
        """Create a new business."""
        if not BusinessPolicy.can_create(user=request.user):
            raise PermissionDenied(
                message="Business creation requires platform approval. "
                        "Submit a business creation permission request first.",
                action="create",
                resource="BusinessAccount",
            )

        serializer = BusinessCreateInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = BusinessAccountService.create_business(
            owner=request.user,
            request=request,
            **serializer.validated_data,
        )

        output = BusinessAccountOutput(business, context={'request': request})
        return Response(output.data, status=status.HTTP_201_CREATED)


class MyBusinessListView(APIView):
    """
    API endpoint for listing user's businesses.

    GET /api/v1/business/my/
        List businesses owned by or where the user is a member.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination

    @extend_schema(
        summary="List my businesses",
        description="""
        List businesses where the authenticated user is an active member
        (including businesses they own).
        """,
        tags=["Business"],
        responses={
            200: OpenApiResponse(
                response=BusinessAccountListOutput(many=True),
                description="List of user's businesses",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        """List user's businesses."""
        businesses = BusinessAccountSelector.list_by_member(user=request.user)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(businesses, request)

        if page is not None:
            serializer = BusinessAccountListOutput(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = BusinessAccountListOutput(businesses, many=True, context={'request': request})
        return Response(serializer.data)


class BusinessByIdView(RelationshipInjectMixin, PermissionInjectMixin, APIView):
    """
    API endpoint for getting business by UUID.

    GET /api/v1/business/id/{uuid}/
        Get business by UUID.
    """

    permission_classes = [IsAuthenticated]
    policy_class = BusinessPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "business": self._resource}

    def _build_relationship_data(self):
        return _build_business_relationship(self.request.user, self._resource)

    @extend_schema(
        summary="Get business by ID",
        description="Retrieve a business by its UUID.",
        tags=["Business"],
        parameters=[
            OpenApiParameter(
                name="business_id",
                type=UUID,
                location=OpenApiParameter.PATH,
                description="Business UUID",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=BusinessAccountOutput,
                description="Business details",
            ),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def get(self, request, business_id: UUID):
        """Get business by UUID."""
        business = BusinessAccountSelector.get_by_id(business_id=business_id)

        if not BusinessPolicy.can_view(user=request.user, business=business):
            raise PermissionDenied(
                message="You don't have permission to view this business",
                action="view",
                resource="BusinessAccount",
            )

        self._resource = business
        self._inject_permissions = True
        self._inject_relationship = True

        viewer_access = VisibilityResolver.compute_viewer_access(
            viewer=request.user, account_type="business", account_id=business.id,
        )
        profile = getattr(business, "profile", None)
        serializer = BusinessAccountOutput(business, context={
            'request': request,
            'visibility': {
                'viewer_access': viewer_access,
                'visibility_overrides': profile.visibility_overrides if profile else None,
                'is_public': profile.is_public if profile else True,
            },
        })
        response_data = serializer.data
        if not viewer_access.is_member and profile and not profile.is_public:
            response_data['is_limited'] = True
        return Response(response_data)


class BusinessDetailView(RelationshipInjectMixin, PermissionInjectMixin, APIView):
    """
    API endpoint for business operations by slug.

    GET /api/v1/business/{slug}/
        Get business by slug (public for active businesses with public profiles).

    PATCH /api/v1/business/{slug}/
        Update business (authenticated + permission).

    DELETE /api/v1/business/{slug}/
        Soft delete business (authenticated + permission).
    """

    permission_classes = [AllowAny]
    policy_class = BusinessPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "business": self._resource}

    def _build_relationship_data(self):
        return _build_business_relationship(self.request.user, self._resource)

    @extend_schema(
        summary="Get business by slug",
        description="""
        Retrieve a business by its URL slug.

        If the slug has changed, returns a redirect header with the new slug.
        """,
        tags=["Business"],
        parameters=[
            OpenApiParameter(
                name="slug",
                type=str,
                location=OpenApiParameter.PATH,
                description="Business slug",
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=BusinessAccountOutput,
                description="Business details",
            ),
            301: OpenApiResponse(description="Redirect to new slug"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def get(self, request, slug: str):
        """Get business by slug."""
        business, redirect_slug = BusinessAccountSelector.get_by_slug_or_redirect(
            slug=slug
        )

        if not BusinessPolicy.can_view(user=request.user, business=business):
            raise PermissionDenied(
                message="You don't have permission to view this business",
                action="view",
                resource="BusinessAccount",
            )

        if redirect_slug:
            response = Response(
                {"redirect_to": redirect_slug},
                status=status.HTTP_301_MOVED_PERMANENTLY,
            )
            response["Location"] = f"/api/v1/business/{redirect_slug}/"
            return response

        self._resource = business
        self._inject_permissions = True
        self._inject_relationship = True

        viewer_access = VisibilityResolver.compute_viewer_access(
            viewer=request.user, account_type="business", account_id=business.id,
        )
        profile = getattr(business, "profile", None)
        serializer = BusinessAccountOutput(business, context={
            'request': request,
            'visibility': {
                'viewer_access': viewer_access,
                'visibility_overrides': profile.visibility_overrides if profile else None,
                'is_public': profile.is_public if profile else True,
            },
        })
        response_data = serializer.data
        if not viewer_access.is_member and profile and not profile.is_public:
            response_data['is_limited'] = True
        return Response(response_data)

    @extend_schema(
        summary="Update business",
        description="""
        Update business account information.

        **Updatable fields:**
        - `legal_name`, `registration_number`, `tax_id`
        - `country`, `legal_address`
        - `business_type`, `settings`

        To change slug, use PATCH /api/v1/business/{slug}/slug/
        """,
        tags=["Business"],
        request=BusinessUpdateInput,
        responses={
            200: OpenApiResponse(
                response=BusinessAccountOutput,
                description="Updated business",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def patch(self, request, slug: str):
        """Update business."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)

        if not BusinessPolicy.can_update(user=request.user, business=business):
            raise PermissionDenied(
                message="You don't have permission to update this business",
                action="update",
                resource="BusinessAccount",
            )

        serializer = BusinessUpdateInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = BusinessAccountService.update(
            business=business,
            actor=request.user,
            request=request,
            **serializer.validated_data,
        )

        output = BusinessAccountOutput(business, context={'request': request})
        return Response(output.data)

    @extend_schema(
        summary="Delete business",
        description="""
        Soft delete a business.

        Only owner or superuser can delete. The business data is preserved
        but marked as deleted.
        """,
        tags=["Business"],
        responses={
            204: OpenApiResponse(description="Business deleted"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def delete(self, request, slug: str):
        """Soft delete business."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)

        if not BusinessPolicy.can_delete(user=request.user, business=business):
            raise PermissionDenied(
                message="You don't have permission to delete this business",
                action="delete",
                resource="BusinessAccount",
            )

        BusinessAccountService.soft_delete(
            business=business,
            actor=request.user,
            request=request,
        )

        return Response(status=status.HTTP_204_NO_CONTENT)


class BusinessSlugUpdateView(APIView):
    """
    API endpoint for changing business slug.

    PATCH /api/v1/business/{slug}/slug/
        Change business slug.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change business slug",
        description="""
        Change the business URL slug.

        The old slug is saved for redirects and can never be reused.
        Only owner can change slug.
        """,
        tags=["Business"],
        request=BusinessSlugUpdateInput,
        responses={
            200: OpenApiResponse(
                response=BusinessAccountOutput,
                description="Updated business with new slug",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
            409: OpenApiResponse(description="Slug already in use"),
        },
    )
    def patch(self, request, slug: str):
        """Change business slug."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)

        if not BusinessPolicy.can_update_slug(user=request.user, business=business):
            raise PermissionDenied(
                message="Only owners can change the business slug",
                action="update_slug",
                resource="BusinessAccount",
            )

        serializer = BusinessSlugUpdateInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = BusinessAccountService.update_slug(
            business=business,
            new_slug=serializer.validated_data["slug"],
            actor=request.user,
            request=request,
        )

        output = BusinessAccountOutput(business, context={'request': request})
        return Response(output.data)


class BusinessProfileView(PermissionInjectMixin, APIView):
    """
    API endpoint for business profile operations.

    GET /api/v1/business/{slug}/profile/
        Get business profile.

    PATCH /api/v1/business/{slug}/profile/
        Update business profile.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    policy_class = BusinessPolicy

    def _build_policy_kwargs(self):
        return {"user": self.request.user, "business": self._resource}

    @extend_schema(
        summary="Get business profile",
        description="Get the business's public profile.",
        tags=["Business"],
        responses={
            200: OpenApiResponse(
                response=BusinessProfileOutput,
                description="Business profile",
            ),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def get(self, request, slug: str):
        """Get business profile."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)
        profile = business.profile

        if not BusinessPolicy.can_view_profile(
            user=request.user, business=business, profile=profile
        ):
            raise PermissionDenied(
                message="You don't have permission to view this profile",
                action="view",
                resource="BusinessProfile",
            )

        self._resource = business
        self._inject_permissions = True

        viewer_access = VisibilityResolver.compute_viewer_access(
            viewer=request.user, account_type="business", account_id=business.id,
        )
        serializer = BusinessProfileOutput(profile, context={
            'request': request,
            'visibility': {
                'viewer_access': viewer_access,
                'visibility_overrides': profile.visibility_overrides,
                'is_public': profile.is_public,
            },
        })
        return Response(serializer.data)

    @extend_schema(
        summary="Update business profile",
        description="""
        Update the business's public profile.

        **Updatable fields:**
        - `display_name`, `tagline`, `description`
        - `logo`, `cover_image` (images)
        - `website`, `contact_email`, `contact_phone`
        - `industry`, `company_size`, `founded_year`
        - `social_links`, `is_public`
        """,
        tags=["Business"],
        request=BusinessProfileUpdateInput,
        responses={
            200: OpenApiResponse(
                response=BusinessProfileOutput,
                description="Updated profile",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def patch(self, request, slug: str):
        """Update business profile."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)

        if not BusinessPolicy.can_update_profile(user=request.user, business=business):
            raise PermissionDenied(
                message="You don't have permission to update this profile",
                action="update",
                resource="BusinessProfile",
            )

        serializer = BusinessProfileUpdateInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile = BusinessProfileService.update(
            profile=business.profile,
            actor=request.user,
            request=request,
            **serializer.validated_data,
        )

        output = BusinessProfileOutput(profile, context={'request': request})
        return Response(output.data)


class BusinessSuspendView(APIView):
    """
    API endpoint for suspending a business.

    POST /api/v1/business/{slug}/suspend/
        Suspend business (staff only).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Suspend business",
        description="""
        Suspend a business account.

        **Staff/superuser only.**

        Suspended businesses cannot be accessed by members.
        """,
        tags=["Business Admin"],
        request=BusinessSuspendInput,
        responses={
            200: OpenApiResponse(
                response=BusinessAccountOutput,
                description="Suspended business",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized (staff required)"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def post(self, request, slug: str):
        """Suspend business."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)

        if not BusinessPolicy.can_suspend(user=request.user, business=business):
            raise PermissionDenied(
                message="Only staff can suspend businesses",
                action="suspend",
                resource="BusinessAccount",
            )

        serializer = BusinessSuspendInput(data=request.data)
        serializer.is_valid(raise_exception=True)

        business = BusinessAccountService.suspend(
            business=business,
            reason=serializer.validated_data["reason"],
            actor=request.user,
            request=request,
        )

        output = BusinessAccountOutput(business, context={'request': request})
        return Response(output.data)


class BusinessReactivateView(APIView):
    """
    API endpoint for reactivating a business.

    POST /api/v1/business/{slug}/reactivate/
        Reactivate suspended business (staff only).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Reactivate business",
        description="""
        Reactivate a suspended business.

        **Staff/superuser only.**
        """,
        tags=["Business Admin"],
        responses={
            200: OpenApiResponse(
                response=BusinessAccountOutput,
                description="Reactivated business",
            ),
            400: OpenApiResponse(description="Business is not suspended"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized (staff required)"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def post(self, request, slug: str):
        """Reactivate business."""
        business = BusinessAccountSelector.get_by_slug(slug=slug, include_deleted=True)

        if not BusinessPolicy.can_reactivate(user=request.user, business=business):
            raise PermissionDenied(
                message="Only staff can reactivate businesses",
                action="reactivate",
                resource="BusinessAccount",
            )

        business = BusinessAccountService.reactivate(
            business=business,
            actor=request.user,
            request=request,
        )

        output = BusinessAccountOutput(business, context={'request': request})
        return Response(output.data)


class BusinessArchiveView(APIView):
    """
    API endpoint for archiving a business.

    POST /api/v1/business/{slug}/archive/
        Archive business (owner only).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Archive business",
        description="""
        Archive a business account.

        **Owner only.**

        Archived businesses are preserved but inactive.
        """,
        tags=["Business"],
        responses={
            200: OpenApiResponse(
                response=BusinessAccountOutput,
                description="Archived business",
            ),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized (owner required)"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def post(self, request, slug: str):
        """Archive business."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)

        if not BusinessPolicy.can_archive(user=request.user, business=business):
            raise PermissionDenied(
                message="Only owners can archive businesses",
                action="archive",
                resource="BusinessAccount",
            )

        business = BusinessAccountService.archive(
            business=business,
            actor=request.user,
            request=request,
        )

        output = BusinessAccountOutput(business, context={'request': request})
        return Response(output.data)


class BusinessProfileVisibilityView(APIView):
    """
    API endpoint for business profile visibility settings.

    GET /api/v1/business/{slug}/profile/visibility/
        Get T2 field visibility settings with current levels and choices.

    PATCH /api/v1/business/{slug}/profile/visibility/
        Update visibility overrides for T2 fields.
    """

    permission_classes = [IsAuthenticated]

    REGISTRY_KEY = "business_profile"

    @extend_schema(
        summary="Get visibility settings",
        description="""
        Get the configurable visibility settings for a business profile.

        Returns a list of T2 (conditional) fields with:
        - `field_name`: The field identifier
        - `current_level`: Currently effective visibility level
        - `default_level`: System default visibility level
        - `choices`: Available visibility levels for this account type

        Only the business owner or members with `can_edit_profile` permission
        can view visibility settings.
        """,
        tags=["Business Profile"],
        responses={
            200: OpenApiResponse(description="Visibility settings"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def get(self, request, slug: str):
        """Get visibility settings for business profile."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)

        if not BusinessPolicy.can_update_profile(user=request.user, business=business):
            raise PermissionDenied(
                message="You don't have permission to view visibility settings",
                action="view_visibility",
                resource="BusinessProfile",
            )

        profile = business.profile
        settings = VisibilityResolver.get_visibility_settings(
            registry_key=self.REGISTRY_KEY,
            visibility_overrides=profile.visibility_overrides,
        )
        return Response(settings)

    @extend_schema(
        summary="Update visibility settings",
        description="""
        Update the visibility overrides for T2 fields on a business profile.

        **Request body:**
        ```json
        {"overrides": {"contact_email": 3, "contact_phone": 0}}
        ```

        Only T2 field names are accepted. Values must be valid visibility
        levels for the business account type (0=Members, 1=Connected,
        2=Followers, 3=World).
        """,
        tags=["Business Profile"],
        request=VisibilityOverrideInput,
        responses={
            200: OpenApiResponse(description="Updated visibility settings"),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Not authenticated"),
            403: OpenApiResponse(description="Not authorized"),
            404: OpenApiResponse(description="Business not found"),
        },
    )
    def patch(self, request, slug: str):
        """Update visibility overrides for business profile."""
        business = BusinessAccountSelector.get_by_slug(slug=slug)

        if not BusinessPolicy.can_update_profile(user=request.user, business=business):
            raise PermissionDenied(
                message="You don't have permission to update visibility settings",
                action="update_visibility",
                resource="BusinessProfile",
            )

        serializer = VisibilityOverrideInput(
            data=request.data,
            context={"registry_key": self.REGISTRY_KEY},
        )
        serializer.is_valid(raise_exception=True)

        profile = business.profile
        # Merge overrides (partial update)
        current_overrides = profile.visibility_overrides or {}
        current_overrides.update(serializer.validated_data["overrides"])
        profile.visibility_overrides = current_overrides
        profile.save(update_fields=["visibility_overrides", "updated_at"])

        # Return updated settings
        settings = VisibilityResolver.get_visibility_settings(
            registry_key=self.REGISTRY_KEY,
            visibility_overrides=profile.visibility_overrides,
        )
        return Response(settings)
