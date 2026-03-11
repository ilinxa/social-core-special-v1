"""
Console Email Backend
=====================
Print emails to console for development/testing.
"""

import uuid

from apps.core.observability import get_logger
from apps.email.services.backends.base import BaseEmailBackend

logger = get_logger(__name__)


class ConsoleBackend(BaseEmailBackend):
    """
    Console email backend for development.

    Prints email content to console instead of sending.
    Useful for local development and testing.
    """

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
        Print email to console.

        Args:
            to_email: Recipient email address
            from_email: Sender email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content
            reply_to: Reply-to address

        Returns:
            Generated Message ID
        """
        message_id = f"console-{uuid.uuid4()}"

        separator = "=" * 60
        print(f"\n{separator}")
        print("EMAIL SENT (Console Backend)")
        print(separator)
        print(f"Message-ID: {message_id}")
        print(f"From: {from_email}")
        print(f"To: {to_email}")
        if reply_to:
            print(f"Reply-To: {reply_to}")
        print(f"Subject: {subject}")
        print(separator)
        print("TEXT BODY:")
        print(text_body or "(auto-generated from HTML)")
        print(separator)
        print("HTML BODY:")
        print(html_body[:500] + "..." if len(html_body) > 500 else html_body)
        print(f"{separator}\n")

        logger.info(
            "email.console.sent",
            message_id=message_id,
            to_email=to_email,
            subject=subject,
        )

        return message_id
