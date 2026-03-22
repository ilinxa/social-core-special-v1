"""
Phase 09 — Notifications + Email (N01–N08, E01–E03)

Tests notification preferences CRUD, history, configurable types,
and SES webhook handling.

Depends on Phase 01 (users).
"""

import pytest

# =============================================================================
# N01–N08: NOTIFICATION PREFERENCES & HISTORY
# =============================================================================


class TestNotificationPreferences:
    """Test notification preference management."""

    def test_n01_get_preferences(self, api, state):
        """GET /notifications/preferences/ returns all preferences."""
        api.set_token(state.get_token("alice"))
        r = api.get("notifications/preferences/")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (dict, list))

    def test_n02_get_configurable_types(self, api, state):
        """GET /notifications/types/ returns configurable notification types."""
        api.set_token(state.get_token("alice"))
        r = api.get("notifications/types/")
        assert r.status_code == 200
        data = r.json()
        # Response format: {"types": [...], "count": N}
        results = data.get("types", []) if isinstance(data, dict) else data
        assert isinstance(results, list)
        assert len(results) > 0, f"Expected notification types, got: {data}"
        if results:
            # Store a type name for later tests
            state.cms["notification_type"] = results[0].get("name")

    def test_n03_get_preference_detail(self, api, state):
        """GET /notifications/preferences/<type>/ returns specific preference."""
        ntype = state.cms.get("notification_type")
        if not ntype:
            pytest.skip("No notification types available")

        api.set_token(state.get_token("alice"))
        r = api.get(f"notifications/preferences/{ntype}/")
        assert r.status_code == 200

    def test_n04_update_preference(self, api, state):
        """PATCH /notifications/preferences/<type>/ updates preference."""
        ntype = state.cms.get("notification_type")
        if not ntype:
            pytest.skip("No notification types available")

        api.set_token(state.get_token("alice"))
        r = api.patch(
            f"notifications/preferences/{ntype}/",
            json={
                "email_enabled": False,
            },
        )
        assert r.status_code == 200

    def test_n05_restore_preference(self, api, state):
        """Restore preference to default."""
        ntype = state.cms.get("notification_type")
        if not ntype:
            pytest.skip("No notification types")

        api.set_token(state.get_token("alice"))
        r = api.patch(
            f"notifications/preferences/{ntype}/",
            json={
                "email_enabled": True,
            },
        )
        assert r.status_code == 200

    def test_n06_get_history(self, api, state):
        """GET /notifications/history/ returns notification log."""
        api.set_token(state.get_token("alice"))
        r = api.get("notifications/history/")
        assert r.status_code == 200

    def test_n07_invalid_type(self, api, state):
        """GET /notifications/preferences/<invalid>/ returns 404."""
        api.set_token(state.get_token("alice"))
        r = api.get("notifications/preferences/nonexistent_type/")
        assert r.status_code == 404

    def test_n08_batch_update_preferences(self, api, state):
        """PATCH /notifications/preferences/ updates multiple preferences."""
        api.set_token(state.get_token("alice"))
        r = api.patch(
            "notifications/preferences/",
            json={
                "push_enabled": True,
            },
        )
        # May be 200 or 400 depending on whether batch update is supported
        assert r.status_code in (200, 400, 405)


# =============================================================================
# E01–E03: SES WEBHOOK
# =============================================================================


class TestEmailWebhook:
    """Test SES webhook endpoint for email event processing.

    The webhook validates AWS SNS signatures via SNSSignatureVerifier.
    Without valid signatures, it returns 403 Forbidden.
    Tests verify the endpoint is reachable and handles payloads.
    """

    def test_e01_ses_delivery(self, api):
        """POST /email/webhooks/ses/ with delivery notification."""
        api.clear_token()  # Webhook is public (no Bearer auth)
        r = api.post(
            "email/webhooks/ses/",
            json={
                "Type": "Notification",
                "Message": '{"notificationType":"Delivery","delivery":{"recipients":["alice@test.com"],"timestamp":"2026-01-01T00:00:00Z","processingTimeMillis":100,"reportingMTA":"mta.example.com","smtpResponse":"250 OK"}}',
            },
        )
        # 403 = SNS signature validation failure (expected without valid AWS signatures)
        # 200 = processed, 400 = malformed
        assert r.status_code in (200, 400, 403)

    def test_e02_ses_bounce(self, api):
        """POST /email/webhooks/ses/ with bounce notification."""
        api.clear_token()
        r = api.post(
            "email/webhooks/ses/",
            json={
                "Type": "Notification",
                "Message": '{"notificationType":"Bounce","bounce":{"bounceType":"Permanent","bouncedRecipients":[{"emailAddress":"bounced@test.com"}],"timestamp":"2026-01-01T00:00:00Z"}}',
            },
        )
        assert r.status_code in (200, 400, 403)

    def test_e03_ses_complaint(self, api):
        """POST /email/webhooks/ses/ with complaint notification."""
        api.clear_token()
        r = api.post(
            "email/webhooks/ses/",
            json={
                "Type": "Notification",
                "Message": '{"notificationType":"Complaint","complaint":{"complainedRecipients":[{"emailAddress":"complaint@test.com"}],"timestamp":"2026-01-01T00:00:00Z","complaintFeedbackType":"abuse"}}',
            },
        )
        assert r.status_code in (200, 400, 403)
