# apps/organization/tests/business/test_views.py
"""
Tests for Business views/API endpoints.
"""

import pytest


@pytest.mark.django_db
class TestBusinessListCreateView:
    """Tests for BusinessListCreateView endpoints."""

    def test_list_businesses(self, authenticated_client, business_with_profile):
        """Test listing active businesses."""
        response = authenticated_client.get("/api/v1/business/")

        assert response.status_code == 200
        assert "results" in response.data
        assert len(response.data["results"]) >= 1

    def test_list_businesses_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list businesses."""
        response = api_client.get("/api/v1/business/")

        assert response.status_code == 401

    def test_create_business(self, authenticated_client, user):
        """Test creating a new business (with platform approval)."""
        user.can_create_business = True
        user.save(update_fields=["can_create_business"])

        response = authenticated_client.post(
            "/api/v1/business/",
            {
                "legal_name": "New Business",
                "country": "US",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["legal_name"] == "New Business"
        assert response.data["slug"] == "new-business"
        assert response.data["profile"] is not None

    def test_create_business_with_all_fields(self, authenticated_client, user):
        """Test creating business with all fields."""
        user.can_create_business = True
        user.save(update_fields=["can_create_business"])

        response = authenticated_client.post(
            "/api/v1/business/",
            {
                "legal_name": "Full Business",
                "country": "GB",
                "slug": "full-business",
                "business_type": "llc",
                "registration_number": "REG123",
                "tax_id": "TAX456",
                "legal_address": "123 Street",
                "display_name": "Full Biz",
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["slug"] == "full-business"
        assert response.data["business_type"] == "llc"
        assert response.data["profile"]["display_name"] == "Full Biz"

    def test_create_business_duplicate_slug(
        self, authenticated_client, user, business_account
    ):
        """Test that creating business with duplicate slug fails."""
        user.can_create_business = True
        user.save(update_fields=["can_create_business"])

        response = authenticated_client.post(
            "/api/v1/business/",
            {
                "legal_name": "Another Business",
                "country": "US",
                "slug": business_account.slug,
            },
            format="json",
        )

        assert response.status_code == 409

    def test_create_business_without_permission(self, authenticated_client):
        """User without can_create_business flag gets 403."""
        response = authenticated_client.post(
            "/api/v1/business/",
            {"legal_name": "Test", "country": "US"},
            format="json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestMyBusinessListView:
    """Tests for MyBusinessListView endpoint."""

    def test_list_my_businesses(self, authenticated_client, business_with_profile):
        """Test listing user's businesses."""
        response = authenticated_client.get("/api/v1/business/my/")

        assert response.status_code == 200
        assert "results" in response.data

    def test_my_businesses_only_shows_own(
        self, authenticated_client, business_with_profile, another_business
    ):
        """Test that only user's own businesses are shown."""
        response = authenticated_client.get("/api/v1/business/my/")

        slugs = [b["slug"] for b in response.data["results"]]
        assert business_with_profile.slug in slugs
        assert another_business.slug not in slugs


