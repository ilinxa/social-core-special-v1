"""
SMTP Email Backend
==================
Send emails via standard SMTP server.
"""

import smtplib
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from django.conf import settings

from apps.core.exceptions import ServiceUnavailable
from apps.core.observability import get_logger
from apps.email.services.backends.base import BaseEmailBackend

logger = get_logger(__name__)


class SMTPBackend(BaseEmailBackend):
    """
    Standard SMTP email backend.

    Requires settings:
        - EMAIL_HOST: SMTP server hostname
        - EMAIL_PORT: SMTP port (default: 587)
        - EMAIL_HOST_USER: SMTP username
        - EMAIL_HOST_PASSWORD: SMTP password
        - EMAIL_USE_TLS: Use TLS (default: True)
        - EMAIL_USE_SSL: Use SSL (default: False)

    Note:
        - Use TLS for port 587 (STARTTLS)
        - Use SSL for port 465 (implicit SSL)
        - Don't use both TLS and SSL
    """

    def __init__(self):
        """Initialize SMTP settings."""
        self.host = getattr(settings, 'EMAIL_HOST', 'localhost')
        self.port = getattr(settings, 'EMAIL_PORT', 587)
        self.username = getattr(settings, 'EMAIL_HOST_USER', '')
        self.password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        self.use_tls = getattr(settings, 'EMAIL_USE_TLS', True)
        self.use_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
        self.timeout = getattr(settings, 'EMAIL_TIMEOUT', 30)

    def send(
        self,
        *,
        to_email: str,
        from_email: str,
        subject: str,
        html_body: str,
        text_body: str = '',
        reply_to: str = ''
    ) -> str:
        """
        Send email via SMTP.

        Args:
            to_email: Recipient email address
            from_email: Sender email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content
            reply_to: Reply-to address

        Returns:
            Generated Message ID

        Raises:
            ServiceUnavailable: If SMTP send fails
        """
        # Generate message ID
        message_id = f"{uuid.uuid4()}@{self.host}"

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            msg['Message-ID'] = f"<{message_id}>"

            if reply_to:
                msg['Reply-To'] = reply_to

            # Attach text and HTML parts
            if text_body:
                msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            # Connect and send
            if self.use_ssl:
                server = smtplib.SMTP_SSL(
                    self.host,
                    self.port,
                    timeout=self.timeout
                )
            else:
                server = smtplib.SMTP(
                    self.host,
                    self.port,
                    timeout=self.timeout
                )

            try:
                if self.use_tls and not self.use_ssl:
                    server.starttls()

                if self.username and self.password:
                    server.login(self.username, self.password)

                server.sendmail(from_email, [to_email], msg.as_string())

                logger.info(
                    "email.smtp.sent",
                    message_id=message_id,
                    to_email_hash=hash(to_email),
                )

                return message_id

            finally:
                server.quit()

        except smtplib.SMTPAuthenticationError as e:
            logger.error("email.smtp.auth_failed", error=str(e))
            raise ServiceUnavailable(
                message="SMTP authentication failed",
                service='SMTP'
            )

        except smtplib.SMTPException as e:
            logger.error("email.smtp.error", error=str(e))
            raise ServiceUnavailable(
                message=f"Failed to send email via SMTP: {str(e)}",
                service='SMTP'
            )

        except Exception as e:
            logger.error("email.smtp.unexpected_error", error=str(e))
            raise ServiceUnavailable(
                message=f"Failed to send email: {str(e)}",
                service='SMTP'
            )
