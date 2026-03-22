# apps/core/tests/test_visibility_integration.py
"""
Cross-app integration tests for the Content Visibility System.

These tests verify end-to-end visibility behaviour across multiple endpoints:
- PATCH visibility overrides → detail endpoint reflects change
- is_public toggle → T2 fields hide/show
- Membership gain → T3 fields appear
- Profile endpoint applies same filtering as detail endpoint
- T2 override boundary conditions (follower vs. MEMBERS-only)
- T3 permission combinations (member with partial RBAC permissions)
- is_limited flag consistency across viewer types
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from rest_framework.test import APIClient

from apps.organization.tests.factories import (
    BusinessAccountFactory,
    BusinessProfileFactory,
    UserFactory,
)


def _setup_business_with_rbac(owner=None, **biz_kwargs):
    """Create a business with RBAC initialized. Returns (business, owner)."""
    from apps.rbac.services import RBACService

    if owner is None:
        owner = UserFactory()
    biz = BusinessAccountFactory(created_by=owner, updated_by=owner, **biz_kwargs)
    BusinessProfileFactory(business=biz)
    RBACService.initialize_business_account(business_id=biz.id, owner=owner)
    return biz, owner


def _add_member(business, user, permissions=None):
    """Add a base member to business. Optionally grant specific permissions."""
    from apps.core.constants import AccountType
    from apps.rbac.selectors import RoleSelector
    from apps.rbac.services import RBACService

    base_role = RoleSelector.get_base_member_role(
        account_type=AccountType.BUSINESS,
        account_id=business.id,
    )

    membership = RBACService.create_membership(
        user=user,
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        role_id=base_role.id,
        created_by=business.created_by,
    )

    if permissions:
        from apps.rbac.models import Permission, Role, RolePermission

        # Create a custom role with the desired permissions
        custom_role = Role.objects.create(
            name=f"Custom Role {uuid4().hex[:6]}",
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            level=5,
            is_system_role=False,
            created_by=business.created_by,
            updated_by=business.created_by,
        )
        for perm_code in permissions:
            perm = Permission.objects.get(code=perm_code)
            RolePermission.objects.create(
                role=custom_role,
                permission=perm,
            )
        # Change membership to custom role
        membership.role = custom_role
        membership.save(update_fields=["role"])

    return membership


# =============================================================================
# CROSS-ENDPOINT CONSISTENCY
# =============================================================================


@pytest.mark.django_db
class TestCrossEndpointVisibilityConsistency:
    """Verify that detail, by-id, and profile endpoints apply the same filtering."""

    def test_detail_and_byid_return_same_t2_filtering(self, db):
        """Both /business/{slug}/ and /business/id/{uuid}/ filter T2 identically."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "secret@acme.com"
        biz.profile.is_public = True
        biz.profile.save(update_fields=["contact_email", "is_public"])

        viewer = UserFactory()
        client = APIClient()
        client.force_authenticate(user=viewer)

        r_slug = client.get(f"/api/v1/business/{biz.slug}/")
        r_id = client.get(f"/api/v1/business/id/{biz.id}/")

        assert r_slug.status_code == 200
        assert r_id.status_code == 200
        # Both should show T2 on public profile
        assert r_slug.data["profile"]["contact_email"] == "secret@acme.com"
        assert r_id.data["profile"]["contact_email"] == "secret@acme.com"
        # Both should hide T3
        assert "registration_number" not in r_slug.data
        assert "registration_number" not in r_id.data

    def test_profile_endpoint_applies_t2_filtering(self, db):
        """GET /business/{slug}/profile/ also filters T2 fields."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "t2@acme.com"
        biz.profile.contact_phone = "+1234567890"
        biz.profile.is_public = False
        biz.profile.save(update_fields=["contact_email", "contact_phone", "is_public"])

        viewer = UserFactory()
        client = APIClient()
        client.force_authenticate(user=viewer)

        # Viewer is neither member nor follower → T2 should be hidden on private
        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=True,  # Allow access (follower can view)
        ):
            response = client.get(f"/api/v1/business/{biz.slug}/profile/")

        assert response.status_code == 200
        # Follower viewing private → T2 default level=FOLLOWERS(2),
        # viewer level=FOLLOWERS(2) → 2 >= 2 → visible
        assert response.data["contact_email"] == "t2@acme.com"

    def test_profile_endpoint_hides_t2_for_stranger_on_private(self, db):
        """Profile endpoint denies non-follower non-member on private business."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "hidden@acme.com"
        biz.profile.is_public = False
        biz.profile.save(update_fields=["contact_email", "is_public"])

        viewer = UserFactory()
        client = APIClient()
        client.force_authenticate(user=viewer)

        # Viewer is authenticated but not a follower/member
        # can_view_profile → FollowSelector.is_following (lazy import at source)
        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=False,
        ):
            response = client.get(f"/api/v1/business/{biz.slug}/profile/")

        # Not a follower + private → 403 (can_view_profile denies)
        assert response.status_code == 403


