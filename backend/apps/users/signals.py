"""
User Signals
============
Django signals for the Users app.

Signals:
    - create_user_profile: Auto-create UserProfile when User is created

Important:
    Uses transaction.on_commit() to ensure profile is only created
    if the user creation transaction commits successfully. This prevents
    orphan profiles when user creation fails or rolls back.
"""

from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.users.models import User, UserProfile
from apps.core.observability import get_logger

logger = get_logger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create UserProfile when User is created.

    This signal handler:
        - Only runs when a new User is created (not on updates)
        - Uses transaction.on_commit() to prevent orphan profiles
        - Logs errors if profile creation fails

    Args:
        sender: The model class (User)
        instance: The User instance that was saved
        created: True if this is a new User, False if update
        **kwargs: Additional signal arguments

    Why transaction.on_commit?
        If the user creation is part of a larger transaction that fails,
        we don't want to create a profile. on_commit ensures the profile
        is only created after the transaction successfully commits.
    """
    if created:
        def _create_profile():
            # Guard against duplicate profile creation
            # This can happen if signal fires multiple times or profile created manually
            if UserProfile.objects.filter(user_id=instance.id).exists():
                logger.debug(f"Profile already exists for user {instance.id}, skipping")
                return

            try:
                UserProfile.objects.create(user=instance)
                logger.debug(f"Created profile for user {instance.id}")
            except Exception as e:
                # Could be race condition or database error
                logger.error(
                    f"Failed to create profile for user {instance.id}: {e}"
                )

        transaction.on_commit(_create_profile)
