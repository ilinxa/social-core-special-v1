from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.core.constants import ResponseStatus
from apps.forms.models import FormResponse


@receiver(post_save, sender=FormResponse, dispatch_uid="on_response_submitted")
def on_response_submitted(sender, instance, created, **kwargs):
    """
    React to response submission.
    Can be extended for notifications, webhooks, etc.
    """
    if not created and instance.status == ResponseStatus.SUBMITTED:
        pass  # Placeholder for future notification integration
