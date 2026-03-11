"""
Data migration to clear all user-related data before UUID migration.

This migration runs BEFORE the schema migration that converts User.id
from BigAutoField to UUIDField. It clears all dependent data to prevent
integrity errors during the FK column type changes.
"""

from django.db import migrations


def clear_user_data(apps, schema_editor):
    """Clear all user-related data before UUID migration."""
    # Order matters - clear dependent tables first

    # Auth models (label is 'authentication' to avoid conflict with Django's built-in 'auth')
    RefreshToken = apps.get_model('authentication', 'RefreshToken')
    DeviceSession = apps.get_model('authentication', 'DeviceSession')
    EmailVerificationToken = apps.get_model('authentication', 'EmailVerificationToken')
    PasswordResetToken = apps.get_model('authentication', 'PasswordResetToken')
    OAuthConnection = apps.get_model('authentication', 'OAuthConnection')

    RefreshToken.objects.all().delete()
    DeviceSession.objects.all().delete()
    EmailVerificationToken.objects.all().delete()
    PasswordResetToken.objects.all().delete()
    OAuthConnection.objects.all().delete()

    # Notification models
    NotificationPreference = apps.get_model('notifications', 'NotificationPreference')
    NotificationLog = apps.get_model('notifications', 'NotificationLog')

    NotificationPreference.objects.all().delete()
    NotificationLog.objects.all().delete()

    # Organization - clear verified_by references (set to NULL, don't delete businesses)
    BusinessAccount = apps.get_model('organization', 'BusinessAccount')
    BusinessAccount.objects.update(verified_by=None, created_by=None, updated_by=None, deleted_by=None)

    PlatformAccount = apps.get_model('organization', 'PlatformAccount')
    PlatformAccount.objects.update(created_by=None, updated_by=None, deleted_by=None)

    # User models - clear self-reference first, then profiles, then users
    User = apps.get_model('users', 'User')
    User.objects.update(referred_by=None)

    UserProfile = apps.get_model('users', 'UserProfile')
    UserProfile.objects.all().delete()

    User.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0004_remove_user_verified_only_if_active'),
        ('authentication', '0001_initial'),
        ('notifications', '0001_initial'),
        ('organization', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(clear_user_data, migrations.RunPython.noop),
    ]
