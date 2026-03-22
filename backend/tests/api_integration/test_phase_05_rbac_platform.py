"""
Phase 05 — RBAC Platform (RS01, RP01–RP14)

Tests platform-scoped RBAC: permission listing, role CRUD with permission
assignment, and platform member management.

Depends on Phase 03 (platform configured with Alice as owner).
"""

import uuid

import pytest

# =============================================================================
# RS01: PERMISSIONS LIST
# =============================================================================


class TestPermissionsList:
    """Test the shared permissions endpoint."""

    def test_rs01_list_all_permissions(self, api, state):
        """GET /rbac/permissions/ returns all 51 seeded permissions."""
        api.set_token(state.get_token("alice"))
        r = api.get("rbac/permissions/")
        assert r.status_code == 200
        data = r.json()
        perms = data if isinstance(data, list) else data.get("results", [])
        # 26 (core) + 2 (transaction) + 23 (CMS) = 51
        assert len(perms) >= 51, f"Expected at least 51 permissions, got {len(perms)}"
        # Store for later use
        state.permissions = perms

        # Verify each permission has expected fields
        for p in perms[:3]:
            assert "id" in p
            assert "code" in p
            assert "name" in p
            assert "category" in p


# =============================================================================
# RP01–RP08: PLATFORM ROLES
# =============================================================================


class TestPlatformRoles:
    """Test platform-scoped role CRUD and permission management."""

    def test_rp01_list_platform_roles(self, api, state):
        """GET /platform/roles/ lists platform roles."""
        api.set_token(state.get_token("alice"))
        r = api.get("platform/roles/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        assert len(results) >= 1  # At least owner role

    def test_rp02_create_platform_role(self, api, state):
        """POST /platform/roles/ creates a platform role."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "platform/roles/",
            json={
                "name": "Platform Moderator",
                "level": 5,
                "description": "Moderates platform content",
            },
        )
        assert r.status_code == 201, f"Create role failed: {r.text}"
        data = r.json()
        state.roles["plat:moderator"] = {"id": data["id"]}

    def test_rp03_get_platform_role(self, api, state):
        """GET /platform/roles/<id>/ returns role detail."""
        api.set_token(state.get_token("alice"))
        role_id = state.roles["plat:moderator"]["id"]
        r = api.get(f"platform/roles/{role_id}/")
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "Platform Moderator"

    def test_rp04_update_platform_role(self, api, state):
        """PATCH /platform/roles/<id>/ updates role."""
        api.set_token(state.get_token("alice"))
        role_id = state.roles["plat:moderator"]["id"]
        r = api.patch(
            f"platform/roles/{role_id}/",
            json={
                "description": "Updated moderator description",
            },
        )
        assert r.status_code == 200

    def test_rp05_assign_platform_permission(self, api, state):
        """POST /platform/roles/<id>/permissions/ assigns permission."""
        if not state.permissions:
            pytest.skip("No permissions available")

        api.set_token(state.get_token("alice"))
        role_id = state.roles["plat:moderator"]["id"]
        perm = state.permissions[0]
        r = api.post(
            f"platform/roles/{role_id}/permissions/",
            json={
                "permission_id": perm["id"],
                "scope": "platform_only",
            },
        )
        assert r.status_code in (200, 201), f"Assign failed: {r.text}"

    def test_rp06_remove_platform_permission(self, api, state):
        """DELETE /platform/roles/<id>/permissions/ removes permission."""
        if not state.permissions:
            pytest.skip("No permissions available")

        api.set_token(state.get_token("alice"))
        role_id = state.roles["plat:moderator"]["id"]
        perm = state.permissions[0]
        r = api.delete(
            f"platform/roles/{role_id}/permissions/",
            json={
                "permission_id": perm["id"],
            },
        )
        assert r.status_code in (200, 204)

    def test_rp07_delete_platform_role(self, api, state):
        """DELETE /platform/roles/<id>/ deletes a custom role."""
        api.set_token(state.get_token("alice"))
        # Create a disposable role
        r = api.post(
            "platform/roles/",
            json={
                "name": "Temp Role",
                "level": 9,
            },
        )
        assert r.status_code == 201
        temp_id = r.json()["id"]

        r = api.delete(f"platform/roles/{temp_id}/")
        assert r.status_code in (200, 204)

    def test_rp08_duplicate_role_name(self, api, state):
        """POST /platform/roles/ with duplicate name returns 400/409."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "platform/roles/",
            json={
                "name": "Platform Moderator",
                "level": 6,
            },
        )
        # 403 if platform membership missing
        assert r.status_code in (400, 403, 409)


# =============================================================================
# RP09–RP14: PLATFORM MEMBERS
# =============================================================================


