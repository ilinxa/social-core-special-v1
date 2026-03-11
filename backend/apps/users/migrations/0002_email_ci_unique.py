"""
Case-Insensitive Email Uniqueness
=================================
This migration adds a functional index on LOWER(email) for PostgreSQL
to enforce case-insensitive email uniqueness at the database level.

For SQLite (local development), this is a no-op as SQLite handles
case-insensitivity differently and we rely on application-level checks.

The application-level check in UserService.create_user() uses __iexact
to prevent duplicate emails regardless of case.
"""

from django.db import migrations


def create_ci_email_index(apps, schema_editor):
    """Create case-insensitive email index on PostgreSQL only."""
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_uniq
            ON users (LOWER(email));
        """)


def drop_ci_email_index(apps, schema_editor):
    """Drop case-insensitive email index on PostgreSQL only."""
    if schema_editor.connection.vendor == 'postgresql':
        schema_editor.execute("DROP INDEX IF EXISTS users_email_lower_uniq;")


class Migration(migrations.Migration):
    """
    Add case-insensitive email uniqueness constraint.

    PostgreSQL: Creates a unique index on LOWER(email)
    SQLite/Others: No-op (relies on application-level checks)
    """

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_ci_email_index,
            drop_ci_email_index,
        ),
    ]
