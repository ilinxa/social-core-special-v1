"""
Email App
=========
Infrastructure for email delivery via AWS SES or SMTP.

This app is a "dumb pipe" - it sends what it's told, when it's told.
Business logic (when to send, to whom) lives in the Notifications system.

Key Components:
    - EmailTemplate: Admin-manageable versioned templates
    - EmailLog: Full audit trail of sent emails
    - EmailService: High-level send API
    - SES/SMTP backends: Pluggable delivery backends
"""

default_app_config = "apps.email.apps.EmailConfig"
