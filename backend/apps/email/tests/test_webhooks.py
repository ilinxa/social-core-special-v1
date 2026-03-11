# apps/email/tests/test_webhooks.py
"""
Tests for SES webhook handler (apps.email.webhooks).

Covers:
    - JSON parsing (invalid JSON → 400)
    - HTTP method enforcement (GET → 405)
    - SNS signature verification (failure → 403)
    - SubscriptionConfirmation handling (auto-confirm via SubscribeURL)
    - Notification routing: Delivery, Bounce, Complaint
    - EmailLog updates for each notification type
    - Unknown message types and notification types → 200
    - Malformed notification Message JSON → 200
    - Unknown message_id still returns 200 (no crash)
"""

import json
from unittest.mock import patch, MagicMock

import pytest
from django.test import Client

from apps.email.models import EmailLog
from apps.email.tests.factories import SentEmailLogFactory


# =============================================================================
# HELPERS — SNS payload builders
# =============================================================================


def _sns_envelope(message_type, message_body=None, **overrides):
    """
    Build an SNS message envelope.

    Args:
        message_type: SNS Type field (Notification, SubscriptionConfirmation, etc.)
        message_body: For Notification type, the inner Message dict (will be JSON-serialized).
        **overrides: Override any top-level SNS envelope field.

    Returns:
        dict: Complete SNS message envelope.
    """
    payload = {
        "Type": message_type,
        "MessageId": "sns-msg-id-001",
        "TopicArn": "arn:aws:sns:us-east-1:123456789:ses-events",
        "Timestamp": "2024-01-15T12:00:00.000Z",
        "SignatureVersion": "1",
        "Signature": "dGVzdC1zaWduYXR1cmU=",
        "SigningCertURL": "https://sns.us-east-1.amazonaws.com/SimpleNotificationService-abc123.pem",
    }
    if message_type == "Notification" and message_body is not None:
        payload["Message"] = json.dumps(message_body)
        payload["Subject"] = "Amazon SES Email Event Notification"
    elif message_type == "SubscriptionConfirmation":
        payload["Message"] = "You have chosen to subscribe to the topic arn:aws:sns:..."
        payload["SubscribeURL"] = "https://sns.us-east-1.amazonaws.com/?Action=ConfirmSubscription&Token=abc123"
        payload["Token"] = "abc123"
    payload.update(overrides)
    return payload


def _delivery_notification(message_id):
    """Build SES Delivery notification inner message."""
    return {
        "notificationType": "Delivery",
        "mail": {
            "messageId": message_id,
            "source": "noreply@example.com",
            "destination": ["user@example.com"],
        },
        "delivery": {
            "timestamp": "2024-01-15T12:00:01.000Z",
            "recipients": ["user@example.com"],
            "processingTimeMillis": 450,
            "smtpResponse": "250 2.0.0 OK",
        },
    }


def _bounce_notification(message_id, bounce_type="Permanent", bounce_subtype="General"):
    """Build SES Bounce notification inner message."""
    return {
        "notificationType": "Bounce",
        "mail": {
            "messageId": message_id,
            "source": "noreply@example.com",
            "destination": ["bad@example.com"],
        },
        "bounce": {
            "bounceType": bounce_type,
            "bounceSubType": bounce_subtype,
            "bouncedRecipients": [
                {"emailAddress": "bad@example.com", "status": "5.1.1"},
            ],
            "timestamp": "2024-01-15T12:00:02.000Z",
        },
    }


def _complaint_notification(message_id, feedback_type="abuse"):
    """Build SES Complaint notification inner message."""
    return {
        "notificationType": "Complaint",
        "mail": {
            "messageId": message_id,
            "source": "noreply@example.com",
            "destination": ["complainer@example.com"],
        },
        "complaint": {
            "complaintFeedbackType": feedback_type,
            "complainedRecipients": [
                {"emailAddress": "complainer@example.com"},
            ],
            "timestamp": "2024-01-15T12:00:03.000Z",
        },
    }


# =============================================================================
# CONSTANTS
# =============================================================================

SES_WEBHOOK_URL = "/api/v1/email/webhooks/ses/"
VERIFIER_PATH = "apps.email.webhooks.SNSSignatureVerifier.verify"
REQUESTS_GET_PATH = "apps.email.webhooks.requests.get"


# =============================================================================
# TESTS
# =============================================================================


