---
name: django-notifications
description: Guide for implementing the multi-channel notification system in Django apps. Use when adding notifications for user actions, events, or system alerts. Covers notification type definition, email template creation, service integration, user preferences, and multi-channel dispatch (email, push, SMS). Trigger when user requests notifications for features like: user registration, password reset, content updates, subscriptions, orders, comments, friend requests, reminders, or any event requiring user communication.
---

# Django Notifications System

Implement multi-channel notifications (email, push, SMS) in your Django apps using the centralized notification system.

## Quick Start

Send a notification in 3 steps:

```python
from apps.notifications.services import NotificationService

# 1. Send notification (assumes type already defined)
NotificationService.send(
    user=user,
    notification_type='welcome',
    context={'extra_field': 'value'}
)
```

## Core Concepts

### System Architecture

**Notifications App** (`apps.notifications`):
- Handles "when to send" - business logic
- Multi-channel dispatch (email, push, SMS)
- User preference management
- Delivery tracking and retry logic

**Email App** (`apps.email`):
- Handles "how to send" - delivery infrastructure
- Template management with versioning
- Pluggable backends (SES, SMTP, console)
- Webhook tracking (delivery, bounce, complaint)

**Relationship**: Notifications delegates email delivery to Email system via EmailChannel.

### Notification Flow

```
Your App → NotificationService.send()
    ↓
Create NotificationLog (status=PENDING, channels=['email', 'push'])
    ↓
Celery: dispatch_notification_task (async, default)
    ↓
For each enabled channel:
    EmailChannel → EmailService.send() → EmailLog → Celery: send_email_task
    PushChannel → (placeholder, not implemented)
    ↓
Update NotificationLog (status=SENT/PARTIAL/FAILED)
    ↓
If PARTIAL → retry failed channels after 5 min
```

## Implementation Workflow

### Step 1: Define Notification Type

Edit `apps/notifications/types.py`:

```python
from apps.notifications.enums import Category, Channel
from apps.notifications.types import NotificationTypeConfig

NOTIFICATION_TYPES = {
    # ... existing types ...

    'your_new_type': NotificationTypeConfig(
        name='your_new_type',
        display_name='Your New Type',
        description='Description shown to users in preferences',
        category=Category.TRANSACTIONAL,  # or AUTH, SECURITY, MARKETING, SYSTEM
        default_channels=[Channel.EMAIL],  # Default enabled channels
        required_context=['field1', 'field2'],  # Required template variables
        email_template='your_template_name',  # Links to EmailTemplate.name
        push_template=None,  # Not implemented yet
        sms_template=None,   # Not implemented yet
        user_configurable=True,  # Can user disable this notification?
        enabled=True,
    ),
}
```

**Categories**:
- `AUTH` - Authentication (login, registration, verification)
- `SECURITY` - Security alerts (suspicious activity, password changes)
- `TRANSACTIONAL` - Business transactions (orders, payments, confirmations)
- `MARKETING` - Promotional content (newsletters, announcements)
- `SYSTEM` - System messages (maintenance, updates)

**Channels**:
- `Channel.EMAIL` - Email notifications (implemented)
- `Channel.PUSH` - Push notifications (placeholder)
- `Channel.SMS` - SMS notifications (placeholder)

**user_configurable**:
- `True` - User can disable in preferences (newsletters, marketing)
- `False` - Mandatory, cannot be disabled (security, auth)

**For detailed type configuration options, see** [references/types.md](references/types.md)

### Step 2: Create Email Template

Via Django Admin (`/admin/email/emailtemplate/add/`):

**Required Fields**:
- **name**: Unique identifier (matches `email_template` in type config)
- **subject**: Email subject with {{ variables }}
- **html_body**: HTML content with {{ variables }}
- **text_body**: Plain text (auto-generated from HTML if empty)
- **variables**: JSON schema for validation
  ```json
  {
    "field1": {"type": "string", "required": true},
    "field2": {"type": "string", "required": false}
  }
  ```
- **category**: auth, transactional, marketing, system
- **is_active**: Must be true to use

**Template Syntax**: Django templates
```django
<h1>Hello {{ user_name }}</h1>
<p>Click here: <a href="{{ action_link }}">Action</a></p>
```

**Automatic Context** (always available):
- `user_email` - User's email address
- `user_name` - User's display name from profile

**Versioning**: Editing creates new version, preserves history

**For template management details, see** [references/templates.md](references/templates.md)

### Step 3: Send from Your App

```python
from apps.notifications.services import NotificationService

# Basic send (async by default, respects user preferences)
log = NotificationService.send(
    user=user,
    notification_type='your_new_type',
    context={
        'field1': 'value1',
        'field2': 'value2',
    }
)

# With options
log = NotificationService.send(
    user=user,
    notification_type='your_new_type',
    context={'field1': 'value1', 'field2': 'value2'},
    force_channels=['email'],  # Override user preferences (for critical notifications)
    async_dispatch=False       # Send synchronously (rare, for immediate feedback)
)

# Bulk send to multiple users
logs = NotificationService.send_bulk(
    users=[user1, user2, user3],
    notification_type='your_new_type',
    context_fn=lambda user: {
        'field1': f'value for {user.email}',
        'field2': 'shared value',
    }
)
```

**Return Value**: `NotificationLog` instance with:
- `id` - UUID
- `status` - PENDING, PROCESSING, SENT, PARTIAL, FAILED
- `channels` - List of channels ['email', 'push']
- `channel_results` - Dict with per-channel status