@pytest.mark.django_db
class TestBusinessDetailView:
    """Tests for BusinessDetailView endpoints."""

    def test_get_business_by_slug(self, authenticated_client, business_with_profile):
        """Test getting business by slug."""
        response = authenticated_client.get(
            f"/api/v1/business/{business_with_profile.slug}/"
        )

        assert response.status_code == 200
        assert response.data["slug"] == business_with_profile.slug

    def test_get_business_by_id(self, authenticated_client, business_with_profile):
        """Test getting business by UUID."""
        response = authenticated_client.get(
            f"/api/v1/business/id/{business_with_profile.id}/"
        )

        assert response.status_code == 200
        assert response.data["id"] == str(business_with_profile.id)

    def test_get_business_not_found(self, authenticated_client):
        """Test getting non-existent business."""
        response = authenticated_client.get("/api/v1/business/non-existent-slug/")

        assert response.status_code == 404

    def test_update_business_as_owner(self, authenticated_client, business_with_profile):
        """Test updating business as owner."""
        response = authenticated_client.patch(
            f"/api/v1/business/{business_with_profile.slug}/",
            {"legal_name": "Updated Name"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["legal_name"] == "Updated Name"

    def test_update_business_as_non_owner_forbidden(
        self, authenticated_client, another_business
    ):
        """Test that non-owners cannot update business."""
        response = authenticated_client.patch(
            f"/api/v1/business/{another_business.slug}/",
            {"legal_name": "Hacked Name"},
            format="json",
        )

        assert response.status_code == 403

    def test_delete_business_as_owner(self, authenticated_client, business_with_profile):
        """Test soft deleting business as owner."""
        response = authenticated_client.delete(
            f"/api/v1/business/{business_with_profile.slug}/"
        )

        assert response.status_code == 204

    def test_delete_business_as_non_owner_forbidden(
        self, authenticated_client, another_business
    ):
        """Test that non-owners cannot delete business."""
        response = authenticated_client.delete(
            f"/api/v1/business/{another_business.slug}/"
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestBusinessDetailViewPermissions:
    """Tests for _permissions injection in business detail GET responses."""

    def test_get_response_includes_permissions(
        self, authenticated_client, business_with_profile,
    ):
        """GET detail response includes _permissions dict."""
        response = authenticated_client.get(
            f"/api/v1/business/{business_with_profile.slug}/"
        )

        assert response.status_code == 200
        assert "_permissions" in response.data
        assert isinstance(response.data["_permissions"], dict)

    def test_owner_gets_full_permissions(
        self, authenticated_client, business_with_profile,
    ):
        """Owner sees all permissions as True."""
        response = authenticated_client.get(
            f"/api/v1/business/{business_with_profile.slug}/"
        )

        perms = response.data["_permissions"]
        assert perms["can_view"] is True
        assert perms["can_edit"] is True
        assert perms["can_edit_profile"] is True
        assert perms["can_delete"] is True
        assert perms["can_change_slug"] is True
        assert perms["can_archive"] is True

    def test_non_owner_gets_limited_permissions(
        self, authenticated_client, another_business,
    ):
        """Non-owner sees limited permissions."""
        response = authenticated_client.get(
            f"/api/v1/business/{another_business.slug}/"
        )

        perms = response.data["_permissions"]
        assert perms["can_view"] is True
        assert perms["can_edit"] is False
        assert perms["can_delete"] is False

    def test_patch_response_excludes_permissions(
        self, authenticated_client, business_with_profile,
    ):
        """PATCH response does NOT include _permissions."""
        response = authenticated_client.patch(
            f"/api/v1/business/{business_with_profile.slug}/",
            {"legal_name": "Patched Name"},
            format="json",
        )

        assert response.status_code == 200
        assert "_permissions" not in response.data

    def test_get_by_id_includes_permissions(
        self, authenticated_client, business_with_profile,
    ):
        """GET by UUID also includes _permissions."""
        response = authenticated_client.get(
            f"/api/v1/business/id/{business_with_profile.id}/"
        )

        assert response.status_code == 200
        assert "_permissions" in response.data

    def test_list_response_excludes_permissions(
        self, authenticated_client, business_with_profile,
    ):
        """GET list does NOT include _permissions (no opt-in on list views)."""
        response = authenticated_client.get("/api/v1/business/")

        assert response.status_code == 200
        assert "_permissions" not in response.data

    def test_profile_get_includes_permissions(
        self, authenticated_client, business_with_profile,
    ):
        """GET profile also includes _permissions."""
        response = authenticated_client.get(
            f"/api/v1/business/{business_with_profile.slug}/profile/"
        )

        assert response.status_code == 200
        assert "_permissions" in response.data

    def test_profile_patch_excludes_permissions(
        self, authenticated_client, business_with_profile,
    ):
        """PATCH profile does NOT include _permissions."""
        response = authenticated_client.patch(
            f"/api/v1/business/{business_with_profile.slug}/profile/",
            {"display_name": "New Name"},
            format="json",
        )

        assert response.status_code == 200
        assert "_permissions" not in response.data


@pytest.mark.django_db
class TestBusinessDetailViewRelationship:
    """Tests for _relationship injection in business detail GET responses."""

    def test_authenticated_get_includes_relationship(
        self, authenticated_client, business_with_profile,
    ):
        """Authenticated GET detail response includes _relationship dict."""
        response = authenticated_client.get(
            f"/api/v1/business/{business_with_profile.slug}/"
        )
        assert response.status_code == 200
        assert "_relationship" in response.data
        rel = response.data["_relationship"]
        assert "membership_status" in rel
        assert "active_transaction" in rel

    def test_anonymous_get_excludes_relationship(self, api_client, db):
        """Anonymous GET does NOT include _relationship."""
        from apps.organization.tests.factories import BusinessAccountWithProfileFactory
        business = BusinessAccountWithProfileFactory()
        response = api_client.get(f"/api/v1/business/{business.slug}/")
        assert response.status_code == 200
        assert "_relationship" not in response.data

    def test_owner_shows_active_membership(
        self, authenticated_client, business_with_profile,
    ):
        """Owner's _relationship shows active membership_status."""
        response = authenticated_client.get(
            f"/api/v1/business/{business_with_profile.slug}/"
        )
        rel = response.data["_relationship"]
        assert rel["membership_status"] == "active"

    def test_non_member_shows_null_membership(
        self, authenticated_client, another_business,
    ):
        """Non-member sees null membership_status and null active_transaction."""
        response = authenticated_client.get(
            f"/api/v1/business/{another_business.slug}/"
        )
        rel = response.data["_relationship"]
        assert rel["membership_status"] is None
        assert rel["active_transaction"] is None

    def test_pending_request_shows_active_transaction(
        self, authenticated_client, user, another_business,
    ):
        """User with a pending request sees it in active_transaction."""
        from apps.transaction.tests.factories import TransactionFactory
        from apps.transaction.constants import TransactionStatus, PartyType
        from apps.core.constants import ContextType

        TransactionFactory(
            transaction_type="business_membership_request",
            mode="request",
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            target_type=PartyType.ACCOUNT,
            target_id=another_business.id,
            context_type=ContextType.BUSINESS,
            context_id=another_business.id,
            status=TransactionStatus.PENDING,
        )

        response = authenticated_client.get(
            f"/api/v1/business/{another_business.slug}/"
        )
        rel = response.data["_relationship"]
        assert rel["active_transaction"] is not None
        assert rel["active_transaction"]["type"] == "business_membership_request"
        assert rel["active_transaction"]["mode"] == "request"

    def test_pending_invitation_shows_active_transaction(
        self, authenticated_client, user, another_business,
    ):
        """User with a pending invitation sees it in active_transaction."""
        from apps.transaction.tests.factories import TransactionFactory
        from apps.transaction.constants import TransactionStatus, PartyType
        from apps.core.constants import ContextType

        TransactionFactory(
            transaction_type="business_membership_invitation",
            mode="invitation",
            initiator_type=PartyType.MEMBERSHIP_ACTOR,
            target_type=PartyType.USER,
            target_id=user.id,
            context_type=ContextType.BUSINESS,
            context_id=another_business.id,
            status=TransactionStatus.PENDING,
        )

        response = authenticated_client.get(
            f"/api/v1/business/{another_business.slug}/"
        )
        rel = response.data["_relationship"]
        assert rel["active_transaction"] is not None
        assert rel["active_transaction"]["type"] == "business_membership_invitation"
        assert rel["active_transaction"]["mode"] == "invitation"

    def test_patch_response_excludes_relationship(
        self, authenticated_client, business_with_profile,
    ):
        """PATCH response does NOT include _relationship."""
        response = authenticated_client.patch(
            f"/api/v1/business/{business_with_profile.slug}/",
            {"legal_name": "Patched Corp"},
            format="json",
        )
        assert response.status_code == 200
        assert "_relationship" not in response.data

    def test_get_by_id_includes_relationship(
        self, authenticated_client, business_with_profile,
    ):
        """GET by UUID also includes _relationship."""
        response = authenticated_client.get(
            f"/api/v1/business/id/{business_with_profile.id}/"
        )
        assert response.status_code == 200
        assert "_relationship" in response.data

    def test_pending_request_includes_viewer_role_initiator(
        self, authenticated_client, user, another_business,
    ):
        """User who created a request sees viewer_role='initiator'."""
        from apps.transaction.tests.factories import TransactionFactory
        from apps.transaction.constants import TransactionStatus, PartyType
        from apps.core.constants import ContextType

        TransactionFactory(
            transaction_type="business_membership_request",
            mode="request",
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            target_type=PartyType.ACCOUNT,
            target_id=another_business.id,
            context_type=ContextType.BUSINESS,
            context_id=another_business.id,
            status=TransactionStatus.PENDING,
        )

        response = authenticated_client.get(
            f"/api/v1/business/{another_business.slug}/"
        )
        rel = response.data["_relationship"]
        assert rel["active_transaction"]["viewer_role"] == "initiator"

    def test_pending_invitation_includes_viewer_role_target(
        self, authenticated_client, user, another_business,
    ):
        """User who is target of an invitation sees viewer_role='target'."""
        from apps.transaction.tests.factories import TransactionFactory
        from apps.transaction.constants import TransactionStatus, PartyType
        from apps.core.constants import ContextType

        TransactionFactory(
            transaction_type="business_membership_invitation",
            mode="invitation",
            initiator_type=PartyType.MEMBERSHIP_ACTOR,
            target_type=PartyType.USER,
            target_id=user.id,
            context_type=ContextType.BUSINESS,
            context_id=another_business.id,
            status=TransactionStatus.PENDING,
        )

        response = authenticated_client.get(
            f"/api/v1/business/{another_business.slug}/"
        )
        rel = response.data["_relationship"]
        assert rel["active_transaction"]["viewer_role"] == "target"

    def test_active_follow_shows_follow_id(
        self, authenticated_client, user, another_business,
    ):
        """Following a business populates follow_id in _relationship."""
        from apps.network.tests.factories import FollowFactory

        follow = FollowFactory(
            follower=user,
            followee_type="business",
            followee_id=another_business.id,
        )

        response = authenticated_client.get(
            f"/api/v1/business/{another_business.slug}/"
        )
        rel = response.data["_relationship"]
        assert rel["follow_status"] == "active"
        assert rel["follow_id"] == str(follow.id)


@pytest.mark.django_db
class TestBusinessSlugUpdateView:
    """Tests for BusinessSlugUpdateView endpoint."""

    def test_update_slug(self, authenticated_client, business_with_profile):
        """Test changing business slug."""
        response = authenticated_client.patch(
            f"/api/v1/business/{business_with_profile.slug}/slug/",
            {"slug": "new-slug-name"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["slug"] == "new-slug-name"

    def test_update_slug_as_non_owner_forbidden(
        self, authenticated_client, another_business
    ):
        """Test that non-owners cannot change slug."""
        response = authenticated_client.patch(
            f"/api/v1/business/{another_business.slug}/slug/",
            {"slug": "hacked-slug"},
            format="json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestBusinessProfileView:
    """Tests for BusinessProfileView endpoints."""

    def test_get_profile(self, authenticated_client, business_with_profile):
        """Test getting business profile."""
        response = authenticated_client.get(
            f"/api/v1/business/{business_with_profile.slug}/profile/"
        )

        assert response.status_code == 200
        assert "display_name" in response.data

    def test_update_profile(self, authenticated_client, business_with_profile):
        """Test updating business profile."""
        response = authenticated_client.patch(
            f"/api/v1/business/{business_with_profile.slug}/profile/",
            {"display_name": "Updated Display", "tagline": "New tagline"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["display_name"] == "Updated Display"

    def test_update_profile_as_non_owner_forbidden(
        self, authenticated_client, another_business
    ):
        """Test that non-owners cannot update profile."""
        response = authenticated_client.patch(
            f"/api/v1/business/{another_business.slug}/profile/",
            {"display_name": "Hacked"},
            format="json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestBusinessSuspendView:
    """Tests for BusinessSuspendView endpoint."""

    def test_suspend_as_staff(self, staff_client, business_with_profile):
        """Test suspending business as staff."""
        response = staff_client.post(
            f"/api/v1/business/{business_with_profile.slug}/suspend/",
            {"reason": "Violation of terms"},
            format="json",
        )

        assert response.status_code == 200
        assert response.data["status"] == "suspended"

    def test_suspend_as_regular_user_forbidden(
        self, authenticated_client, business_with_profile
    ):
        """Test that regular users cannot suspend businesses."""
        response = authenticated_client.post(
            f"/api/v1/business/{business_with_profile.slug}/suspend/",
            {"reason": "I want to"},
            format="json",
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestBusinessReactivateView:
    """Tests for BusinessReactivateView endpoint."""

    def test_reactivate_as_staff(self, staff_client, suspended_business):
        """Test reactivating business as staff."""
        response = staff_client.post(
            f"/api/v1/business/{suspended_business.slug}/reactivate/"
        )

        assert response.status_code == 200
        assert response.data["status"] == "active"

    def test_reactivate_as_regular_user_forbidden(
        self, authenticated_client, suspended_business
    ):
        """Test that regular users cannot reactivate businesses."""
        response = authenticated_client.post(
            f"/api/v1/business/{suspended_business.slug}/reactivate/"
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestBusinessArchiveView:
    """Tests for BusinessArchiveView endpoint."""

    def test_archive_as_owner(self, authenticated_client, business_with_profile):
        """Test archiving business as owner."""
        response = authenticated_client.post(
            f"/api/v1/business/{business_with_profile.slug}/archive/"
        )

        assert response.status_code == 200
        assert response.data["status"] == "archived"

    def test_archive_as_non_owner_forbidden(
        self, authenticated_client, another_business
    ):
        """Test that non-owners cannot archive businesses."""
        response = authenticated_client.post(
            f"/api/v1/business/{another_business.slug}/archive/"
        )

        assert response.status_code == 403


@pytest.mark.django_db
class TestBusinessDetailViewAnonymous:
    """Tests for anonymous (unauthenticated) access to BusinessDetailView."""

    def test_anonymous_get_public_profile_returns_200(self, api_client, db):
        """Anonymous GET to /api/v1/business/{slug}/ returns 200 for active business with public profile."""
        from apps.organization.tests.factories import BusinessAccountWithProfileFactory

        business = BusinessAccountWithProfileFactory()

        response = api_client.get(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 200
        assert response.data["slug"] == business.slug

    def test_anonymous_get_private_profile_returns_403(self, api_client, db):
        """Anonymous GET returns 403 for business with is_public=False profile."""
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
        )

        business = BusinessAccountFactory()
        BusinessProfileFactory(business=business, is_public=False)

        response = api_client.get(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 403

    def test_anonymous_get_suspended_business_returns_403(self, api_client, db):
        """Anonymous GET returns 403 for suspended business even with public profile."""
        from apps.organization.tests.factories import (
            SuspendedBusinessFactory,
            BusinessProfileFactory,
        )

        business = SuspendedBusinessFactory()
        BusinessProfileFactory(business=business, is_public=True)

        response = api_client.get(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 403

    def test_anonymous_get_returns_permissions(self, api_client, db):
        """Anonymous GET returns _permissions dict with can_view=True and all others False."""
        from apps.organization.tests.factories import BusinessAccountWithProfileFactory

        business = BusinessAccountWithProfileFactory()

        response = api_client.get(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 200
        assert "_permissions" in response.data
        perms = response.data["_permissions"]
        assert perms["can_view"] is True
        assert perms["can_edit"] is False
        assert perms["can_edit_profile"] is False
        assert perms["can_delete"] is False
        assert perms["can_change_slug"] is False
        assert perms["can_archive"] is False

    def test_anonymous_patch_returns_403(self, api_client, db):
        """Anonymous PATCH to /api/v1/business/{slug}/ returns 403."""
        from apps.organization.tests.factories import BusinessAccountWithProfileFactory

        business = BusinessAccountWithProfileFactory()

        response = api_client.patch(
            f"/api/v1/business/{business.slug}/",
            {"legal_name": "Hacked Name"},
            format="json",
        )

        assert response.status_code == 403

    def test_anonymous_delete_returns_403(self, api_client, db):
        """Anonymous DELETE to /api/v1/business/{slug}/ returns 403."""
        from apps.organization.tests.factories import BusinessAccountWithProfileFactory

        business = BusinessAccountWithProfileFactory()

        response = api_client.delete(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 403


# =============================================================================
# VISIBILITY FILTERING TESTS
# =============================================================================


@pytest.mark.django_db
class TestBusinessVisibilityFiltering:
    """Tests for T2/T3 field filtering on business detail views."""

    def test_owner_sees_all_fields(self, authenticated_client, business_with_profile):
        """Owner sees all fields including T3 (registration_number, settings)."""
        business_with_profile.registration_number = "REG123"
        business_with_profile.settings = {"key": "val"}
        business_with_profile.save(update_fields=["registration_number", "settings"])
        business_with_profile.profile.contact_email = "hi@acme.com"
        business_with_profile.profile.save(update_fields=["contact_email"])

        response = authenticated_client.get(
            f"/api/v1/business/{business_with_profile.slug}/"
        )

        assert response.status_code == 200
        assert response.data["registration_number"] == "REG123"
        assert response.data["settings"] == {"key": "val"}
        assert response.data["profile"]["contact_email"] == "hi@acme.com"

    def test_anonymous_public_business_sees_t1_and_t2(self, api_client, db):
        """Anonymous viewer of public business sees T1 + T2 fields (is_public=True)."""
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
        )

        business = BusinessAccountFactory(registration_number="REG123")
        BusinessProfileFactory(
            business=business,
            is_public=True,
            contact_email="hi@acme.com",
        )

        response = api_client.get(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 200
        # T1 fields visible
        assert "slug" in response.data
        assert "legal_name" in response.data
        # T2 visible (is_public=True → global override)
        assert response.data["profile"]["contact_email"] == "hi@acme.com"
        # T3 hidden from anonymous
        assert "registration_number" not in response.data
        assert "settings" not in response.data

    def test_non_member_authenticated_public_sees_t1_t2_not_t3(
        self, api_client, db
    ):
        """Authenticated non-member viewing public business: T1+T2 visible, T3 hidden."""
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
            UserFactory,
        )

        viewer = UserFactory()
        business = BusinessAccountFactory(registration_number="REG789")
        BusinessProfileFactory(
            business=business,
            is_public=True,
            contact_email="contact@acme.com",
        )

        api_client.force_authenticate(user=viewer)
        response = api_client.get(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 200
        # T2 visible (public)
        assert response.data["profile"]["contact_email"] == "contact@acme.com"
        # T3 hidden (not a member)
        assert "registration_number" not in response.data
        assert "settings" not in response.data
        assert "max_members" not in response.data

    def test_member_sees_t3_fields(self, api_client, db):
        """Member with can_view_legal_info sees T3 registration_number."""
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
            UserFactory,
        )
        from apps.rbac.services import RBACService
        from apps.rbac.selectors import RoleSelector
        from apps.core.constants import AccountType

        owner = UserFactory()
        business = BusinessAccountFactory(
            registration_number="REG456",
            created_by=owner,
            updated_by=owner,
        )
        BusinessProfileFactory(business=business)
        RBACService.initialize_business_account(
            business_id=business.id, owner=owner,
        )

        api_client.force_authenticate(user=owner)
        response = api_client.get(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 200
        # Owner sees everything
        assert response.data["registration_number"] == "REG456"
        assert "settings" in response.data

    def test_is_limited_flag_on_private_non_member(self, api_client, db):
        """Non-member viewing private business gets is_limited=True."""
        from unittest.mock import patch
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
            UserFactory,
        )

        viewer = UserFactory()
        business = BusinessAccountFactory()
        BusinessProfileFactory(business=business, is_public=False)

        api_client.force_authenticate(user=viewer)

        # Mock follower check to return False (viewer is not a follower)
        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=False,
        ):
            response = api_client.get(f"/api/v1/business/{business.slug}/")

        # Private business, not a member → 403 from can_view_profile
        # Actually, can_view() returns True for authenticated users on active business.
        # But is_limited is set based on viewer_access.is_member AND is_public.
        assert response.status_code == 200
        assert response.data.get("is_limited") is True

    def test_no_is_limited_flag_on_public(self, api_client, db):
        """Public business response does NOT have is_limited flag."""
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
            UserFactory,
        )

        viewer = UserFactory()
        business = BusinessAccountFactory()
        BusinessProfileFactory(business=business, is_public=True)

        api_client.force_authenticate(user=viewer)
        response = api_client.get(f"/api/v1/business/{business.slug}/")

        assert response.status_code == 200
        assert "is_limited" not in response.data

    def test_by_id_view_also_applies_visibility(self, api_client, db):
        """BusinessByIdView also applies visibility filtering."""
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
            UserFactory,
        )

        viewer = UserFactory()
        business = BusinessAccountFactory(registration_number="REG999")
        BusinessProfileFactory(
            business=business,
            is_public=True,
            contact_email="id@acme.com",
        )

        api_client.force_authenticate(user=viewer)
        response = api_client.get(f"/api/v1/business/id/{business.id}/")

        assert response.status_code == 200
        # T2 visible (public)
        assert response.data["profile"]["contact_email"] == "id@acme.com"
        # T3 hidden (not member)
        assert "registration_number" not in response.data

    def test_follower_can_view_private_profile(self, api_client, db):
        """Follower can view a private business profile (not 403)."""
        from unittest.mock import patch
        from apps.organization.tests.factories import (
            BusinessAccountFactory,
            BusinessProfileFactory,
            UserFactory,
        )

        viewer = UserFactory()
        business = BusinessAccountFactory()
        BusinessProfileFactory(business=business, is_public=False)

        api_client.force_authenticate(user=viewer)

        with patch(
            "apps.network.selectors.FollowSelector.is_following",
            return_value=True,
        ):
            response = api_client.get(
                f"/api/v1/business/{business.slug}/profile/"
            )

        assert response.status_code == 200
        assert "display_name" in response.data


# =============================================================================
# Visibility Settings Tests
# =============================================================================


@pytest.mark.django_db
class TestBusinessProfileVisibilityView:
    """Tests for GET/PATCH /api/v1/business/{slug}/profile/visibility/"""

    def _url(self, slug):
        return f"/api/v1/business/{slug}/profile/visibility/"

    def test_get_returns_t2_fields(self, authenticated_client, business_with_profile):
        """GET returns list of T2 fields with current levels and choices."""
        response = authenticated_client.get(
            self._url(business_with_profile.slug)
        )

        assert response.status_code == 200
        data = response.data
        assert isinstance(data, list)
        assert len(data) == 2  # contact_email, contact_phone

        field_names = {item["field_name"] for item in data}
        assert field_names == {"contact_email", "contact_phone"}

        # Check structure of each item
        for item in data:
            assert "field_name" in item
            assert "current_level" in item
            assert "default_level" in item
            assert "choices" in item
            assert isinstance(item["choices"], list)
            assert len(item["choices"]) == 4  # Members, Connected, Followers, World

    def test_get_default_levels(self, authenticated_client, business_with_profile):
        """GET returns correct default levels (FOLLOWERS=2 for contact fields)."""
        response = authenticated_client.get(
            self._url(business_with_profile.slug)
        )

        for item in response.data:
            assert item["default_level"] == 2  # BusinessVisibility.FOLLOWERS
            assert item["current_level"] == 2  # No overrides yet

    def test_patch_updates_overrides(self, authenticated_client, business_with_profile):
        """PATCH updates visibility overrides and returns updated settings."""
        response = authenticated_client.patch(
            self._url(business_with_profile.slug),
            {"overrides": {"contact_email": 3}},  # Set to WORLD
            format="json",
        )

        assert response.status_code == 200

        # Verify the response shows updated level
        email_setting = next(
            item for item in response.data if item["field_name"] == "contact_email"
        )
        assert email_setting["current_level"] == 3

        # Verify persisted
        business_with_profile.profile.refresh_from_db()
        assert business_with_profile.profile.visibility_overrides == {
            "contact_email": 3,
        }

    def test_patch_invalid_field_name(self, authenticated_client, business_with_profile):
        """PATCH rejects non-T2 field names."""
        response = authenticated_client.patch(
            self._url(business_with_profile.slug),
            {"overrides": {"display_name": 3}},  # T1 field
            format="json",
        )

        assert response.status_code == 400

    def test_patch_invalid_level(self, authenticated_client, business_with_profile):
        """PATCH rejects out-of-range visibility levels."""
        response = authenticated_client.patch(
            self._url(business_with_profile.slug),
            {"overrides": {"contact_email": 99}},
            format="json",
        )

        assert response.status_code == 400

    def test_non_member_cannot_access(self, api_client, business_with_profile, non_member_user):
        """Non-members cannot view or update visibility settings."""
        api_client.force_authenticate(user=non_member_user)

        response = api_client.get(self._url(business_with_profile.slug))
        assert response.status_code == 403

        response = api_client.patch(
            self._url(business_with_profile.slug),
            {"overrides": {"contact_email": 3}},
            format="json",
        )
        assert response.status_code == 403

    def test_unauthenticated_cannot_access(self, api_client, business_with_profile):
        """Unauthenticated users cannot access visibility settings."""
        response = api_client.get(self._url(business_with_profile.slug))
        assert response.status_code == 401

    def test_patch_merges_overrides(self, authenticated_client, business_with_profile):
        """PATCH merges new overrides with existing ones."""
        # First update
        authenticated_client.patch(
            self._url(business_with_profile.slug),
            {"overrides": {"contact_email": 3}},
            format="json",
        )

        # Second update (should merge, not replace)
        response = authenticated_client.patch(
            self._url(business_with_profile.slug),
            {"overrides": {"contact_phone": 0}},
            format="json",
        )

        assert response.status_code == 200
        business_with_profile.profile.refresh_from_db()
        assert business_with_profile.profile.visibility_overrides == {
            "contact_email": 3,
            "contact_phone": 0,
        }