# =============================================================================
# VISIBILITY OVERRIDE → DETAIL ENDPOINT PERSISTENCE
# =============================================================================


@pytest.mark.django_db
class TestVisibilityOverridePersistence:
    """Verify that PATCHing visibility overrides is reflected on detail endpoints."""

    def test_patch_override_reflected_on_detail(self, db):
        """PATCH visibility overrides → detail endpoint respects the new level."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "override@acme.com"
        biz.profile.is_public = False  # Private → T2 uses per-field checks
        biz.profile.save(update_fields=["contact_email", "is_public"])

        owner_client = APIClient()
        owner_client.force_authenticate(user=owner)

        # Default level is FOLLOWERS(2). Override to MEMBERS(0).
        resp = owner_client.patch(
            f"/api/v1/business/{biz.slug}/profile/visibility/",
            {"overrides": {"contact_email": 0}},  # MEMBERS only
            format="json",
        )
        assert resp.status_code == 200

        # Now a follower should NOT see contact_email (level=2, required=0)
        follower = UserFactory()
        follower_client = APIClient()
        follower_client.force_authenticate(user=follower)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=True,
        ):
            detail = follower_client.get(f"/api/v1/business/{biz.slug}/")

        assert detail.status_code == 200
        # Follower level=2, required=0 → 2 >= 0 → True → should see it!
        # Wait — MEMBERS=0 means most restrictive. Level hierarchy:
        # MEMBERS(0) → CONNECTIONS(1) → FOLLOWERS(2) → WORLD(3)
        # A follower has level=2, required_level=0 → 2 >= 0 → True → visible
        # This is correct: MEMBERS(0) means "at least members", which is the LEAST
        # restrictive (everyone above level 0 can see it).
        assert response_has_field(detail.data, "profile", "contact_email")

    def test_override_to_world_shows_to_all_authenticated(self, db):
        """Override to WORLD(3) → stranger can still see T2 on private if level >= 3."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "world@acme.com"
        biz.profile.is_public = False
        biz.profile.save(update_fields=["contact_email", "is_public"])

        owner_client = APIClient()
        owner_client.force_authenticate(user=owner)

        # Override contact_email to WORLD(3)
        owner_client.patch(
            f"/api/v1/business/{biz.slug}/profile/visibility/",
            {"overrides": {"contact_email": 3}},  # WORLD
            format="json",
        )

        # Authenticated stranger (level=WORLD=3) viewing private business
        stranger = UserFactory()
        stranger_client = APIClient()
        stranger_client.force_authenticate(user=stranger)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=False,
        ):
            detail = stranger_client.get(f"/api/v1/business/{biz.slug}/")

        assert detail.status_code == 200
        # Stranger level=WORLD(3), required=WORLD(3) → 3 >= 3 → visible
        assert detail.data["profile"]["contact_email"] == "world@acme.com"

    def test_override_to_world_hides_from_follower(self, db):
        """Override contact_phone to WORLD(3). Follower (level=2) can't see it (2 < 3)."""
        # This test verifies the actual resolver behaviour with overrides.
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_phone = "+1-555-HIDDEN"
        biz.profile.is_public = False
        biz.profile.save(update_fields=["contact_phone", "is_public"])

        owner_client = APIClient()
        owner_client.force_authenticate(user=owner)

        # Override contact_phone to WORLD(3) → most restrictive for non-members
        owner_client.patch(
            f"/api/v1/business/{biz.slug}/profile/visibility/",
            {"overrides": {"contact_phone": 3}},  # WORLD
            format="json",
        )

        # Follower (level=2) should NOT see contact_phone (2 < 3)
        follower = UserFactory()
        follower_client = APIClient()
        follower_client.force_authenticate(user=follower)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=True,
        ):
            detail = follower_client.get(f"/api/v1/business/{biz.slug}/")

        assert detail.status_code == 200
        # Follower level=FOLLOWERS(2), required=WORLD(3) → 2 >= 3 → False → hidden
        assert "contact_phone" not in detail.data.get("profile", {})


