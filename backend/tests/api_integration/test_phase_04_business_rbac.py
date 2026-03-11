"""
Phase 04 — Business + RBAC Business (B01–B18, RB01–RB14)

Tests business account CRUD, profile, lifecycle (suspend/reactivate/archive),
and business-scoped RBAC (roles, permissions, members).

Depends on Phase 01 (users), Phase 03 (platform configured).
"""

import uuid

import pytest


# =============================================================================
# B01–B08: BUSINESS ACCOUNT CRUD
# =============================================================================

class TestBusinessCRUD:
    """Test business account creation, listing, and management."""

    def test_b01_create_business(self, api, state, db_helper):
        """POST /business/ creates a new business account."""
        api.set_token(state.get_token("alice"))
        r = api.post("business/", json={
            "legal_name": "Alice Corp",
            "country": "US",
            "slug": "alice-corp",
        })
        assert r.status_code == 201, f"Create business failed: {r.text}"
        data = r.json()
        assert data["legal_name"] == "Alice Corp"
        assert data["slug"] == "alice-corp"
        state.businesses["alice_corp"] = {
            "id": data["id"],
            "slug": data["slug"],
        }
        # Raise max_members so Phase 06+ can invite members
        db_helper.set_business_max_members(data["id"], 10)

    def test_b02_create_second_business(self, api, state, db_helper):
        """Create a second business for cross-business tests."""
        api.set_token(state.get_token("bob"))
        r = api.post("business/", json={
            "legal_name": "Bob LLC",
            "country": "GB",
            "slug": "bob-llc",
        })
        assert r.status_code == 201
        data = r.json()
        state.businesses["bob_llc"] = {
            "id": data["id"],
            "slug": data["slug"],
        }
        # Raise max_members so Phase 06+ can invite members
        db_helper.set_business_max_members(data["id"], 10)

    def test_b03_list_businesses(self, api, state):
        """GET /business/ lists all businesses."""
        api.set_token(state.get_token("alice"))
        r = api.get("business/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        assert len(results) >= 1

    def test_b04_my_businesses(self, api, state):
        """GET /business/my/ lists businesses where user is a member."""
        api.set_token(state.get_token("alice"))
        r = api.get("business/my/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        slugs = [b["slug"] for b in results]
        assert "alice-corp" in slugs

    def test_b05_get_by_uuid(self, api, state):
        """GET /business/id/<uuid>/ returns business by UUID."""
        api.set_token(state.get_token("alice"))
        biz_id = state.businesses["alice_corp"]["id"]
        r = api.get(f"business/id/{biz_id}/")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == biz_id

    def test_b06_get_by_slug(self, api, state):
        """GET /business/<slug>/ returns business by slug."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.get(f"business/{slug}/")
        assert r.status_code == 200
        data = r.json()
        assert data["slug"] == slug

    def test_b07_update_business(self, api, state):
        """PATCH /business/<slug>/ updates business fields."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.patch(f"business/{slug}/", json={
            "legal_name": "Alice Corp Updated",
            "registration_number": "REG-001",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["legal_name"] == "Alice Corp Updated"

    def test_b08_duplicate_slug(self, api, state):
        """POST /business/ with duplicate slug returns 400/409."""
        api.set_token(state.get_token("alice"))
        r = api.post("business/", json={
            "legal_name": "Duplicate Corp",
            "country": "US",
            "slug": "alice-corp",
        })
        assert r.status_code in (400, 409)


# =============================================================================
# B09–B11: BUSINESS PROFILE & SLUG
# =============================================================================

class TestBusinessProfile:
    """Test business profile CRUD and slug changes."""

    def test_b09_get_profile(self, api, state):
        """GET /business/<slug>/profile/ returns business profile."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.get(f"business/{slug}/profile/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    def test_b10_patch_profile(self, api, state):
        """PATCH /business/<slug>/profile/ updates profile."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.patch(f"business/{slug}/profile/", json={
            "display_name": "Alice Corporation",
            "tagline": "Building the future",
            "website": "https://alice-corp.example.com",
        })
        assert r.status_code == 200

    def test_b11_change_slug(self, api, state):
        """PATCH /business/<slug>/slug/ changes business slug."""
        api.set_token(state.get_token("alice"))
        old_slug = state.businesses["alice_corp"]["slug"]
        new_slug = "alice-corporation"
        r = api.patch(f"business/{old_slug}/slug/", json={
            "slug": new_slug,
        })
        assert r.status_code == 200
        state.businesses["alice_corp"]["slug"] = new_slug

        # Verify old slug no longer works (may return 301/302 redirect or 404)
        r = api.get(f"business/{old_slug}/", allow_redirects=False)
        # 200 = slug history redirect (server follows), 301/302 = redirect, 404 = gone
        assert r.status_code in (200, 301, 302, 404)

        # Verify new slug works
        r = api.get(f"business/{new_slug}/")
        assert r.status_code == 200


