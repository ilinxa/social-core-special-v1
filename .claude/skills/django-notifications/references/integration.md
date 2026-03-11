# Notification Integration Patterns

Code examples and patterns for integrating notifications into Django apps.

## Table of Contents

1. [Basic Integration](#basic-integration)
2. [Common Use Cases](#common-use-cases)
3. [Advanced Patterns](#advanced-patterns)
4. [Error Handling](#error-handling)
5. [Testing](#testing)
6. [Performance Considerations](#performance-considerations)

## Basic Integration

### Minimal Setup

```python
from apps.notifications.services import NotificationService

# In your app's views, services, or signal handlers
def my_function(user):
    # Your business logic
    result = do_something()

    # Send notification
    NotificationService.send(
        user=user,
        notification_type='action_completed',
        context={'result': result}
    )
```

### With Error Handling

```python
from apps.notifications.services import NotificationService
from apps.core.exceptions import NotFound, ValidationError

def my_function(user):
    result = do_something()

    try:
        NotificationService.send(
            user=user,
            notification_type='action_completed',
            context={'result': result}
        )
    except (NotFound, ValidationError) as e:
        # Log error but don't fail the main operation
        logger.error(f"Failed to send notification: {e}")
```

## Common Use Cases

### 1. User Registration Flow

```python
# apps/users/services.py
from apps.notifications.services import NotificationService
from apps.users.models import User
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

def register_user(email, password, **profile_data):
    """Register new user and send verification email"""

    # Create user (inactive until verified)
    user = User.objects.create_user(
        email=email,
        password=password,
        is_active=False
    )

    # Create profile
    user.profile.display_name = profile_data.get('display_name', email.split('@')[0])
    user.profile.save()

    # Generate verification token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    verification_link = f"https://example.com/verify/{uid}/{token}/"

    # Send verification email
    NotificationService.send(
        user=user,
        notification_type='verify_email',
        context={
            'verification_link': verification_link,
            'verification_code': token[:6].upper()  # First 6 chars as code
        },
        async_dispatch=False  # Send immediately for better UX
    )

    return user
```

### 2. Password Reset

```python
# apps/auth/services.py
from apps.notifications.services import NotificationService
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

def request_password_reset(email):
    """Send password reset email"""

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # Security: don't reveal if email exists
        # Send fake notification delay
        import time
        time.sleep(0.5)
        return

    # Generate reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    reset_link = f"https://example.com/reset/{uid}/{token}/"

    # Send reset email (force channels for security)
    NotificationService.send(
        user=user,
        notification_type='password_reset',
        context={'reset_link': reset_link},
        force_channels=['email'],  # Always send via email
        async_dispatch=False  # Immediate send
    )
```

### 3. Order Status Updates

```python
# apps/orders/services.py
from apps.notifications.services import NotificationService
from apps.orders.models import Order

def mark_order_shipped(order_id, tracking_number, carrier):
    """Mark order as shipped and notify customer"""

    order = Order.objects.get(id=order_id)
    order.status = 'shipped'
    order.tracking_number = tracking_number
    order.carrier = carrier
    order.save()

    # Build tracking URL
    tracking_urls = {
        'UPS': f'https://www.ups.com/track?tracknum={tracking_number}',
        'FedEx': f'https://www.fedex.com/apps/fedextrack/?tracknumbers={tracking_number}',
        'USPS': f'https://tools.usps.com/go/TrackConfirmAction?tLabels={tracking_number}',
    }
    tracking_url = tracking_urls.get(carrier, '#')

    # Send notification
    NotificationService.send(
        user=order.user,
        notification_type='order_shipped',
        context={
            'order_id': str(order.id),
            'tracking_number': tracking_number,
            'carrier': carrier,
            'tracking_url': tracking_url,
            'estimated_delivery': order.estimated_delivery.strftime('%B %d, %Y'),
        }
    )

    return order
```

### 4. Comment Notifications

```python
# apps/posts/services.py
from apps.notifications.services import NotificationService
from apps.posts.models import Post, Comment

def create_comment(post_id, user, text):
    """Create comment and notify post author"""

    post = Post.objects.get(id=post_id)
    comment = Comment.objects.create(
        post=post,
        user=user,
        text=text
    )

    # Don't notify if commenting on own post
    if post.author != user:
        NotificationService.send(
            user=post.author,
            notification_type='comment_reply',
            context={
                'post_title': post.title,
                'post_url': f'https://example.com/posts/{post.id}/',
                'comment_author': user.profile.display_name,
                'comment_text': text[:200],  # Truncate for email preview
            }
        )

    return comment
```

### 5. Subscription Expiring Reminder

```python
# apps/subscriptions/tasks.py
from apps.notifications.services import NotificationService
from apps.subscriptions.models import Subscription
from django.utils import timezone
from datetime import timedelta
from celery import shared_task

@shared_task
def send_expiring_subscription_reminders():
    """Daily task to send subscription expiration reminders"""

    # Find subscriptions expiring in 7 days
    expiry_date = timezone.now() + timedelta(days=7)
    expiring_subs = Subscription.objects.filter(
        expires_at__date=expiry_date.date(),
        is_active=True,
        auto_renew=False
    )

    for sub in expiring_subs:
        NotificationService.send(
            user=sub.user,
            notification_type='subscription_expiring',
            context={
                'expiry_date': sub.expires_at.strftime('%B %d, %Y'),
                'plan_name': sub.plan.name,
                'renewal_url': f'https://example.com/subscriptions/{sub.id}/renew/',
            }
        )
```

### 6. Bulk Newsletter

```python
# apps/marketing/services.py
from apps.notifications.services import NotificationService
from apps.users.models import User

def send_newsletter(subject, content, image_url=None):
    """Send newsletter to all opted-in users"""

    # Get users who opted in to newsletters
    subscribers = User.objects.filter(
        is_active=True,
        profile__newsletter_opt_in=True
    )

    # Send bulk notification
    logs = NotificationService.send_bulk(
        users=subscribers,
        notification_type='newsletter',
        context_fn=lambda user: {
            'subject': subject,
            'content': content,
            'image_url': image_url,
            'unsubscribe_link': f'https://example.com/unsubscribe/?token={user.unsubscribe_token}',
        }
    )

    return {
        'sent': len(logs),
        'recipients': subscribers.count()
    }
```

### 7. Welcome Email After Email Verification

```python
# apps/auth/services.py
from apps.notifications.services import NotificationService
from django.contrib.auth.tokens import default_token_generator

def verify_email(uid, token):
    """Verify email and send welcome notification"""

    user = get_user_from_token(uid, token)

    if not default_token_generator.check_token(user, token):
        raise ValidationError('Invalid or expired token')

    # Activate user
    user.is_active = True
    user.email_verified = True
    user.save()

    # Send welcome email
    NotificationService.send(
        user=user,
        notification_type='welcome',
        context={
            'getting_started_url': 'https://example.com/getting-started/',
        }
    )

    return user
```

### 8. Security Alert

```python
# apps/auth/services.py
from apps.notifications.services import NotificationService
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

@receiver(user_logged_in)
def check_suspicious_login(sender, request, user, **kwargs):
    """Detect and alert on suspicious login attempts"""

    # Get client info
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')

    # Check if new device
    is_new_device = not LoginHistory.objects.filter(
        user=user,
        ip_address=ip_address
    ).exists()

    if is_new_device:
        # Log the login
        LoginHistory.objects.create(
            user=user,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Send security alert (force channels, ignore preferences)
        NotificationService.send(
            user=user,
            notification_type='new_login',
            context={
                'ip_address': ip_address,
                'device': parse_user_agent(user_agent),
                'location': get_ip_location(ip_address),
                'timestamp': timezone.now().isoformat(),
                'secure_account_url': 'https://example.com/account/security/',
            },
            force_channels=['email', 'push']  # Critical security alert
        )
```

## Advanced Patterns

### Pattern 1: Conditional Notifications

```python
from apps.notifications.services import NotificationService
from apps.notifications.services import PreferenceService

def notify_if_enabled(user, notification_type, context):
    """Only send if user has at least one channel enabled"""

    enabled_channels = PreferenceService.get_enabled_channels(
        user=user,
        notification_type=notification_type
    )

    if enabled_channels:
        NotificationService.send(
            user=user,
            notification_type=notification_type,
            context=context
        )
    else:
        logger.info(f"User {user.id} has disabled all channels for {notification_type}")
```

### Pattern 2: Aggregated Notifications

```python
from apps.notifications.services import NotificationService
from django.utils import timezone
from datetime import timedelta

def send_daily_digest(user):
    """Send daily digest of activity instead of individual notifications"""

    # Get today's activity
    today = timezone.now().date()
    activities = Activity.objects.filter(
        user=user,
        created_at__date=today
    )

    if not activities.exists():
        return

    # Aggregate by type
    activity_summary = {
        'comments': activities.filter(type='comment').count(),
        'likes': activities.filter(type='like').count(),
        'follows': activities.filter(type='follow').count(),
    }

    # Send single digest notification
    NotificationService.send(
        user=user,
        notification_type='daily_digest',
        context={
            'date': today.strftime('%B %d, %Y'),
            'total_activities': activities.count(),
            'activity_breakdown': activity_summary,
            'view_all_url': 'https://example.com/activity/',
        }
    )
```

### Pattern 3: Rate-Limiting Notifications

```python
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationLog
from django.utils import timezone
from datetime import timedelta

def send_with_rate_limit(user, notification_type, context, limit_hours=24):
    """Don't send same notification type more than once per period"""

    # Check recent notifications
    cutoff = timezone.now() - timedelta(hours=limit_hours)
    recent = NotificationLog.objects.filter(
        user=user,
        notification_type=notification_type,
        created_at__gte=cutoff
    ).exists()

    if recent:
        logger.info(f"Rate limit: {notification_type} already sent to {user.id} in last {limit_hours}h")
        return None

    return NotificationService.send(
        user=user,
        notification_type=notification_type,
        context=context
    )
```

### Pattern 4: Multi-User Notifications

```python
from apps.notifications.services import NotificationService

def notify_team_members(team, notification_type, context):
    """Send notification to all team members"""

    members = team.members.filter(is_active=True)

    # Use bulk send for efficiency
    logs = NotificationService.send_bulk(
        users=members,
        notification_type=notification_type,
        context_fn=lambda user: {
            **context,
            'team_name': team.name,
            'member_name': user.profile.display_name,
        }
    )

    return logs
```

### Pattern 5: Escalation Notifications

```python
from apps.notifications.services import NotificationService
from django.utils import timezone

def send_escalating_reminder(user, task):
    """Send increasingly urgent reminders"""

    days_overdue = (timezone.now().date() - task.due_date).days

    if days_overdue == 1:
        # First reminder: email only
        NotificationService.send(
            user=user,
            notification_type='task_overdue',
            context={'task_title': task.title, 'days_overdue': 1},
            force_channels=['email']
        )
    elif days_overdue == 3:
        # Second reminder: email + push
        NotificationService.send(
            user=user,
            notification_type='task_overdue',
            context={'task_title': task.title, 'days_overdue': 3},
            force_channels=['email', 'push']
        )
    elif days_overdue >= 7:
        # Final reminder: all channels
        NotificationService.send(
            user=user,
            notification_type='task_critical_overdue',
            context={'task_title': task.title, 'days_overdue': days_overdue},
            force_channels=['email', 'push', 'sms']
        )
```

## Error Handling

### Pattern 1: Graceful Degradation

```python
from apps.notifications.services import NotificationService
from apps.core.exceptions import NotFound, ValidationError, ServiceUnavailable
import logging

logger = logging.getLogger(__name__)

def send_notification_safely(user, notification_type, context):
    """Send notification without failing main operation"""

    try:
        return NotificationService.send(
            user=user,
            notification_type=notification_type,
            context=context
        )
    except NotFound:
        # Unknown notification type - log as error
        logger.error(f"Unknown notification type: {notification_type}")
    except ValidationError as e:
        # Missing context or invalid config - log as error
        logger.error(f"Notification validation error: {e}")
    except ServiceUnavailable:
        # Email service down - log as warning (will retry)
        logger.warning(f"Notification service unavailable for {notification_type}")
    except Exception as e:
        # Unexpected error - log but don't crash
        logger.exception(f"Unexpected error sending notification: {e}")

    return None
```

### Pattern 2: Retry on Failure

```python
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationLog
from celery import shared_task

@shared_task(bind=True, max_retries=3)
def send_critical_notification(self, user_id, notification_type, context):
    """Send critical notification with automatic retries"""

    try:
        user = User.objects.get(id=user_id)
        log = NotificationService.send(
            user=user,
            notification_type=notification_type,
            context=context,
            async_dispatch=False  # Synchronous to detect failures
        )

        if log.status == 'FAILED':
            raise Exception(f"Notification failed: {log.error_message}")

        return log.id

    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### Pattern 3: Fallback Channels

```python
from apps.notifications.services import NotificationService
from apps.email.services import EmailService

def send_with_fallback(user, notification_type, context):
    """Try notification system, fallback to direct email"""

    try:
        return NotificationService.send(
            user=user,
            notification_type=notification_type,
            context=context
        )
    except Exception as e:
        logger.error(f"Notification system failed: {e}, falling back to direct email")

        # Fallback: send simple email directly
        return EmailService.send_raw(
            to_email=user.email,
            subject=f"Notification: {notification_type}",
            html_body=f"<p>Context: {context}</p>",
            async_send=True
        )
```

## Testing

### Unit Tests

```python
from django.test import TestCase
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationLog
from apps.users.models import User

class NotificationTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='password123'
        )

    def test_send_welcome_notification(self):
        """Test welcome notification is sent"""

        log = NotificationService.send(
            user=self.user,
            notification_type='welcome',
            context={},
            async_dispatch=False  # Synchronous for testing
        )

        self.assertEqual(log.status, 'SENT')
        self.assertEqual(log.notification_type, 'welcome')
        self.assertIn('email', log.channels)

    def test_send_with_required_context(self):
        """Test notification with required context"""

        log = NotificationService.send(
            user=self.user,
            notification_type='password_reset',
            context={'reset_link': 'https://example.com/reset/'},
            async_dispatch=False
        )

        self.assertEqual(log.status, 'SENT')
        self.assertEqual(log.context['reset_link'], 'https://example.com/reset/')

    def test_missing_required_context_raises_error(self):
        """Test validation error on missing context"""

        from apps.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            NotificationService.send(
                user=self.user,
                notification_type='password_reset',
                context={},  # Missing 'reset_link'
                async_dispatch=False
            )

    def test_bulk_send(self):
        """Test bulk notification sending"""

        users = [
            User.objects.create_user(email=f'user{i}@example.com', password='pass')
            for i in range(5)
        ]

        logs = NotificationService.send_bulk(
            users=users,
            notification_type='newsletter',
            context_fn=lambda u: {'content': f'Newsletter for {u.email}'}
        )

        self.assertEqual(len(logs), 5)
```

### Integration Tests

```python
from django.test import TestCase
from apps.notifications.services import NotificationService
from apps.email.models import EmailLog

class NotificationIntegrationTestCase(TestCase):
    def test_notification_creates_email(self):
        """Test notification creates corresponding email log"""

        user = User.objects.create_user(email='test@example.com', password='pass')

        log = NotificationService.send(
            user=user,
            notification_type='welcome',
            context={},
            async_dispatch=False
        )

        # Check email was created
        email_log_id = log.channel_results['email']['email_log_id']
        email_log = EmailLog.objects.get(id=email_log_id)

        self.assertEqual(email_log.to_email, user.email)
        self.assertEqual(email_log.template_name, 'welcome')
        self.assertEqual(email_log.status, 'SENT')
```

## Performance Considerations

### 1. Use Async Dispatch (Default)

```python
# Good: async by default (queues to Celery)
NotificationService.send(
    user=user,
    notification_type='order_shipped',
    context={'order_id': '123'},
    async_dispatch=True  # Default
)

# Bad: synchronous blocks request
NotificationService.send(
    user=user,
    notification_type='order_shipped',
    context={'order_id': '123'},
    async_dispatch=False  # Blocks!
)
```

**Use async=False only when**:
- Testing
- Need immediate feedback (verification codes)
- Critical security alerts

### 2. Use Bulk Send for Multiple Users

```python
# Good: bulk send (one task)
NotificationService.send_bulk(
    users=users,
    notification_type='announcement',
    context_fn=lambda u: {'content': '...'}
)

# Bad: loop with individual sends (N tasks)
for user in users:
    NotificationService.send(user=user, ...)
```

### 3. Limit Context Size

```python
# Good: minimal context
context = {
    'post_id': post.id,
    'post_title': post.title[:100],  # Truncate
}

# Bad: large context (serializes to DB)
context = {
    'post': model_to_dict(post),  # Entire model
    'all_comments': list(post.comments.values()),  # QuerySet
}
```

### 4. Consider Rate Limiting

```python
# For high-frequency notifications, add rate limiting
def notify_on_like(post, liker):
    # Don't spam author with every like
    send_with_rate_limit(
        user=post.author,
        notification_type='post_liked',
        context={'liker': liker.name},
        limit_hours=1  # Max once per hour
    )
```

## Integration Checklist

Before integrating notifications into your app:

- [ ] Notification type defined in `apps/notifications/types.py`
- [ ] Email template created in Django admin
- [ ] Template name matches type config
- [ ] All required context fields provided
- [ ] Error handling implemented (try/except)
- [ ] Using `async_dispatch=True` (unless special case)
- [ ] Tested with `async_dispatch=False` in unit tests
- [ ] Consider user preferences (don't force channels unless critical)
- [ ] Check notification log status if synchronous
- [ ] Document notification in app's README
