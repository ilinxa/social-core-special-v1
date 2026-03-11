"""
Email Webhooks
==============
Handle AWS SES notifications via SNS.

Notification types:
    - Delivery: Email successfully delivered to recipient's mail server
    - Bounce: Email bounced (permanent or transient)
    - Complaint: Recipient marked email as spam

SECURITY: All SNS messages are signature-verified.
"""

import json

import requests
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from apps.core.observability import get_logger
from apps.email.models import EmailLog
from apps.email.services.sns_verifier import SNSSignatureVerifier

logger = get_logger(__name__)


# Schema for documentation (webhook is a Django function view, not DRF)
SES_WEBHOOK_SCHEMA = extend_schema(
    summary="AWS SES Webhook",
    description="""
    Receive AWS SES notifications via SNS.

    **This endpoint is for AWS SNS, not for direct API calls.**

    Configure this URL in AWS SES/SNS as the notification destination
    for delivery, bounce, and complaint events.

    **Message Types:**
    - `SubscriptionConfirmation`: Initial SNS topic subscription (auto-confirmed)
    - `Notification`: Email delivery/bounce/complaint events

    **Event Types (in Notification):**
    - `Delivery`: Email successfully delivered to recipient's mail server
    - `Bounce`: Email bounced (permanent = invalid address, transient = temp failure)
    - `Complaint`: Recipient marked email as spam

    **Security:**
    - All messages are SNS signature-verified
    - Invalid signatures return 403 Forbidden
    - Returns 200 OK even on processing errors to prevent SNS retry flood
    """,
    tags=["Webhooks (Internal)"],
    request=OpenApiTypes.OBJECT,
    responses={
        200: OpenApiTypes.STR,
        400: OpenApiTypes.STR,
        403: OpenApiTypes.STR,
    },
    exclude=True,  # Hide from public API docs (internal webhook)
)


@csrf_exempt
@require_POST
def ses_webhook(request):
    """
    Handle AWS SES notifications via SNS.

    This endpoint receives:
    1. SubscriptionConfirmation - Initial setup (auto-confirmed)
    2. Notification - Delivery/Bounce/Complaint events

    Security:
        - All messages are SNS signature-verified
        - Returns 200 even on errors to prevent SNS retry flood
    """
    try:
        # Parse request body
        try:
            body = json.loads(request.body)
        except json.JSONDecodeError:
            logger.warning("email.webhook.invalid_json")
            return HttpResponseBadRequest("Invalid JSON")

        # Verify SNS signature (CRITICAL)
        try:
            SNSSignatureVerifier.verify(body)
        except ValueError as e:
            logger.warning("email.webhook.signature_failed", error=str(e))
            return HttpResponseForbidden("Invalid signature")

        message_type = body.get('Type', '')

        # Handle subscription confirmation
        if message_type == 'SubscriptionConfirmation':
            return _handle_subscription_confirmation(body)

        # Handle notification
        if message_type == 'Notification':
            return _handle_notification(body)

        # Unknown message type
        logger.warning("email.webhook.unknown_type", message_type=message_type)
        return HttpResponse('OK')

    except Exception as e:
        # Log error but return 200 to prevent SNS retry flood
        logger.exception("email.webhook.error", error=str(e))
        return HttpResponse('OK')


def _handle_subscription_confirmation(body: dict) -> HttpResponse:
    """
    Handle SNS subscription confirmation.

    Auto-confirms by visiting the SubscribeURL.
    This is required when setting up SES event destinations.
    """
    subscribe_url = body.get('SubscribeURL')
    if subscribe_url:
        try:
            response = requests.get(subscribe_url, timeout=10)
            response.raise_for_status()
            logger.info("email.webhook.subscription_confirmed")
        except Exception as e:
            logger.error("email.webhook.subscription_failed", error=str(e))

    return HttpResponse('OK')


def _handle_notification(body: dict) -> HttpResponse:
    """
    Handle SES notification (Delivery/Bounce/Complaint).

    Parses the nested message and routes to appropriate handler.
    """
    try:
        message = json.loads(body.get('Message', '{}'))
    except json.JSONDecodeError:
        logger.warning("email.webhook.notification_invalid_json")
        return HttpResponse('OK')

    notification_type = message.get('notificationType', '')

    if notification_type == 'Delivery':
        _handle_delivery(message)
    elif notification_type == 'Bounce':
        _handle_bounce(message)
    elif notification_type == 'Complaint':
        _handle_complaint(message)
    else:
        logger.warning("email.webhook.unknown_notification_type", notification_type=notification_type)

    return HttpResponse('OK')


def _handle_delivery(message: dict) -> None:
    """
    Handle delivery notification.

    Updates EmailLog status to 'delivered'.
    """
    mail = message.get('mail', {})
    message_id = mail.get('messageId')

    if not message_id:
        logger.warning("email.webhook.delivery_missing_id")
        return

    delivery = message.get('delivery', {})
    timestamp = delivery.get('timestamp')

    updated = EmailLog.objects.filter(message_id=message_id).update(
        status=EmailLog.Status.DELIVERED,
        delivered_at=timezone.now()
    )

    if updated:
        logger.info(
            "email.delivered",
            message_id=message_id,
            recipients=delivery.get('recipients', []),
        )
    else:
        logger.warning("email.webhook.delivery_not_found", message_id=message_id)


def _handle_bounce(message: dict) -> None:
    """
    Handle bounce notification.

    Updates EmailLog status to 'bounced' with bounce details.

    Bounce types:
        - Permanent: Hard bounce (invalid address, domain doesn't exist)
        - Transient: Soft bounce (mailbox full, server unavailable)
    """
    mail = message.get('mail', {})
    message_id = mail.get('messageId')

    if not message_id:
        logger.warning("email.webhook.bounce_missing_id")
        return

    bounce = message.get('bounce', {})
    bounce_type = bounce.get('bounceType', '')
    bounce_subtype = bounce.get('bounceSubType', '')

    updated = EmailLog.objects.filter(message_id=message_id).update(
        status=EmailLog.Status.BOUNCED,
        bounced_at=timezone.now(),
        bounce_type=bounce_type,
        bounce_subtype=bounce_subtype
    )

    if updated:
        logger.warning(
            "email.bounced",
            message_id=message_id,
            bounce_type=bounce_type,
            bounce_subtype=bounce_subtype,
            bounced_recipients=[
                r.get('emailAddress') for r in bounce.get('bouncedRecipients', [])
            ],
        )
    else:
        logger.warning("email.webhook.bounce_not_found", message_id=message_id)


def _handle_complaint(message: dict) -> None:
    """
    Handle complaint notification.

    Updates EmailLog status to 'complained'.
    Complaints indicate recipient marked email as spam.

    Important: High complaint rates can damage sender reputation
    and lead to SES sending restrictions.
    """
    mail = message.get('mail', {})
    message_id = mail.get('messageId')

    if not message_id:
        logger.warning("email.webhook.complaint_missing_id")
        return

    complaint = message.get('complaint', {})
    complaint_feedback_type = complaint.get('complaintFeedbackType', '')

    updated = EmailLog.objects.filter(message_id=message_id).update(
        status=EmailLog.Status.COMPLAINED,
        complained_at=timezone.now()
    )

    if updated:
        logger.warning(
            "email.complained",
            message_id=message_id,
            feedback_type=complaint_feedback_type,
            complained_recipients=[
                r.get('emailAddress') for r in complaint.get('complainedRecipients', [])
            ],
        )
    else:
        logger.warning("email.webhook.complaint_not_found", message_id=message_id)