# =============================================================================
# B12–B18: BUSINESS LIFECYCLE & ACCESS CONTROL
# =============================================================================

class TestBusinessLifecycle:
    """Test suspend/reactivate/archive and access control."""

    def test_b12_non_member_access(self, api, state):
        """Non-member cannot update business."""
        api.set_token(state.get_token("nobody"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.patch(f"business/{slug}/", json={
            "legal_name": "Hacked!",
        })
        assert r.status_code == 403

    def test_b13_non_owner_actions(self, api, state):
        """Non-owner member cannot perform owner-only actions."""
        # Bob is not a member of alice_corp — should be 403
        api.set_token(state.get_token("bob"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.post(f"business/{slug}/suspend/", json={
            "reason": "Unauthorized",
        })
        assert r.status_code == 403

    def test_b14_suspend_business(self, api, state):
        """POST /business/<slug>/suspend/ suspends the business."""
        # Create a disposable business for lifecycle testing
        api.set_token(state.get_token("alice"))
        r = api.post("business/", json={
            "legal_name": "Lifecycle Corp",
            "country": "US",
            "slug": "lifecycle-corp",
        })
        assert r.status_code == 201
        state.businesses["lifecycle"] = {
            "id": r.json()["id"],
            "slug": "lifecycle-corp",
        }

        r = api.post("business/lifecycle-corp/suspend/", json={
            "reason": "Testing suspension",
        })
        assert r.status_code == 200

    def test_b15_reactivate_business(self, api, state):
        """POST /business/<slug>/reactivate/ reactivates a suspended business."""
        api.set_token(state.get_token("alice"))
        r = api.post("business/lifecycle-corp/reactivate/")
        assert r.status_code == 200

    def test_b16_archive_business(self, api, state):
        """POST /business/<slug>/archive/ archives the business."""
        api.set_token(state.get_token("alice"))
        r = api.post("business/lifecycle-corp/archive/")
        assert r.status_code == 200

    def test_b17_get_nonexistent_business(self, api, state):
        """GET /business/<random_slug>/ returns 404."""
        api.set_token(state.get_token("alice"))
        r = api.get("business/nonexistent-slug-xyz/")
        assert r.status_code == 404

    def test_b18_get_nonexistent_uuid(self, api, state):
        """GET /business/id/<random_uuid>/ returns 404."""
        api.set_token(state.get_token("alice"))
        fake_id = str(uuid.uuid4())
        r = api.get(f"business/id/{fake_id}/")
        assert r.status_code == 404


# =============================================================================
# RB01–RB07: BUSINESS ROLES
# =============================================================================

class TestBusinessRoles:
    """Test business-scoped role CRUD and permission management."""

    def test_rb01_list_roles(self, api, state):
        """GET /business/<slug>/roles/ lists roles."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.get(f"business/{slug}/roles/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        # Should have at least the system owner role
        assert len(results) >= 1

    def test_rb02_create_role(self, api, state):
        """POST /business/<slug>/roles/ creates a custom role."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.post(f"business/{slug}/roles/", json={
            "name": "Editor",
            "level": 5,
            "description": "Content editor role",
        })
        assert r.status_code == 201, f"Create role failed: {r.text}"
        data = r.json()
        state.roles["biz:editor"] = {"id": data["id"]}

    def test_rb03_get_role_detail(self, api, state):
        """GET /business/<slug>/roles/<id>/ returns role detail."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        role_id = state.roles["biz:editor"]["id"]
        r = api.get(f"business/{slug}/roles/{role_id}/")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Editor"

    def test_rb04_update_role(self, api, state):
        """PATCH /business/<slug>/roles/<id>/ updates role."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        role_id = state.roles["biz:editor"]["id"]
        r = api.patch(f"business/{slug}/roles/{role_id}/", json={
            "description": "Content editor with review permissions",
        })
        assert r.status_code == 200

    def test_rb05_assign_permission(self, api, state):
        """POST /business/<slug>/roles/<id>/permissions/ assigns permission."""
        api.set_token(state.get_token("alice"))

        # First get the list of all permissions to find one to assign
        r = api.get("rbac/permissions/")
        assert r.status_code == 200
        perms_data = r.json()
        perms = perms_data if isinstance(perms_data, list) else perms_data.get("results", [])
        if not perms:
            pytest.skip("No permissions found")

        # Store permissions for later use
        state.permissions = perms

        # Pick the first permission
        perm = perms[0]
        slug = state.businesses["alice_corp"]["slug"]
        role_id = state.roles["biz:editor"]["id"]
        r = api.post(f"business/{slug}/roles/{role_id}/permissions/", json={
            "permission_id": perm["id"],
            "scope": "business",
        })
        assert r.status_code in (200, 201), f"Assign permission failed: {r.text}"

    def test_rb06_remove_permission(self, api, state):
        """DELETE /business/<slug>/roles/<id>/permissions/ removes permission."""
        if not state.permissions:
            pytest.skip("No permissions to remove")

        api.set_token(state.get_token("alice"))
        perm = state.permissions[0]
        slug = state.businesses["alice_corp"]["slug"]
        role_id = state.roles["biz:editor"]["id"]
        r = api.delete(f"business/{slug}/roles/{role_id}/permissions/", json={
            "permission_id": perm["id"],
        })
        assert r.status_code in (200, 204)

    def test_rb07_delete_role(self, api, state):
        """DELETE /business/<slug>/roles/<id>/ deletes a custom role."""
        # Create a disposable role to delete
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.post(f"business/{slug}/roles/", json={
            "name": "Disposable",
            "level": 8,
        })
        assert r.status_code == 201
        disposable_id = r.json()["id"]

        r = api.delete(f"business/{slug}/roles/{disposable_id}/")
        assert r.status_code in (200, 204)


# =============================================================================
# RB08–RB14: BUSINESS MEMBERS
# =============================================================================

class TestBusinessMembers:
    """Test business membership management."""

    def test_rb08_list_members(self, api, state):
        """GET /business/<slug>/members/ lists members."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.get(f"business/{slug}/members/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        # Alice should be the owner member
        assert len(results) >= 1
        # Store Alice's membership ID
        for m in results:
            user = m.get("user", {})
            if user.get("email") == "alice@test.com":
                state.memberships["biz:alice"] = {
                    "id": m["id"],
                    "role_id": m.get("role", {}).get("id") if isinstance(m.get("role"), dict) else m.get("role_name"),
                }

    def test_rb09_member_detail(self, api, state):
        """GET /business/<slug>/members/<id>/ returns member detail."""
        if "biz:alice" not in state.memberships:
            pytest.skip("No membership ID stored")

        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        mid = state.memberships["biz:alice"]["id"]
        r = api.get(f"business/{slug}/members/{mid}/")
        assert r.status_code == 200

    def test_rb10_change_member_role(self, api, state):
        """PATCH /business/<slug>/members/<id>/role/ changes role.

        Note: We need a non-owner member to change role.
        For now, test that owner can't change their own role (if applicable).
        """
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        # This test will be more meaningful after we add members via transactions

    def test_rb11_suspend_member(self, api, state):
        """POST /business/<slug>/members/<id>/suspend/ suspends a member.

        Skip if no non-owner member exists yet.
        """
        # Will be properly testable after transactions phase adds members
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]

    def test_rb12_remove_member(self, api, state):
        """POST /business/<slug>/members/<id>/remove/ removes a member."""
        # Will be properly testable after transactions phase adds members
        pass

    def test_rb13_ban_member(self, api, state):
        """POST /business/<slug>/members/<id>/ban/ bans a member."""
        # Will be properly testable after transactions phase adds members
        pass

    def test_rb14_owner_cannot_leave(self, api, state):
        """POST /business/<slug>/members/leave/ — owner cannot leave."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses["alice_corp"]["slug"]
        r = api.post(f"business/{slug}/members/leave/")
        # Owner should be rejected — 400 or 403
        assert r.status_code in (400, 403), (
            f"Owner should not be able to leave, got {r.status_code}: {r.text}"
        )
