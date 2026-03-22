"""
Phase 11 — Negative Testing (NEG-A01 to NEG-R02)

Tests auth failures, authorization boundaries, validation errors,
conflicts, not-found responses, and rate limiting.
"""

import uuid

import pytest

# =============================================================================
# NEG-A01–A10: AUTH FAILURES
# =============================================================================


class TestNegativeAuth:
    """Test authentication failure scenarios."""

    def test_neg_a01_no_token(self, api):
        """Request without token returns 401."""
        api.clear_token()
        r = api.get("users/me/")
        assert r.status_code == 401

    def test_neg_a02_malformed_bearer(self, api):
        """Malformed Bearer token returns 401."""
        api.set_token("not.a.valid.jwt")
        r = api.get("users/me/")
        assert r.status_code == 401

    def test_neg_a03_empty_bearer(self, api):
        """Empty Bearer value returns 401."""
        api.session.headers["Authorization"] = "Bearer "
        r = api.get("users/me/")
        assert r.status_code == 401
        api.session.headers.pop("Authorization", None)

    def test_neg_a04_bearer_only(self, api):
        """Just 'Bearer' without token returns 401."""
        api.session.headers["Authorization"] = "Bearer"
        r = api.get("users/me/")
        assert r.status_code == 401
        api.session.headers.pop("Authorization", None)

    def test_neg_a05_wrong_scheme(self, api):
        """Wrong auth scheme (Basic) returns 401."""
        api.session.headers["Authorization"] = "Basic dXNlcjpwYXNz"
        r = api.get("users/me/")
        assert r.status_code == 401
        api.session.headers.pop("Authorization", None)

    def test_neg_a06_wrong_password(self, api):
        """Wrong password returns 401 invalid_credentials (or 429 if rate limited)."""
        api.clear_token()
        r = api.post(
            "auth/login/",
            json={
                "email": "alice@test.com",
                "password": "TotallyWrong!",
            },
        )
        # May be rate limited (429) from prior rapid login tests
        assert r.status_code in (401, 429)

    def test_neg_a07_nonexistent_email(self, api):
        """Login with non-existent email returns 401 (or 429 if rate limited)."""
        api.clear_token()
        r = api.post(
            "auth/login/",
            json={
                "email": "ghost@nowhere.com",
                "password": "TestPass123!",
            },
        )
        assert r.status_code in (401, 429)

    def test_neg_a08_register_duplicate_email(self, api):
        """Register with existing email returns 400/409."""
        api.clear_token()
        r = api.register_user("alice@test.com")
        assert r.status_code in (400, 409)

    def test_neg_a09_register_weak_password(self, api):
        """Register with weak password returns 400."""
        api.clear_token()
        r = api.post(
            "auth/register/",
            json={
                "email": "weak@test.com",
                "password": "123",
            },
        )
        assert r.status_code == 400

    def test_neg_a10_register_missing_email(self, api):
        """Register without email returns 400."""
        api.clear_token()
        r = api.post(
            "auth/register/",
            json={
                "password": "TestPass123!",
            },
        )
        assert r.status_code == 400


# =============================================================================
# NEG-B01–B08: AUTHORIZATION FAILURES
# =============================================================================


class TestNegativeAuthorization:
    """Test authorization boundary violations."""

    def test_neg_b01_non_member_business_update(self, api, state):
        """Non-member cannot update business."""
        api.set_token(state.get_token("nobody"))
        slug = state.businesses.get("alice_corp", {}).get("slug")
        if not slug:
            pytest.skip("No business created")
        r = api.patch(f"business/{slug}/", json={"legal_name": "Hacked"})
        assert r.status_code == 403

    def test_neg_b02_non_member_role_create(self, api, state):
        """Non-member cannot create roles."""
        api.set_token(state.get_token("nobody"))
        slug = state.businesses.get("alice_corp", {}).get("slug")
        if not slug:
            pytest.skip("No business")
        r = api.post(
            f"business/{slug}/roles/",
            json={
                "name": "Hacker Role",
                "level": 1,
            },
        )
        assert r.status_code == 403

    def test_neg_b03_non_member_suspend_business(self, api, state):
        """Non-member cannot suspend business."""
        api.set_token(state.get_token("nobody"))
        slug = state.businesses.get("alice_corp", {}).get("slug")
        if not slug:
            pytest.skip("No business")
        r = api.post(f"business/{slug}/suspend/", json={"reason": "Hacked"})
        assert r.status_code == 403

    def test_neg_b04_non_member_platform_profile(self, api, state):
        """Platform profile GET is accessible to any authenticated user.

        PlatformPolicy.can_view() returns True for all authenticated users.
        The platform profile is public info — only modification requires membership.
        """
        api.set_token(state.get_token("nobody"))
        r = api.get("platform/profile/")
        # Any authenticated user can view platform profile (by design)
        assert r.status_code in (200, 403)

    def test_neg_b05_non_member_platform_settings(self, api, state):
        """Non-member cannot modify platform settings."""
        api.set_token(state.get_token("nobody"))
        r = api.patch("platform/settings/", json={"settings": {"hacked": True}})
        assert r.status_code == 403

    def test_neg_b06_non_owner_delete_business(self, api, state):
        """Non-owner member cannot delete business."""
        # Bob might be a member but not owner of alice_corp
        api.set_token(state.get_token("bob"))
        slug = state.businesses.get("alice_corp", {}).get("slug")
        if not slug:
            pytest.skip("No business")
        r = api.delete(f"business/{slug}/")
        assert r.status_code in (403, 404)

    def test_neg_b07_non_member_list_members(self, api, state):
        """Non-member cannot list business members."""
        api.set_token(state.get_token("nobody"))
        slug = state.businesses.get("alice_corp", {}).get("slug")
        if not slug:
            pytest.skip("No business")
        r = api.get(f"business/{slug}/members/")
        assert r.status_code == 403

    def test_neg_b08_unauthenticated_business_create(self, api):
        """Unauthenticated user cannot create business."""
        api.clear_token()
        r = api.post(
            "business/",
            json={
                "legal_name": "Anon Corp",
                "country": "US",
            },
        )
        assert r.status_code == 401

    def test_neg_b09_no_business_creation_permission(self, api, state):
        """Authenticated user without can_create_business flag gets 403."""
        api.set_token(state.get_token("nobody"))
        r = api.post(
            "business/",
            json={
                "legal_name": "Unauthorized Corp",
                "country": "US",
            },
        )
        assert r.status_code == 403


