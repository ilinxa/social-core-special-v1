"""
Base Email Backend
==================
Abstract base class for email backends.
"""

from abc import ABC, abstractmethod


class BaseEmailBackend(ABC):
    """
    Abstract base class for email backends.

    All backends must implement the send() method.
    """

    @abstractmethod
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
        Send an email.

        Args:
            to_email: Recipient email address
            from_email: Sender email address
            subject: Email subject
            html_body: HTML content
            text_body: Plain text content
            reply_to: Reply-to address

        Returns:
            Message ID from the provider

        Raises:
            ServiceUnavailable: If sending fails
        """
        pass