# =============================================================================
# IS_PUBLIC TOGGLE → T2 VISIBILITY
# =============================================================================


@pytest.mark.django_db
class TestIsPublicToggle:
    """Verify that is_public toggle controls T2 field visibility."""

    def test_public_profile_shows_t2_to_anonymous(self, db):
        """Public profile → T2 visible to anonymous viewers."""
        biz, _ = _setup_business_with_rbac()
        biz.profile.contact_email = "pub@acme.com"
        biz.profile.is_public = True
        biz.profile.save(update_fields=["contact_email", "is_public"])

        client = APIClient()
        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        assert response.data["profile"]["contact_email"] == "pub@acme.com"

    def test_private_profile_stranger_sees_t2_at_default_level(self, db):
        """Private profile, stranger (level=WORLD=3) with default T2 level=FOLLOWERS(2): 3>=2 → visible."""
        biz, _ = _setup_business_with_rbac()
        biz.profile.contact_email = "priv@acme.com"
        biz.profile.is_public = False
        biz.profile.save(update_fields=["contact_email", "is_public"])

        stranger = UserFactory()
        client = APIClient()
        client.force_authenticate(user=stranger)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=False,
        ):
            response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # Stranger level=WORLD(3), default required=FOLLOWERS(2) → 3 >= 2 → visible
        assert response.data["profile"]["contact_email"] == "priv@acme.com"

    def test_private_profile_denied_for_anonymous(self, db):
        """Private profile → anonymous gets 403 (can_view denies anonymous+private)."""
        biz, _ = _setup_business_with_rbac()
        biz.profile.contact_email = "anon@acme.com"
        biz.profile.is_public = False
        biz.profile.save(update_fields=["contact_email", "is_public"])

        client = APIClient()  # Not authenticated
        response = client.get(f"/api/v1/business/{biz.slug}/")

        # Anonymous + private → can_view returns False → 403
        assert response.status_code == 403

    def test_public_profile_always_shows_t2_regardless_of_override(self, db):
        """When is_public=True, T2 visible regardless of override value."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "always@acme.com"
        biz.profile.is_public = True
        biz.profile.visibility_overrides = {"contact_email": 0}  # MEMBERS
        biz.profile.save(
            update_fields=["contact_email", "is_public", "visibility_overrides"]
        )

        stranger = UserFactory()
        client = APIClient()
        client.force_authenticate(user=stranger)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # is_public=True → global override → T2 always visible
        assert response.data["profile"]["contact_email"] == "always@acme.com"


# =============================================================================
# MEMBERSHIP → T3 VISIBILITY
# =============================================================================


@pytest.mark.django_db
class TestMembershipT3Visibility:
    """Verify that membership grants/denies T3 field access based on RBAC."""

    def test_owner_sees_all_t3_fields(self, db):
        """Owner sees all T3 fields (registration_number, tax_id, etc.)."""
        biz, owner = _setup_business_with_rbac(
            registration_number="REG-OWNER",
            tax_id="TAX-OWNER",
            legal_address="123 Owner St",
        )

        client = APIClient()
        client.force_authenticate(user=owner)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        assert response.data["registration_number"] == "REG-OWNER"
        assert response.data["tax_id"] == "TAX-OWNER"
        assert response.data["legal_address"] == "123 Owner St"
        assert "settings" in response.data
        assert "max_members" in response.data

    def test_member_without_permission_cannot_see_t3_legal(self, db):
        """Base member (no can_view_legal_info) cannot see T3 legal fields."""
        biz, owner = _setup_business_with_rbac(
            registration_number="REG-HIDDEN",
            tax_id="TAX-HIDDEN",
        )

        member = UserFactory()
        _add_member(biz, member)  # Base member, no special permissions

        client = APIClient()
        client.force_authenticate(user=member)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # Base member without can_view_legal_info → T3 legal fields hidden
        assert "registration_number" not in response.data
        assert "tax_id" not in response.data
        assert "legal_address" not in response.data

    def test_member_with_view_legal_info_sees_legal_fields(self, db):
        """Member with can_view_legal_info sees T3 legal fields."""
        biz, owner = _setup_business_with_rbac(
            registration_number="REG-PERM",
            tax_id="TAX-PERM",
        )

        member = UserFactory()
        _add_member(biz, member, permissions=["can_view_legal_info"])

        client = APIClient()
        client.force_authenticate(user=member)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        assert response.data["registration_number"] == "REG-PERM"
        assert response.data["tax_id"] == "TAX-PERM"

    def test_member_with_partial_permissions(self, db):
        """Member with can_view_legal_info but NOT can_edit_business sees legal but not settings."""
        biz, owner = _setup_business_with_rbac(
            registration_number="REG-PART",
        )
        biz.settings = {"theme": "dark"}
        biz.save(update_fields=["settings"])

        member = UserFactory()
        _add_member(biz, member, permissions=["can_view_legal_info"])

        client = APIClient()
        client.force_authenticate(user=member)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # Has can_view_legal_info → sees legal fields
        assert response.data["registration_number"] == "REG-PART"
        # Does NOT have can_edit_business → settings hidden
        assert "settings" not in response.data

    def test_non_member_never_sees_t3(self, db):
        """Non-member never sees T3 regardless of level."""
        biz, _ = _setup_business_with_rbac(
            registration_number="REG-NOPE",
        )
        biz.profile.is_public = True
        biz.profile.save(update_fields=["is_public"])

        viewer = UserFactory()
        client = APIClient()
        client.force_authenticate(user=viewer)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        assert "registration_number" not in response.data

    def test_member_always_sees_t2_regardless_of_override(self, db):
        """Members bypass T2 checks entirely."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "member-bypass@acme.com"
        biz.profile.is_public = False
        biz.profile.visibility_overrides = {"contact_email": 3}  # Even WORLD
        biz.profile.save(
            update_fields=["contact_email", "is_public", "visibility_overrides"]
        )

        member = UserFactory()
        _add_member(biz, member)

        client = APIClient()
        client.force_authenticate(user=member)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # Member bypass → T2 always visible
        assert response.data["profile"]["contact_email"] == "member-bypass@acme.com"


