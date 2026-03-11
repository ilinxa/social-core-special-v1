# Template for adding a new notification type
# Copy this template and customize for your notification

from apps.notifications.enums import Category, Channel
from apps.notifications.types import NotificationTypeConfig

# Add to NOTIFICATION_TYPES dict in apps/notifications/types.py
NOTIFICATION_TYPES = {
    # ... existing types ...

    'your_notification_name': NotificationTypeConfig(
        # Unique identifier (snake_case)
        name='your_notification_name',

        # Human-readable name shown in preferences UI (Title Case)
        display_name='Your Notification Name',

        # Description shown to users (one sentence, user perspective)
        description='Sent when [describe when this notification is sent]',

        # Category for grouping in preferences
        # Options: Category.AUTH, Category.SECURITY, Category.TRANSACTIONAL,
        #          Category.MARKETING, Category.SYSTEM
        category=Category.TRANSACTIONAL,

        # Channels enabled by default
        # Options: Channel.EMAIL, Channel.PUSH, Channel.SMS
        default_channels=[Channel.EMAIL],

        # Required template variables (must be provided in context)
        # Empty list [] if no required fields
        # Note: user_email and user_name are auto-added, don't include them
        required_context=['field1', 'field2'],

        # Email template name (must match EmailTemplate.name in admin)
        # Set to None if not using email channel
        email_template='your_template_name',

        # Push template (not implemented yet, always None)
        push_template=None,

        # SMS template (not implemented yet, always None)
        sms_template=None,

        # Can user disable this notification?
        # True: User can toggle in preferences (newsletters, optional updates)
        # False: Mandatory (security alerts, authentication, critical)
        user_configurable=True,

        # Is notification type active?
        # True: Active and can be used
        # False: Disabled (feature flag, A/B testing)
        enabled=True,
    ),
}

# After adding the type configuration:
# 1. Create email template in Django admin at /admin/email/emailtemplate/add/
#    - name: must match email_template value above
#    - subject: email subject with {{ variables }}
#    - html_body: HTML content with {{ variables }}
#    - variables: JSON schema matching required_context
#    - category: matching category above
#    - is_active: True
#
# 2. Send notification from your app:
#    from apps.notifications.services import NotificationService
#
#    NotificationService.send(
#        user=user,
#        notification_type='your_notification_name',
#        context={
#            'field1': 'value1',
#            'field2': 'value2',
#        }
#    )