**Exceptions**:
- `NotFound` - Unknown notification type
- `ValidationError` - Type disabled or missing required context

**For integration examples and patterns, see** [references/integration.md](references/integration.md)

## User Preferences

Users manage preferences via API:

```
GET    /api/v1/notifications/preferences/           # All preferences by category
GET    /api/v1/notifications/preferences/{type}/    # Single preference
PATCH  /api/v1/notifications/preferences/{type}/    # Update channels
DELETE /api/v1/notifications/preferences/{type}/    # Reset to defaults
GET    /api/v1/notifications/history/               # Notification history
GET    /api/v1/notifications/types/                 # User-configurable types
```

**Default Behavior**:
- No preference row = use defaults from NotificationTypeConfig
- Preference row = user override

**Mandatory Types**: Cannot be disabled (verify_email, password_reset, suspicious_activity)

## Multi-Channel Support

### Email Channel (Implemented)
- Delegates to EmailService
- Uses email_template from type config
- Tracks delivery via webhooks

### Push Channel (Placeholder)
- Returns `{'status': 'skipped', 'reason': 'Not implemented yet'}`
- To implement: Add Firebase Cloud Messaging in `channels/push.py`

### SMS Channel (Placeholder)
- Returns `{'status': 'skipped', 'reason': 'Not implemented yet'}`
- To implement: Add Twilio in `channels/sms.py`

## Common Patterns

### Pattern 1: Simple Notification
```python
# User completes action
def complete_action(user):
    # ... business logic ...

    NotificationService.send(
        user=user,
        notification_type='action_completed',
        context={'action_name': 'Profile Update'}
    )
```

### Pattern 2: Critical Notification (Force Channels)
```python
# Security alert - ignore user preferences
def log_suspicious_activity(user, activity_type):
    NotificationService.send(
        user=user,
        notification_type='suspicious_activity',
        context={
            'activity_type': activity_type,
            'timestamp': timezone.now().isoformat(),
            'ip_address': get_client_ip()
        },
        force_channels=['email', 'push']  # Send regardless of preferences
    )
```

### Pattern 3: Bulk Notification
```python
# Newsletter to all subscribers
def send_newsletter(content):
    subscribers = User.objects.filter(is_newsletter_subscribed=True)

    NotificationService.send_bulk(
        users=subscribers,
        notification_type='newsletter',
        context_fn=lambda user: {
            'content': content,
            'unsubscribe_link': f'/unsubscribe?token={user.unsubscribe_token}'
        }
    )
```

### Pattern 4: Synchronous Send (Rare)
```python
# Need immediate feedback (e.g., verification code display)
def send_verification_code(user):
    code = generate_code()

    log = NotificationService.send(
        user=user,
        notification_type='verify_email',
        context={'verification_code': code, 'verification_link': f'/verify?code={code}'},
        async_dispatch=False  # Wait for result
    )

    if log.status == 'FAILED':
        raise ServiceUnavailable('Failed to send verification email')

    return code
```

## Testing Notifications

```python
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationLog

def test_send_notification(self):
    log = NotificationService.send(
        user=self.user,
        notification_type='welcome',
        context={},
        async_dispatch=False  # Synchronous for testing
    )

    self.assertEqual(log.status, 'SENT')
    self.assertIn('email', log.channels)
```

## Troubleshooting

| Issue | Check |
|-------|-------|
| Notification not sent | 1. Verify type in NOTIFICATION_TYPES<br>2. Check user preferences<br>3. Check NotificationLog.status<br>4. Verify Celery worker running |
| Template not found | 1. Check EmailTemplate exists in admin<br>2. Verify is_active=True, is_current=True<br>3. Match name with type config |
| Missing context error | 1. Check required_context in type config<br>2. Verify all fields provided in context dict |
| Email not delivered | 1. Check EmailLog.status<br>2. Verify EMAIL_BACKEND_TYPE setting<br>3. Check bounce/complaint logs |

## Configuration

```python
# backend_core/settings/base.py

INSTALLED_APPS = [
    'apps.notifications',
    'apps.email',
]

# Retention
NOTIFICATION_LOG_RETENTION_DAYS = 90
EMAIL_LOG_RETENTION_DAYS = 90

# Email backend
EMAIL_BACKEND_TYPE = 'console'  # or 'ses', 'smtp'
DEFAULT_FROM_EMAIL = 'noreply@example.com'

# Celery (required for async)
CELERY_BROKER_URL = 'redis://localhost:6379/0'
```

## Reference Files

- **[references/types.md](references/types.md)** - Complete notification type configuration guide
- **[references/templates.md](references/templates.md)** - Email template management and best practices
- **[references/integration.md](references/integration.md)** - Integration patterns and code examples

## Quick Reference

```python
# Import
from apps.notifications.services import NotificationService

# Send
log = NotificationService.send(
    user=user,
    notification_type='type_name',
    context={'key': 'value'}
)

# Bulk
logs = NotificationService.send_bulk(
    users=[user1, user2],
    notification_type='type_name',
    context_fn=lambda u: {'key': f'value-{u.id}'}
)

# Force channels (critical)
log = NotificationService.send(
    user=user,
    notification_type='security_alert',
    context={'details': '...'},
    force_channels=['email', 'push']
)

# Synchronous (rare)
log = NotificationService.send(
    user=user,
    notification_type='verification',
    context={'code': '123456'},
    async_dispatch=False
)
```
