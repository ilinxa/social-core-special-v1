"""
Email Backends
==============
Pluggable email delivery backends.

Available backends:
    - SESBackend: AWS Simple Email Service
    - SMTPBackend: Standard SMTP (fallback)
    - ConsoleBackend: Print to console (development)

Usage:
    backend = get_email_backend()
    message_id = backend.send(
        to_email='user@example.com',
        from_email='noreply@app.com',
        subject='Hello',
        html_body='<h1>Hello</h1>',
        text_body='Hello'
    )
"""

from django.conf import settings

from apps.email.services.backends.base import BaseEmailBackend
from apps.email.services.backends.ses import SESBackend
from apps.email.services.backends.smtp import SMTPBackend
from apps.email.services.backends.console import ConsoleBackend


def get_email_backend() -> BaseEmailBackend:
    """
    Get the configured email backend.

    Configuration via EMAIL_BACKEND setting:
        - 'ses': AWS SES (production)
        - 'smtp': SMTP server
        - 'console': Print to console (development)

    Returns:
        Configured email backend instance
    """
    backend_name = getattr(settings, 'EMAIL_BACKEND_TYPE', 'console')

    backends = {
        'ses': SESBackend,
        'smtp': SMTPBackend,
        'console': ConsoleBackend,
    }

    backend_class = backends.get(backend_name, ConsoleBackend)
    return backend_class()


__all__ = [
    'get_email_backend',
    'BaseEmailBackend',
    'SESBackend',
    'SMTPBackend',
    'ConsoleBackend',
]
