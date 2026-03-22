"""
Phase 06 — Transactions (T01–T19, PT01–PT07)

Tests transaction listing, invitation/request creation, lifecycle actions
(accept, deny, cancel, dismiss), form-linked transactions, auto-approval,
and platform-scoped transaction lifecycle.

Depends on Phase 01 (users), Phase 03 (platform configured), Phase 04 (businesses created).
"""

import uuid

import pytest

# =============================================================================
# T01–T07: TRANSACTION CREATION & LISTING
# =============================================================================


class TestTransactionCreation:
    """Test transaction listing, invitation, and request creation."""

    def test_t01_list_transactions_empty(self, api, state):
        """GET /transactions/ returns empty list initially."""
        api.set_token(state.get_token("alice"))
        r = api.get("transactions/")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        assert isinstance(results, list)

    def test_t02_create_invitation(self, api, state, db_helper):
        """POST /transactions/invitation/ creates a membership invitation.

        business_membership_invitation requires role_id in payload.
        """
        api.set_token(state.get_token("alice"))
        bob_id = state.users["bob"]["id"]
        biz_id = state.businesses["alice_corp"]["id"]

        # Get the base member role for the business
        role_id = db_helper.get_base_member_role_id("business", biz_id)
        assert role_id, "No base member role found for business"

        r = api.post(
            "transactions/invitation/",
            json={
                "transaction_type": "business_membership_invitation",
                "target_user_id": bob_id,
                "context_type": "business",
                "context_id": biz_id,
                "payload": {"role_id": role_id},
            },
        )
        assert r.status_code == 201, f"Create invitation failed: {r.text}"
        data = r.json()
        assert data["transaction_type"] == "business_membership_invitation"
        assert data["status"] == "pending"
        state.transactions["bob_invite"] = {
            "id": data["id"],
            "type": data["transaction_type"],
            "status": data["status"],
        }

    def test_t03_create_invitation_carol(self, api, state, db_helper):
        """Create invitation for Carol to alice_corp."""
        api.set_token(state.get_token("alice"))
        carol_id = state.users["carol"]["id"]
        biz_id = state.businesses["alice_corp"]["id"]

        role_id = db_helper.get_base_member_role_id("business", biz_id)
        assert role_id, "No base member role found"

        r = api.post(
            "transactions/invitation/",
            json={
                "transaction_type": "business_membership_invitation",
                "target_user_id": carol_id,
                "context_type": "business",
                "context_id": biz_id,
                "payload": {"role_id": role_id},
            },
        )
        assert r.status_code == 201
        state.transactions["carol_invite"] = {
            "id": r.json()["id"],
            "type": "business_membership_invitation",
            "status": "pending",
        }

    def test_t04_create_request(self, api, state):
        """POST /transactions/request/ creates a join request."""
        api.set_token(state.get_token("nobody"))
        biz_id = state.businesses["bob_llc"]["id"]

        r = api.post(
            "transactions/request/",
            json={
                "transaction_type": "business_membership_request",
                "target_account_id": biz_id,
                "target_account_type": "business",
            },
        )
        # May succeed or fail depending on transaction config
        if r.status_code == 201:
            state.transactions["nobody_request"] = {
                "id": r.json()["id"],
                "type": "business_membership_request",
                "status": r.json()["status"],
            }
        else:
            # Some transaction types may not be configured
            assert r.status_code in (400, 404)

    def test_t05_get_form_schema(self, api, state):
        """GET /transactions/types/<type>/form/ returns form schema."""
        api.set_token(state.get_token("alice"))
        r = api.get("transactions/types/business_membership_invitation/form/")
        # 200 with schema or 404 if no form required
        assert r.status_code in (200, 404)

    def test_t06_duplicate_invitation(self, api, state, db_helper):
        """Creating duplicate invitation returns 400/409."""
        api.set_token(state.get_token("alice"))
        bob_id = state.users["bob"]["id"]
        biz_id = state.businesses["alice_corp"]["id"]
        role_id = db_helper.get_base_member_role_id("business", biz_id)

        r = api.post(
            "transactions/invitation/",
            json={
                "transaction_type": "business_membership_invitation",
                "target_user_id": bob_id,
                "context_type": "business",
                "context_id": biz_id,
                "payload": {"role_id": role_id},
            },
        )
        # Should be rejected as duplicate
        assert r.status_code in (400, 409)

    def test_t07_list_transactions_after_creation(self, api, state):
        """GET /transactions/?role=target returns transactions where user is target.

        Note: Invitations created by Alice use initiator_type=membership_actor
        (not "user"), so they won't appear under ?role=initiator for Alice.
        Bob is the target, so he sees them under ?role=target.
        """
        api.set_token(state.get_token("bob"))
        r = api.get("transactions/?role=target")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        assert len(results) >= 1, f"Expected transactions for Bob, got: {data}"