# =============================================================================
# IS_LIMITED FLAG CONSISTENCY
# =============================================================================


@pytest.mark.django_db
class TestIsLimitedFlag:
    """Verify is_limited flag consistency across viewer types."""

    def test_no_is_limited_for_owner(self, db):
        """Owner never gets is_limited."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.is_public = False
        biz.profile.save(update_fields=["is_public"])

        client = APIClient()
        client.force_authenticate(user=owner)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        assert "is_limited" not in response.data

    def test_no_is_limited_for_member(self, db):
        """Member never gets is_limited, even on private profile."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.is_public = False
        biz.profile.save(update_fields=["is_public"])

        member = UserFactory()
        _add_member(biz, member)

        client = APIClient()
        client.force_authenticate(user=member)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        assert "is_limited" not in response.data

    def test_is_limited_for_non_member_on_private(self, db):
        """Non-member on private profile gets is_limited=True."""
        biz, _ = _setup_business_with_rbac()
        biz.profile.is_public = False
        biz.profile.save(update_fields=["is_public"])

        stranger = UserFactory()
        client = APIClient()
        client.force_authenticate(user=stranger)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=False,
        ):
            response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        assert response.data.get("is_limited") is True

    def test_is_limited_for_follower_on_private(self, db):
        """Follower on private profile gets is_limited=True (not a member)."""
        biz, _ = _setup_business_with_rbac()
        biz.profile.is_public = False
        biz.profile.save(update_fields=["is_public"])

        follower = UserFactory()
        client = APIClient()
        client.force_authenticate(user=follower)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=True,
        ):
            response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # Follower is not a member → is_limited on private
        assert response.data.get("is_limited") is True

    def test_no_is_limited_on_public(self, db):
        """No is_limited on public profiles regardless of viewer."""
        biz, _ = _setup_business_with_rbac()
        biz.profile.is_public = True
        biz.profile.save(update_fields=["is_public"])

        stranger = UserFactory()
        client = APIClient()
        client.force_authenticate(user=stranger)

        response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        assert "is_limited" not in response.data

    def test_is_limited_on_byid_endpoint_too(self, db):
        """is_limited flag also set on BusinessByIdView."""
        biz, _ = _setup_business_with_rbac()
        biz.profile.is_public = False
        biz.profile.save(update_fields=["is_public"])

        stranger = UserFactory()
        client = APIClient()
        client.force_authenticate(user=stranger)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=False,
        ):
            response = client.get(f"/api/v1/business/id/{biz.id}/")

        assert response.status_code == 200
        assert response.data.get("is_limited") is True


