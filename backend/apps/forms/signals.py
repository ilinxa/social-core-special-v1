from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.forms.models import FormResponse
from apps.core.constants import ResponseStatus


@receiver(post_save, sender=FormResponse)
def on_response_submitted(sender, instance, created, **kwargs):
    """
    React to response submission.
    Can be extended for notifications, webhooks, etc.
    """
    if not created and instance.status == ResponseStatus.SUBMITTED:
        pass  # Placeholder for future notification integration
