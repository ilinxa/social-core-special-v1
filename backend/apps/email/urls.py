"""
Email URLs
==========
URL configuration for email app.

Currently only exposes webhook endpoints.
Template management is via admin interface.
"""

from django.urls import path

from apps.email import webhooks

app_name = 'email'

urlpatterns = [
    # SES webhook endpoint
    # Configure this URL in AWS SES/SNS for delivery/bounce/complaint notifications
    path('webhooks/ses/', webhooks.ses_webhook, name='ses-webhook'),
]
