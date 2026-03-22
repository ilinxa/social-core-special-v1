"""
Seed essential email templates for auth and notification flows.

Usage:
    python manage.py seed_email_templates

Idempotent — skips templates that already exist (by name + is_current=True).
"""

from django.core.management.base import BaseCommand

from apps.email.models import EmailTemplate

TEMPLATES = [
    {
        "name": "verify_email",
        "subject": "Verify your email address",
        "html_body": (
            "<h2>Verify your email</h2>"
            "<p>Hi {{ user_name }},</p>"
            "<p>Your verification code is: <strong>{{ code }}</strong></p>"
            "<p>Or click the link below to verify your email:</p>"
            '<p><a href="{{ verification_link }}">Verify Email</a></p>'
            "<p>This code expires in 15 minutes.</p>"
        ),
        "text_body": (
            "Verify your email\n\n"
            "Hi {{ user_name }},\n\n"
            "Your verification code is: {{ code }}\n\n"
            "Or visit: {{ verification_link }}\n\n"
            "This code expires in 15 minutes."
        ),
        "variables": {
            "user_name": {"type": "string", "required": False},
            "user_email": {"type": "string", "required": False},
            "code": {"type": "string", "required": True},
            "verification_link": {"type": "string", "required": True},
        },
        "category": "auth",
        "description": "Sent after registration to verify email address.",
    },
    {
        "name": "welcome",
        "subject": "Welcome to our platform!",
        "html_body": (
            "<h2>Welcome!</h2>"
            "<p>Hi {{ user_name }},</p>"
            "<p>Your email has been verified. You're all set!</p>"
        ),
        "text_body": (
            "Welcome!\n\n"
            "Hi {{ user_name }},\n\n"
            "Your email has been verified. You're all set!"
        ),
        "variables": {
            "user_name": {"type": "string", "required": False},
            "user_email": {"type": "string", "required": False},
        },
        "category": "auth",
        "description": "Sent after email verification is complete.",
    },
    {
        "name": "password_reset",
        "subject": "Reset your password",
        "html_body": (
            "<h2>Password Reset</h2>"
            "<p>Hi {{ user_name }},</p>"
            "<p>Click the link below to reset your password:</p>"
            '<p><a href="{{ reset_link }}">Reset Password</a></p>'
            "<p>This link expires in 1 hour. "
            "If you didn't request this, ignore this email.</p>"
        ),
        "text_body": (
            "Password Reset\n\n"
            "Hi {{ user_name }},\n\n"
            "Visit this link to reset your password: {{ reset_link }}\n\n"
            "This link expires in 1 hour. "
            "If you didn't request this, ignore this email."
        ),
        "variables": {
            "user_name": {"type": "string", "required": False},
            "user_email": {"type": "string", "required": False},
            "reset_link": {"type": "string", "required": True},
        },
        "category": "auth",
        "description": "Sent when a user requests a password reset.",
    },
    {
        "name": "password_changed",
        "subject": "Your password has been changed",
        "html_body": (
            "<h2>Password Changed</h2>"
            "<p>Hi {{ user_name }},</p>"
            "<p>Your password was successfully changed.</p>"
            "<p>If you didn't make this change, "
            "please contact support immediately.</p>"
        ),
        "text_body": (
            "Password Changed\n\n"
            "Hi {{ user_name }},\n\n"
            "Your password was successfully changed.\n\n"
            "If you didn't make this change, "
            "please contact support immediately."
        ),
        "variables": {
            "user_name": {"type": "string", "required": False},
            "user_email": {"type": "string", "required": False},
        },
        "category": "auth",
        "description": "Sent after a successful password change.",
    },
]


class Command(BaseCommand):
    help = "Seed essential email templates (idempotent — skips existing)."

    def handle(self, *args, **options):
        created = 0
        skipped = 0

        for tmpl_data in TEMPLATES:
            name = tmpl_data["name"]
            if EmailTemplate.objects.filter(name=name, is_current=True).exists():
                self.stdout.write(f"  Skipped: {name} (already exists)")
                skipped += 1
            else:
                EmailTemplate.objects.create(
                    **tmpl_data,
                    version=1,
                    is_active=True,
                    is_current=True,
                )
                self.stdout.write(self.style.SUCCESS(f"  Created: {name}"))
                created += 1

        self.stdout.write(
            self.style.SUCCESS(f"\nDone — {created} created, {skipped} skipped.")
        )
