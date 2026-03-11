"""
Email Services
==============
Service layer for email operations.

Components:
    - EmailService: High-level send API
    - TemplateRenderer: Template rendering with context
    - Backends: SES and SMTP delivery backends
"""

from apps.email.services.email_service import EmailService
from apps.email.services.template_renderer import TemplateRenderer

__all__ = ['EmailService', 'TemplateRenderer']