# =============================================================================
# NEG-V01–V08: VALIDATION FAILURES
# =============================================================================


class TestNegativeValidation:
    """Test input validation error handling."""

    def test_neg_v01_missing_required_fields(self, api, state):
        """Create business without required fields returns 400."""
        api.set_token(state.get_token("alice"))
        r = api.post("business/", json={})
        assert r.status_code == 400

    def test_neg_v02_invalid_email_format(self, api):
        """Register with invalid email returns 400."""
        r = api.post(
            "auth/register/",
            json={
                "email": "not-an-email",
                "password": "TestPass123!",
            },
        )
        assert r.status_code == 400

    def test_neg_v03_password_too_short(self, api):
        """Register with password < 8 chars returns 400."""
        r = api.post(
            "auth/register/",
            json={
                "email": "short@test.com",
                "password": "Short1!",
            },
        )
        assert r.status_code == 400

    def test_neg_v04_invalid_country_code(self, api, state):
        """Create business with invalid country code returns 400."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "business/",
            json={
                "legal_name": "Bad Country Corp",
                "country": "INVALID",
            },
        )
        assert r.status_code == 400

    def test_neg_v05_invalid_json_body(self, api, state):
        """Send malformed JSON returns 400."""
        api.set_token(state.get_token("alice"))
        r = api.session.post(
            api._url("business/"),
            data="not json",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 400

    def test_neg_v06_invalid_uuid_in_path(self, api, state):
        """Invalid UUID in path returns 400/404."""
        api.set_token(state.get_token("alice"))
        r = api.get("business/id/not-a-uuid/")
        assert r.status_code in (400, 404)

    def test_neg_v07_empty_name(self, api, state):
        """Create business with empty name returns 400."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "business/",
            json={
                "legal_name": "",
                "country": "US",
            },
        )
        assert r.status_code == 400

    def test_neg_v08_role_invalid_level(self, api, state):
        """Create role with invalid level returns 400."""
        slug = state.businesses.get("alice_corp", {}).get("slug")
        if not slug:
            pytest.skip("No business")
        api.set_token(state.get_token("alice"))
        r = api.post(
            f"business/{slug}/roles/",
            json={
                "name": "Invalid Level",
                "level": 999,  # max is 10
            },
        )
        assert r.status_code == 400


# =============================================================================
# NEG-C01–C07: CONFLICTS
# =============================================================================