@pytest.mark.django_db
class TestSESWebhook:
    """Tests for the ses_webhook view and its notification handlers."""

    # -----------------------------------------------------------------
    # test_invalid_json_returns_400
    # -----------------------------------------------------------------

    def test_invalid_json_returns_400(self):
        """Sending non-JSON body returns 400 Bad Request."""
        client = Client()
        response = client.post(
            SES_WEBHOOK_URL,
            data="this is not json{{{",
            content_type="application/json",
        )

        assert response.status_code == 400

    # -----------------------------------------------------------------
    # test_invalid_method_get_returns_405
    # -----------------------------------------------------------------

    def test_invalid_method_get_returns_405(self):
        """GET request to the webhook endpoint returns 405 Method Not Allowed."""
        client = Client()
        response = client.get(SES_WEBHOOK_URL)

        assert response.status_code == 405

    # -----------------------------------------------------------------
    # test_signature_verification_failure_returns_400
    # -----------------------------------------------------------------

    def test_signature_verification_failure_returns_403(self):
        """When SNS signature verification fails, the endpoint returns 403 Forbidden."""
        client = Client()
        payload = _sns_envelope(
            "Notification",
            _delivery_notification("ses-msg-id-fake"),
        )

        with patch(VERIFIER_PATH, side_effect=ValueError("Invalid SNS signature")):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 403

    # -----------------------------------------------------------------
    # test_subscription_confirmation_visits_subscribe_url
    # -----------------------------------------------------------------

    def test_subscription_confirmation_visits_subscribe_url(self):
        """SubscriptionConfirmation type auto-confirms by visiting the SubscribeURL."""
        client = Client()
        payload = _sns_envelope("SubscriptionConfirmation")
        subscribe_url = payload["SubscribeURL"]

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        with patch(VERIFIER_PATH, return_value=True), \
             patch(REQUESTS_GET_PATH, return_value=mock_response) as mock_get:
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200
        mock_get.assert_called_once_with(subscribe_url, timeout=10)

    # -----------------------------------------------------------------
    # test_delivery_notification_updates_log_to_delivered
    # -----------------------------------------------------------------

    def test_delivery_notification_updates_log_to_delivered(self):
        """Delivery notification updates matching EmailLog to DELIVERED status."""
        email_log = SentEmailLogFactory(message_id="ses-delivery-001")
        payload = _sns_envelope("Notification", _delivery_notification("ses-delivery-001"))

        client = Client()
        with patch(VERIFIER_PATH, return_value=True):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200
        email_log.refresh_from_db()
        assert email_log.status == EmailLog.Status.DELIVERED
        assert email_log.delivered_at is not None

    # -----------------------------------------------------------------
    # test_delivery_notification_unknown_message_id_still_200
    # -----------------------------------------------------------------

    def test_delivery_notification_unknown_message_id_still_200(self):
        """Delivery notification with an unknown message_id still returns 200 (no crash)."""
        payload = _sns_envelope(
            "Notification",
            _delivery_notification("ses-unknown-id-999"),
        )

        client = Client()
        with patch(VERIFIER_PATH, return_value=True):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200
        # No EmailLog should have been updated
        assert EmailLog.objects.filter(message_id="ses-unknown-id-999").count() == 0

    # -----------------------------------------------------------------
    # test_bounce_notification_updates_log_to_bounced
    # -----------------------------------------------------------------

    def test_bounce_notification_updates_log_to_bounced(self):
        """Bounce notification updates matching EmailLog to BOUNCED status."""
        email_log = SentEmailLogFactory(message_id="ses-bounce-001")
        payload = _sns_envelope("Notification", _bounce_notification("ses-bounce-001"))

        client = Client()
        with patch(VERIFIER_PATH, return_value=True):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200
        email_log.refresh_from_db()
        assert email_log.status == EmailLog.Status.BOUNCED
        assert email_log.bounced_at is not None

    # -----------------------------------------------------------------
    # test_bounce_notification_stores_bounce_details
    # -----------------------------------------------------------------

    def test_bounce_notification_stores_bounce_details(self):
        """Bounce notification stores bounce_type and bounce_subtype on the EmailLog."""
        email_log = SentEmailLogFactory(message_id="ses-bounce-002")
        payload = _sns_envelope(
            "Notification",
            _bounce_notification("ses-bounce-002", bounce_type="Transient", bounce_subtype="MailboxFull"),
        )

        client = Client()
        with patch(VERIFIER_PATH, return_value=True):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200
        email_log.refresh_from_db()
        assert email_log.bounce_type == "Transient"
        assert email_log.bounce_subtype == "MailboxFull"

    # -----------------------------------------------------------------
    # test_complaint_notification_updates_log_to_complained
    # -----------------------------------------------------------------

    def test_complaint_notification_updates_log_to_complained(self):
        """Complaint notification updates matching EmailLog to COMPLAINED status."""
        email_log = SentEmailLogFactory(message_id="ses-complaint-001")
        payload = _sns_envelope("Notification", _complaint_notification("ses-complaint-001"))

        client = Client()
        with patch(VERIFIER_PATH, return_value=True):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200
        email_log.refresh_from_db()
        assert email_log.status == EmailLog.Status.COMPLAINED
        assert email_log.complained_at is not None

    # -----------------------------------------------------------------
    # test_unknown_notification_type_returns_200
    # -----------------------------------------------------------------

    def test_unknown_notification_type_returns_200(self):
        """Notification with an unknown notificationType still returns 200."""
        inner_message = {
            "notificationType": "SomeFutureType",
            "mail": {"messageId": "ses-future-001"},
        }
        payload = _sns_envelope("Notification", inner_message)

        client = Client()
        with patch(VERIFIER_PATH, return_value=True):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200

    # -----------------------------------------------------------------
    # test_unknown_message_type_returns_200
    # -----------------------------------------------------------------

    def test_unknown_message_type_returns_200(self):
        """SNS message with an unknown top-level Type still returns 200."""
        payload = _sns_envelope("UnsubscribeConfirmation")
        # Override Type to something truly unknown
        payload["Type"] = "UnknownSNSType"

        client = Client()
        with patch(VERIFIER_PATH, return_value=True):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200

    # -----------------------------------------------------------------
    # test_malformed_notification_returns_200
    # -----------------------------------------------------------------

    def test_malformed_notification_returns_200(self):
        """Notification with invalid JSON in the Message field still returns 200."""
        payload = _sns_envelope("Notification")
        payload["Message"] = "this is not valid json {{{"

        client = Client()
        with patch(VERIFIER_PATH, return_value=True):
            response = client.post(
                SES_WEBHOOK_URL,
                data=json.dumps(payload),
                content_type="application/json",
            )

        assert response.status_code == 200