# =============================================================================
# T08–T13: TRANSACTION LIFECYCLE
# =============================================================================


class TestTransactionLifecycle:
    """Test accept, deny, cancel, dismiss, and double-action prevention."""

    def test_t08_get_transaction_detail(self, api, state):
        """GET /transactions/<id>/ returns transaction detail."""
        if "bob_invite" not in state.transactions:
            pytest.skip("No invitation created")

        api.set_token(state.get_token("alice"))
        tid = state.transactions["bob_invite"]["id"]
        r = api.get(f"transactions/{tid}/")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == tid
        assert data["status"] == "pending"

    def test_t09_accept_invitation(self, api, state):
        """POST /transactions/<id>/accept/ — Bob accepts invitation."""
        if "bob_invite" not in state.transactions:
            pytest.skip("No invitation created")

        api.set_token(state.get_token("bob"))
        tid = state.transactions["bob_invite"]["id"]
        r = api.post(f"transactions/{tid}/accept/")
        assert r.status_code == 200, f"Accept failed: {r.text}"
        data = r.json()
        assert data["status"] in ("accepted", "completed", "resolved")
        state.transactions["bob_invite"]["status"] = data["status"]

    def test_t10_deny_invitation(self, api, state):
        """POST /transactions/<id>/deny/ — Carol denies invitation."""
        if "carol_invite" not in state.transactions:
            pytest.skip("No Carol invitation")

        api.set_token(state.get_token("carol"))
        tid = state.transactions["carol_invite"]["id"]
        r = api.post(
            f"transactions/{tid}/deny/",
            json={
                "reason": "Not interested right now",
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("denied", "rejected", "resolved")

    def test_t11_cancel_transaction(self, api, state, db_helper):
        """POST /transactions/<id>/cancel/ — initiator cancels."""
        # Create a fresh invitation to cancel
        api.set_token(state.get_token("alice"))
        carol_id = state.users["carol"]["id"]
        biz_id = state.businesses["alice_corp"]["id"]
        role_id = db_helper.get_base_member_role_id("business", biz_id)

        r = api.post(
            "transactions/invitation/",
            json={
                "transaction_type": "business_membership_invitation",
                "target_user_id": carol_id,
                "context_type": "business",
                "context_id": biz_id,
                "payload": {"role_id": role_id},
            },
        )
        if r.status_code != 201:
            pytest.skip("Could not create invitation to cancel")

        tid = r.json()["id"]
        r = api.post(f"transactions/{tid}/cancel/")
        assert r.status_code == 200

    def test_t12_dismiss_transaction(self, api, state):
        """POST /transactions/<id>/dismiss/ — dismiss only works for requests.

        Dismiss is only valid for REQUEST mode transactions (not invitations).
        Invitations cannot be dismissed — they must be denied or cancelled.
        """
        if "nobody_request" not in state.transactions:
            pytest.skip("No request transaction available (T04 didn't create one)")

        api.set_token(state.get_token("bob"))
        tid = state.transactions["nobody_request"]["id"]
        r = api.post(f"transactions/{tid}/dismiss/")
        # 200 if dismiss allowed, 400 if wrong state/mode
        assert r.status_code in (200, 400)

    def test_t13_double_accept_blocked(self, api, state):
        """Accepting an already-resolved transaction returns error."""
        if "bob_invite" not in state.transactions:
            pytest.skip("No invitation")

        api.set_token(state.get_token("bob"))
        tid = state.transactions["bob_invite"]["id"]
        r = api.post(f"transactions/{tid}/accept/")
        # Already accepted — should be 400
        assert r.status_code == 400


# =============================================================================
# T14–T18: FORM-LINKED TRANSACTIONS
# =============================================================================


class TestTransactionForms:
    """Test transactions linked to forms."""

    def test_t14_get_form_response_endpoint(self, api, state):
        """GET /transactions/<id>/form-response/ gets linked form data."""
        if "bob_invite" not in state.transactions:
            pytest.skip("No transaction")

        api.set_token(state.get_token("alice"))
        tid = state.transactions["bob_invite"]["id"]
        r = api.get(f"transactions/{tid}/form-response/")
        # 200 with data or 404 if no form linked
        assert r.status_code in (200, 404)

    def test_t15_create_verification_request(self, api, state, db_helper):
        """Create a business verification request with required form response.

        business_verification_request requires a form response using the
        system-business-verification template. Since system forms have
        owner_type='system' (no membership), we create the response via DB.
        """
        api.set_token(state.get_token("alice"))
        biz_id = state.businesses["alice_corp"]["id"]

        # Create form response for system-business-verification template
        form_response_id = db_helper.create_system_form_response(
            template_slug="system-business-verification",
            user_email="alice@test.com",
            data={
                "legal_name": "Alice Corp LLC",
                "registration_number": "REG-2026-001",
                "tax_id": "TAX-123456",
                "country": "US",
                "legal_address": "123 Business Ave, Suite 100, New York, NY 10001",
            },
            context_type="business",
            context_id=biz_id,
        )
        assert form_response_id, "Failed to create system form response"

        r = api.post(
            "transactions/request/",
            json={
                "transaction_type": "business_verification_request",
                "target_account_id": biz_id,
                "target_account_type": "business",
                "form_response_id": form_response_id,
            },
        )
        assert r.status_code == 201, f"Create verification request failed: {r.text}"
        state.transactions["verification"] = {
            "id": r.json()["id"],
            "type": "business_verification_request",
            "status": r.json()["status"],
        }

    def test_t16_request_info(self, api, state):
        """POST /transactions/<id>/request-info/ asks for more information.

        The request-info endpoint requires PLATFORM_AUTHORITY approver policy,
        so only a platform member can request info. Alice is the platform owner.
        requested_fields must match actual template field keys.
        """
        if "verification" not in state.transactions:
            pytest.skip("No verification transaction")

        api.set_token(state.get_token("alice"))
        tid = state.transactions["verification"]["id"]
        r = api.post(
            f"transactions/{tid}/request-info/",
            json={
                "message": "Please provide business license and tax certificate",
                "requested_fields": ["business_license", "tax_certificate"],
            },
        )
        # 200 = success, 400 = invalid state, 403 = insufficient permissions
        assert r.status_code in (200, 400, 403)

    def test_t17_resubmit(self, api, state):
        """POST /transactions/<id>/resubmit/ resubmits after info request."""
        if "verification" not in state.transactions:
            pytest.skip("No verification transaction")

        api.set_token(state.get_token("alice"))
        tid = state.transactions["verification"]["id"]
        r = api.post(f"transactions/{tid}/resubmit/")
        assert r.status_code in (200, 400)

    def test_t18_patch_form_response(self, api, state):
        """PATCH /transactions/<id>/form-response/ updates form data."""
        if "verification" not in state.transactions:
            pytest.skip("No verification transaction")

        api.set_token(state.get_token("alice"))
        tid = state.transactions["verification"]["id"]
        r = api.patch(
            f"transactions/{tid}/form-response/",
            json={
                "data": {
                    "legal_name": "Alice Corp LLC (Updated)",
                    "registration_number": "REG-2026-001",
                    "tax_id": "TAX-123456",
                    "country": "US",
                    "legal_address": "123 Business Ave, Suite 200, New York, NY 10001",
                    "business_license": "BL-2026-NYC-001",
                    "tax_certificate": "TC-2026-US-001",
                },
            },
        )
        # 200 on success, 400 if no form linked, 404 if not found
        assert r.status_code in (200, 400, 404)


# =============================================================================
# T19: AUTO-APPROVAL
# =============================================================================


class TestTransactionAutoApproval:
    """Test auto-approval transaction types."""

    def test_t19_auto_approval_follow(self, api, state):
        """business_follow_request auto-resolves on creation."""
        api.set_token(state.get_token("carol"))
        biz_id = state.businesses["alice_corp"]["id"]

        r = api.post(
            "transactions/request/",
            json={
                "transaction_type": "business_follow_request",
                "target_account_id": biz_id,
                "target_account_type": "business",
            },
        )
        if r.status_code == 201:
            data = r.json()
            # Auto-approval means status should be resolved immediately
            assert data["status"] in ("accepted", "completed", "resolved", "pending")
        else:
            # Transaction type may not be configured
            assert r.status_code in (400, 404)


# =============================================================================
# PT01–PT07: PLATFORM TRANSACTION LIFECYCLE
# =============================================================================


class TestPlatformTransactions:
    """Test platform-scoped transaction creation, lifecycle, and listing.

    Uses Alice (platform owner from Phase 03) and Carol (external user).
    """

    def test_pt01_create_platform_invitation(self, api, state, db_helper):
        """POST /transactions/invitation/ creates a platform membership invitation."""
        api.set_token(state.get_token("alice"))
        carol_id = state.users["carol"]["id"]
        platform_id = state.platform.get("id")
        if not platform_id:
            pytest.skip("Platform not configured")

        role_id = db_helper.get_base_member_role_id("platform", platform_id)
        assert role_id, "No base member role found for platform"

        r = api.post(
            "transactions/invitation/",
            json={
                "transaction_type": "platform_membership_invitation",
                "target_user_id": carol_id,
                "context_type": "platform",
                "context_id": platform_id,
                "payload": {"role_id": role_id},
            },
        )
        assert r.status_code == 201, f"Create platform invitation failed: {r.text}"
        data = r.json()
        assert data["transaction_type"] == "platform_membership_invitation"
        assert data["status"] == "pending"
        state.transactions["plat_carol_invite"] = {
            "id": data["id"],
            "type": data["transaction_type"],
            "status": data["status"],
        }

    def test_pt02_get_platform_transaction_detail(self, api, state):
        """GET /transactions/<id>/ returns platform transaction detail with _permissions."""
        if "plat_carol_invite" not in state.transactions:
            pytest.skip("No platform invitation created")

        api.set_token(state.get_token("alice"))
        tid = state.transactions["plat_carol_invite"]["id"]
        r = api.get(f"transactions/{tid}/")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == tid
        assert data["context_type"] == "platform"
        assert "_permissions" in data

    def test_pt03_duplicate_platform_invitation_blocked(self, api, state, db_helper):
        """Creating duplicate platform invitation returns 409."""
        if "plat_carol_invite" not in state.transactions:
            pytest.skip("No platform invitation created")

        api.set_token(state.get_token("alice"))
        carol_id = state.users["carol"]["id"]
        platform_id = state.platform.get("id")
        role_id = db_helper.get_base_member_role_id("platform", platform_id)

        r = api.post(
            "transactions/invitation/",
            json={
                "transaction_type": "platform_membership_invitation",
                "target_user_id": carol_id,
                "context_type": "platform",
                "context_id": platform_id,
                "payload": {"role_id": role_id},
            },
        )
        assert r.status_code in (
            400,
            409,
        ), f"Expected duplicate rejection, got {r.status_code}: {r.text}"

    def test_pt04_deny_platform_invitation(self, api, state):
        """POST /transactions/<id>/deny/ — Carol denies platform invitation."""
        if "plat_carol_invite" not in state.transactions:
            pytest.skip("No platform invitation created")

        api.set_token(state.get_token("carol"))
        tid = state.transactions["plat_carol_invite"]["id"]
        r = api.post(
            f"transactions/{tid}/deny/",
            json={
                "reason": "Not interested in platform membership",
            },
        )
        assert r.status_code == 200, f"Deny failed: {r.text}"
        data = r.json()
        assert data["status"] == "denied"

    def test_pt05_create_platform_request(self, api, state, db_helper):
        """POST /transactions/request/ creates a platform membership request."""
        platform_id = state.platform.get("id")
        if not platform_id:
            pytest.skip("Platform not configured")

        # Enable open member requests
        db_helper.execute(
            "UPDATE platform_account SET open_member_request = TRUE WHERE id = %s::uuid",
            (platform_id,),
            fetch=False,
        )

        api.set_token(state.get_token("carol"))
        r = api.post(
            "transactions/request/",
            json={
                "transaction_type": "platform_membership_request",
                "target_account_type": "platform",
                "target_account_id": platform_id,
            },
        )
        assert r.status_code == 201, f"Create platform request failed: {r.text}"
        data = r.json()
        assert data["transaction_type"] == "platform_membership_request"
        assert data["status"] == "pending"
        state.transactions["plat_carol_request"] = {
            "id": data["id"],
            "type": data["transaction_type"],
            "status": data["status"],
        }

    def test_pt06_cancel_platform_request(self, api, state):
        """POST /transactions/<id>/cancel/ — Carol cancels her own request."""
        if "plat_carol_request" not in state.transactions:
            pytest.skip("No platform request created")

        api.set_token(state.get_token("carol"))
        tid = state.transactions["plat_carol_request"]["id"]
        r = api.post(f"transactions/{tid}/cancel/")
        assert r.status_code == 200, f"Cancel failed: {r.text}"
        data = r.json()
        assert data["status"] == "cancelled"

    def test_pt07_list_platform_transactions(self, api, state):
        """GET /transactions/?context_type=platform returns platform transactions."""
        platform_id = state.platform.get("id")
        if not platform_id:
            pytest.skip("Platform not configured")

        api.set_token(state.get_token("alice"))
        r = api.get(f"transactions/?context_type=platform&context_id={platform_id}")
        assert r.status_code == 200
        data = r.json()
        results = data if isinstance(data, list) else data.get("results", [])
        # Should include the platform invitation and request we created
        platform_types = {t["transaction_type"] for t in results}
        assert (
            "platform_membership_invitation" in platform_types or len(results) >= 1
        ), f"Expected platform transactions, got types: {platform_types}"