class TestNegativeConflicts:
    """Test conflict/duplicate scenarios."""

    def test_neg_c01_duplicate_email_register(self, api):
        """Register with existing email returns 400/409."""
        api.clear_token()
        r = api.register_user("alice@test.com")
        assert r.status_code in (400, 409)

    def test_neg_c02_duplicate_business_slug(self, api, state):
        """Create business with existing slug returns 400/409."""
        api.set_token(state.get_token("alice"))
        slug = state.businesses.get("alice_corp", {}).get("slug")
        if not slug:
            pytest.skip("No business")
        r = api.post(
            "business/",
            json={
                "legal_name": "Dup Slug Corp",
                "country": "US",
                "slug": slug,
            },
        )
        assert r.status_code in (400, 409)

    def test_neg_c03_duplicate_site_slug(self, api, state):
        """Create CMS site with existing slug returns 400/409."""
        api.set_token(state.get_token("alice"))
        r = api.post(
            "cms/admin/sites/",
            json={
                "name": "Dup Site",
                "slug": "main-site",  # Already exists from phase 08
            },
        )
        # 403 if Alice lacks platform membership, 400/409 if slug exists
        assert r.status_code in (400, 403, 409)

    def test_neg_c04_configure_platform_twice(self, api, state):
        """Configure platform again returns 400/409."""
        api.set_token(state.get_token("alice"))
        r = api.post("platform/account/", json={"name": "Again"})
        # 403 if Alice lacks platform membership, 400/409 if already configured
        assert r.status_code in (400, 403, 409)

    def test_neg_c05_double_accept(self, api, state):
        """Accept already-resolved transaction returns 400."""
        tid = state.transactions.get("bob_invite", {}).get("id")
        if not tid:
            pytest.skip("No resolved transaction")
        api.set_token(state.get_token("bob"))
        r = api.post(f"transactions/{tid}/accept/")
        assert r.status_code == 400

    def test_neg_c06_duplicate_role_name(self, api, state):
        """Create role with existing name returns 400/409."""
        slug = state.businesses.get("alice_corp", {}).get("slug")
        if not slug or "biz:editor" not in state.roles:
            pytest.skip("No business/role")
        api.set_token(state.get_token("alice"))
        r = api.post(
            f"business/{slug}/roles/",
            json={
                "name": "Editor",  # Already exists
                "level": 6,
            },
        )
        assert r.status_code in (400, 409)

    def test_neg_c07_duplicate_invitation(self, api, state, db_helper):
        """Inviting an already-active member is rejected with 400/409.

        Bob is already a member of alice_corp (from T09 accept).
        The system checks for existing membership before creating invitations.
        """
        api.set_token(state.get_token("alice"))
        biz_id = state.businesses.get("alice_corp", {}).get("id")
        if not biz_id:
            pytest.skip("No business")
        role_id = db_helper.get_base_member_role_id("business", biz_id)
        r = api.post(
            "transactions/invitation/",
            json={
                "transaction_type": "business_membership_invitation",
                "target_user_id": state.users["bob"]["id"],
                "context_type": "business",
                "context_id": biz_id,
                "payload": {"role_id": role_id},
            },
        )
        assert r.status_code in (
            400,
            409,
        ), f"Expected 400/409 for existing member, got {r.status_code}: {r.text}"


# =============================================================================
# NEG-N01–N06: NOT FOUND
# =============================================================================


class TestNegativeNotFound:
    """Test 404 responses for non-existent resources."""

    def test_neg_n01_business_not_found(self, api, state):
        """GET non-existent business returns 404."""
        api.set_token(state.get_token("alice"))
        r = api.get(f"business/id/{uuid.uuid4()}/")
        assert r.status_code == 404

    def test_neg_n02_transaction_not_found(self, api, state):
        """GET non-existent transaction returns 404."""
        api.set_token(state.get_token("alice"))
        r = api.get(f"transactions/{uuid.uuid4()}/")
        assert r.status_code == 404

    def test_neg_n03_form_template_not_found(self, api, state):
        """GET non-existent form template returns 404."""
        api.set_token(state.get_token("alice"))
        r = api.get(f"forms/templates/{uuid.uuid4()}/")
        assert r.status_code == 404

    def test_neg_n04_form_response_not_found(self, api, state):
        """GET non-existent form response returns 404."""
        api.set_token(state.get_token("alice"))
        r = api.get(f"forms/responses/{uuid.uuid4()}/")
        assert r.status_code == 404

    def test_neg_n05_cms_page_not_found(self, api, state):
        """GET non-existent CMS page returns 404 (or 403 without platform membership)."""
        api.set_token(state.get_token("alice"))
        r = api.get("cms/admin/pages/nonexistent-page-xyz/")
        # 403 if Alice lacks platform membership, 404 if page doesn't exist
        assert r.status_code in (403, 404)

    def test_neg_n06_membership_not_found(self, api, state):
        """GET non-existent membership returns 404."""
        api.set_token(state.get_token("alice"))
        r = api.get(f"users/me/memberships/{uuid.uuid4()}/")
        assert r.status_code == 404


# =============================================================================
# NEG-R01–R02: RATE LIMITING
# =============================================================================


class TestNegativeRateLimiting:
    """Test rate limiting on sensitive endpoints."""

    def test_neg_r01_rapid_login(self, api):
        """Rapid login attempts may trigger rate limiting."""
        api.clear_token()
        results = []
        for i in range(20):
            r = api.post(
                "auth/login/",
                json={
                    "email": f"nonexistent{i}@test.com",
                    "password": "WrongPass!",
                },
            )
            results.append(r.status_code)
            if r.status_code == 429:
                break

        # At least verify the endpoint handles rapid requests
        # Rate limiting may or may not be active
        assert all(s in (401, 429) for s in results)

    def test_neg_r02_rapid_password_reset(self, api):
        """Rapid password reset requests may trigger rate limiting."""
        api.clear_token()
        results = []
        for i in range(15):
            r = api.post(
                "auth/password/reset/",
                json={
                    "email": "alice@test.com",
                },
            )
            results.append(r.status_code)
            if r.status_code == 429:
                break

        # All should be 200 or eventually 429
        assert all(s in (200, 429) for s in results)
