"""
AWS SES Email Backend
=====================
Send emails via Amazon Simple Email Service.
"""

import boto3
from botocore.exceptions import ClientError
from django.conf import settings

from apps.core.exceptions import ServiceUnavailable
from apps.core.observability import get_logger
from apps.email.services.backends.base import BaseEmailBackend

logger = get_logger(__name__)


class SESBackend(BaseEmailBackend):
    """
    AWS SES email backend.

    Requires settings:
        - AWS_ACCESS_KEY_ID
        - AWS_SECRET_ACCESS_KEY
        - AWS_SES_REGION_NAME (default: 'us-east-1')
        - AWS_SES_CONFIGURATION_SET (optional, for tracking)

    Note:
        SES must be configured with verified domain/email addresses.
        In sandbox mode, recipient addresses must also be verified.
    """

    def __init__(self):
        """Initialize SES client."""
        self.client = boto3.client(
            "ses",
            region_name=getattr(settings, "AWS_SES_REGION_NAME", "us-east-1"),
            aws_access_key_id=getattr(settings, "AWS_ACCESS_KEY_ID", None),
            aws_secret_access_key=getattr(settings, "AWS_SECRET_ACCESS_KEY", None),
        )
        self.configuration_set = getattr(settings, "AWS_SES_CONFIGURATION_SET", None)

    def send(
        self,
        *,
        to_email: str,
        from_email: str,
        subject: str,
        html_body: str,
        text_body: str = "",
        reply_to: str = "",
    ) -> str:
        """
        Send email via SES.

        Args:
            to_email: Recipient email address
            from_email: Sender email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content
            reply_to: Reply-to address

        Returns:
            SES Message ID

        Raises:
            ServiceUnavailable: If SES send fails
        """
        try:
            message = {
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {"Html": {"Data": html_body, "Charset": "UTF-8"}},
            }

            if text_body:
                message["Body"]["Text"] = {"Data": text_body, "Charset": "UTF-8"}

            params = {
                "Source": from_email,
                "Destination": {"ToAddresses": [to_email]},
                "Message": message,
            }

            if reply_to:
                params["ReplyToAddresses"] = [reply_to]

            if self.configuration_set:
                params["ConfigurationSetName"] = self.configuration_set

            response = self.client.send_email(**params)
            message_id = response["MessageId"]

            logger.info(
                "email.ses.sent",
                message_id=message_id,
                to_email_hash=hash(to_email),
            )

            return message_id

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            logger.error(
                "email.ses.failed",
                error_code=error_code,
                error_message=error_message,
                to_email_hash=hash(to_email),
            )

            raise ServiceUnavailable(
                message=f"Failed to send email via SES: {error_message}",
                service="AWS SES",
            ) from e

        except Exception as e:
            logger.error("email.ses.unexpected_error", error=str(e))
            raise ServiceUnavailable(
                message=f"Failed to send email via SES: {str(e)}", service="AWS SES"
            ) from e