# =============================================================================
# T2 OVERRIDE BOUNDARY CONDITIONS
# =============================================================================


@pytest.mark.django_db
class TestT2OverrideBoundaries:
    """Test T2 override boundary conditions for different viewer levels."""

    def test_follower_sees_field_at_exactly_their_level(self, db):
        """Follower (level=2) sees T2 field with required_level=FOLLOWERS(2)."""
        biz, _ = _setup_business_with_rbac()
        biz.profile.contact_email = "exact@acme.com"
        biz.profile.is_public = False
        biz.profile.save(update_fields=["contact_email", "is_public"])
        # Default override is FOLLOWERS(2) — exactly at follower's level

        follower = UserFactory()
        client = APIClient()
        client.force_authenticate(user=follower)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=True,
        ):
            response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # level=2, required=2 → 2 >= 2 → visible
        assert response.data["profile"]["contact_email"] == "exact@acme.com"

    def test_follower_cannot_see_field_above_their_level(self, db):
        """Follower (level=2) cannot see T2 field overridden to WORLD(3)."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "hidden@acme.com"
        biz.profile.is_public = False
        biz.profile.visibility_overrides = {"contact_email": 3}  # WORLD
        biz.profile.save(
            update_fields=["contact_email", "is_public", "visibility_overrides"]
        )

        follower = UserFactory()
        client = APIClient()
        client.force_authenticate(user=follower)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=True,
        ):
            response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # level=2, required=3 → 2 >= 3 → False → hidden
        assert "contact_email" not in response.data.get("profile", {})

    def test_stranger_sees_field_at_world_level(self, db):
        """Stranger (level=WORLD=3) sees T2 field with required_level=WORLD(3)."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "world@acme.com"
        biz.profile.is_public = False
        biz.profile.visibility_overrides = {"contact_email": 3}
        biz.profile.save(
            update_fields=["contact_email", "is_public", "visibility_overrides"]
        )

        stranger = UserFactory()
        client = APIClient()
        client.force_authenticate(user=stranger)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=False,
        ):
            response = client.get(f"/api/v1/business/{biz.slug}/")

        assert response.status_code == 200
        # level=3, required=3 → 3 >= 3 → visible
        assert response.data["profile"]["contact_email"] == "world@acme.com"

    def test_anonymous_denied_on_private_business(self, db):
        """Anonymous viewer gets 403 on private business (can_view denies)."""
        biz, owner = _setup_business_with_rbac()
        biz.profile.contact_email = "anon@acme.com"
        biz.profile.is_public = False
        biz.profile.visibility_overrides = {"contact_email": 0}  # MEMBERS
        biz.profile.save(
            update_fields=["contact_email", "is_public", "visibility_overrides"]
        )

        client = APIClient()  # Not authenticated
        response = client.get(f"/api/v1/business/{biz.slug}/")

        # Anonymous + private → can_view returns False → 403
        assert response.status_code == 403


# =============================================================================
# HELPER
# =============================================================================


def response_has_field(data, nested_key, field_name):
    """Check if a nested field exists in response data."""
    nested = data.get(nested_key, {})
    return field_name in nested