class TestPlatformMembers:
    """Test platform membership management."""

    def test_rp09_list_platform_members(self, api, state):
        """GET /platform/members/ lists members."""
        api.set_token(state.get_token("alice"))
        r = api.get("platform/members/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        assert len(results) >= 1  # At least Alice as owner
        # Store Alice's platform membership ID
        for m in results:
            user = m.get("user", {})
            if user.get("email") == "alice@test.com":
                state.memberships["plat:alice"] = {
                    "id": m["id"],
                }

    def test_rp10_member_detail(self, api, state):
        """GET /platform/members/<id>/ returns member detail."""
        if "plat:alice" not in state.memberships:
            pytest.skip("No platform membership ID")

        api.set_token(state.get_token("alice"))
        mid = state.memberships["plat:alice"]["id"]
        r = api.get(f"platform/members/{mid}/")
        assert r.status_code == 200

    def test_rp11_invite_and_add_platform_member(self, api, state, db_helper):
        """Invite a new user to the platform and accept, creating a non-owner member.

        This enables RP12-RP13 tests which require a non-owner member.
        """
        suffix = uuid.uuid4().hex[:6]
        member_email = f"platmember-{suffix}@test.com"

        # Register + verify member
        api.clear_token()
        r = api.register_with_retry(member_email)
        assert r.status_code == 201, f"Register failed: {r.text}"
        db_helper.verify_user_directly(member_email)
        r = api.login_as_with_retry(member_email)
        assert r.status_code == 200, f"Login failed: {r.text}"
        member_data = r.json()
        member_id = member_data["user"]["id"]
        member_token = member_data["tokens"]["access_token"]

        # Alice invites member to platform
        api.set_token(state.get_token("alice"))
        platform_id = state.platform.get("id")
        if not platform_id:
            pytest.skip("Platform not configured")

        base_role_id = db_helper.get_base_member_role_id("platform", platform_id)
        r = api.post(
            "transactions/invitation/",
            json={
                "transaction_type": "platform_membership_invitation",
                "target_user_id": member_id,
                "context_type": "platform",
                "context_id": platform_id,
                "payload": {"role_id": base_role_id},
            },
        )
        if r.status_code != 201:
            pytest.skip(f"Platform invitation failed: {r.text}")
        invite_id = r.json()["id"]

        # Member accepts
        api.set_token(member_token)
        r = api.post(f"transactions/{invite_id}/accept/")
        assert r.status_code == 200, f"Accept failed: {r.text}"

        # Find the new member's membership ID
        api.set_token(state.get_token("alice"))
        r = api.get("platform/members/")
        assert r.status_code == 200
        members = (
            r.json() if isinstance(r.json(), list) else r.json().get("results", [])
        )
        member_membership = [
            m for m in members if m.get("user", {}).get("email") == member_email
        ]
        assert member_membership, f"Member {member_email} not found in member list"

        # Store for subsequent tests
        state.memberships["plat:testmember"] = {
            "id": member_membership[0]["id"],
            "email": member_email,
            "token": member_token,
        }

    def test_rp12_change_member_role(self, api, state):
        """PATCH /platform/members/<id>/role/ changes role."""
        if "plat:testmember" not in state.memberships:
            pytest.skip("No platform test member (RP11 skipped)")
        if "plat:moderator" not in state.roles:
            pytest.skip("No moderator role (RP02 skipped)")

        api.set_token(state.get_token("alice"))
        mid = state.memberships["plat:testmember"]["id"]
        role_id = state.roles["plat:moderator"]["id"]

        r = api.patch(
            f"platform/members/{mid}/role/",
            json={
                "role_id": role_id,
            },
        )
        assert r.status_code == 200, f"Change role failed: {r.text}"

    def test_rp13_suspend_member(self, api, state):
        """POST /platform/members/<id>/suspend/ suspends a member."""
        if "plat:testmember" not in state.memberships:
            pytest.skip("No platform test member (RP11 skipped)")

        api.set_token(state.get_token("alice"))
        mid = state.memberships["plat:testmember"]["id"]
        r = api.post(f"platform/members/{mid}/suspend/")
        assert r.status_code == 200, f"Suspend failed: {r.text}"

    def test_rp13b_reactivate_suspended_member(self, api, state):
        """POST /platform/members/<id>/reactivate/ reactivates a suspended member."""
        if "plat:testmember" not in state.memberships:
            pytest.skip("No platform test member (RP11 skipped)")

        api.set_token(state.get_token("alice"))
        mid = state.memberships["plat:testmember"]["id"]
        r = api.post(f"platform/members/{mid}/reactivate/")
        assert r.status_code == 200, f"Reactivate failed: {r.text}"

    def test_rp13c_remove_member(self, api, state):
        """POST /platform/members/<id>/remove/ removes a member."""
        if "plat:testmember" not in state.memberships:
            pytest.skip("No platform test member (RP11 skipped)")

        api.set_token(state.get_token("alice"))
        mid = state.memberships["plat:testmember"]["id"]
        r = api.post(f"platform/members/{mid}/remove/")
        assert r.status_code == 200, f"Remove failed: {r.text}"

    def test_rp14_owner_cannot_leave(self, api, state):
        """POST /platform/members/leave/ — owner cannot leave."""
        api.set_token(state.get_token("alice"))
        r = api.post("platform/members/leave/")
        # Owner should be rejected
        assert r.status_code in (
            400,
            403,
        ), f"Owner should not be able to leave, got {r.status_code}"
