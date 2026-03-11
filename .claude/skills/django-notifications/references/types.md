# Notification Type Configuration Reference

Complete guide for defining notification types in `apps/notifications/types.py`.

## Table of Contents

1. [NotificationTypeConfig Structure](#notificationtypeconfig-structure)
2. [Configuration Fields](#configuration-fields)
3. [Categories](#categories)
4. [Channels](#channels)
5. [Examples by Use Case](#examples-by-use-case)
6. [Best Practices](#best-practices)

## NotificationTypeConfig Structure

```python
from dataclasses import dataclass
from typing import List, Optional
from apps.notifications.enums import Category, Channel

@dataclass
class NotificationTypeConfig:
    name: str
    display_name: str
    description: str
    category: Category
    default_channels: List[Channel]
    required_context: List[str]
    email_template: Optional[str]
    push_template: Optional[str]
    sms_template: Optional[str]
    user_configurable: bool
    enabled: bool
```

## Configuration Fields

### name (str, required)
Unique identifier for the notification type.

**Rules**:
- Use snake_case
- Be descriptive and specific
- Should match the purpose (e.g., `password_reset`, `order_shipped`)

**Examples**:
```python
name='welcome'
name='password_reset'
name='order_shipped'
name='comment_reply'
```

### display_name (str, required)
Human-readable name shown to users in preferences UI.

**Rules**:
- Use Title Case
- Keep concise (2-4 words)
- Clear and user-friendly

**Examples**:
```python
display_name='Welcome Email'
display_name='Password Reset'
display_name='Order Shipped'
display_name='Comment Reply'
```

### description (str, required)
Explanation shown to users in preferences UI.

**Rules**:
- One sentence describing when notification is sent
- User perspective ("when you...", "notification when...")
- Include relevant context

**Examples**:
```python
description='Sent when you first register an account'
description='Notification when you request to reset your password'
description='Sent when your order ships with tracking information'
description='Notification when someone replies to your comment'
```

### category (Category, required)
Classification for grouping in preferences UI.

**Options**:
```python
Category.AUTH         # Authentication and registration
Category.SECURITY     # Security alerts and warnings
Category.TRANSACTIONAL # Business transactions
Category.MARKETING    # Promotional content
Category.SYSTEM       # System announcements
```

**See**: [Categories](#categories) section for details

### default_channels (List[Channel], required)
Channels enabled by default for this notification.

**Options**:
```python
Channel.EMAIL  # Email notifications (implemented)
Channel.PUSH   # Push notifications (placeholder)
Channel.SMS    # SMS notifications (placeholder)
```

**Examples**:
```python
default_channels=[Channel.EMAIL]
default_channels=[Channel.EMAIL, Channel.PUSH]
default_channels=[Channel.EMAIL, Channel.PUSH, Channel.SMS]
```

**User Override**: Users can enable/disable individual channels via preferences (unless `user_configurable=False`)

### required_context (List[str], required)
Template variables that must be provided when sending.

**Rules**:
- List field names required in `context` dict
- Validation happens before sending
- Empty list `[]` if no required fields

**Examples**:
```python
required_context=[]  # No required fields
required_context=['reset_link']
required_context=['order_id', 'tracking_url']
required_context=['comment_author', 'comment_text', 'post_url']
```

**Note**: Standard fields (`user_email`, `user_name`) are auto-added, don't include them.

### email_template (Optional[str], optional)
Name of EmailTemplate to use for email channel.

**Rules**:
- Must match `EmailTemplate.name` in database
- Required if `Channel.EMAIL` in `default_channels`
- Set to `None` if email not used

**Examples**:
```python
email_template='welcome'
email_template='password_reset'
email_template=None  # No email template
```

### push_template (Optional[str], optional)
Name of push template (not implemented yet).

**Current Usage**:
```python
push_template=None  # Always None until push channel implemented
```

### sms_template (Optional[str], optional)
Name of SMS template (not implemented yet).

**Current Usage**:
```python
sms_template=None  # Always None until SMS channel implemented
```

### user_configurable (bool, required)
Whether user can disable this notification type.

**Values**:
- `True` - User can toggle channels in preferences (newsletters, marketing, optional updates)
- `False` - Mandatory notification, cannot be disabled (security alerts, authentication, critical system)

**Examples**:
```python
user_configurable=True   # Marketing, newsletters, optional notifications
user_configurable=False  # Security alerts, password resets, verification
```

**Mandatory Types** (current):
- `verify_email`
- `welcome`
- `password_reset`
- `password_changed`
- `suspicious_activity`

### enabled (bool, required)
Whether notification type is active.

**Values**:
- `True` - Type is active and can be used
- `False` - Type is disabled, sends will fail

**Usage**:
```python
enabled=True   # Normal state
enabled=False  # Temporarily disable type without removing code
```

**Use Case**: Feature flags, A/B testing, gradual rollout

## Categories

### Category.AUTH
Authentication and registration events.

**When to Use**:
- User registration
- Email verification
- Login confirmations
- Account activation

**Examples**:
```python
'welcome': NotificationTypeConfig(
    name='welcome',
    category=Category.AUTH,
    user_configurable=False,  # Usually mandatory
    ...
)

'verify_email': NotificationTypeConfig(
    name='verify_email',
    category=Category.AUTH,
    user_configurable=False,  # Must be mandatory
    ...
)
```

### Category.SECURITY
Security alerts and warnings.

**When to Use**:
- Password changes
- Suspicious login attempts
- Account security changes
- Two-factor authentication

**Examples**:
```python
'password_changed': NotificationTypeConfig(
    name='password_changed',
    category=Category.SECURITY,
    user_configurable=False,  # Security alerts should be mandatory
    ...
)

'suspicious_activity': NotificationTypeConfig(
    name='suspicious_activity',
    category=Category.SECURITY,
    user_configurable=False,  # Critical security
    force_channels=['email', 'push'],  # Use with force_channels in service
    ...
)
```

### Category.TRANSACTIONAL
Business transactions and confirmations.

**When to Use**:
- Order confirmations
- Payment receipts
- Shipping updates
- Booking confirmations
- Subscription changes

**Examples**:
```python
'order_shipped': NotificationTypeConfig(
    name='order_shipped',
    category=Category.TRANSACTIONAL,
    user_configurable=True,  # Users may want to disable shipping updates
    required_context=['order_id', 'tracking_url'],
    ...
)

'payment_received': NotificationTypeConfig(
    name='payment_received',
    category=Category.TRANSACTIONAL,
    user_configurable=False,  # Financial confirmations should be mandatory
    required_context=['amount', 'transaction_id'],
    ...
)
```

### Category.MARKETING
Promotional content and newsletters.

**When to Use**:
- Newsletters
- Promotional offers
- Product announcements
- Marketing campaigns

**Examples**:
```python
'newsletter': NotificationTypeConfig(
    name='newsletter',
    category=Category.MARKETING,
    user_configurable=True,  # MUST be configurable for marketing
    default_channels=[Channel.EMAIL],
    ...
)

'promotions': NotificationTypeConfig(
    name='promotions',
    category=Category.MARKETING,
    user_configurable=True,  # MUST be configurable
    ...
)
```

**Legal Note**: Marketing notifications MUST be `user_configurable=True` for GDPR/CAN-SPAM compliance.

### Category.SYSTEM
System announcements and updates.

**When to Use**:
- Maintenance notifications
- System updates
- Feature announcements
- Service disruptions

**Examples**:
```python
'maintenance_scheduled': NotificationTypeConfig(
    name='maintenance_scheduled',
    category=Category.SYSTEM,
    user_configurable=True,  # Users may not want system updates
    ...
)
```

## Examples by Use Case

### Authentication Flow

```python
NOTIFICATION_TYPES = {
    'verify_email': NotificationTypeConfig(
        name='verify_email',
        display_name='Email Verification',
        description='Sent when you register to verify your email address',
        category=Category.AUTH,
        default_channels=[Channel.EMAIL],
        required_context=['verification_link', 'verification_code'],
        email_template='verify_email',
        push_template=None,
        sms_template=None,
        user_configurable=False,  # Mandatory
        enabled=True,
    ),

    'welcome': NotificationTypeConfig(
        name='welcome',
        display_name='Welcome Email',
        description='Sent after you verify your email address',
        category=Category.AUTH,
        default_channels=[Channel.EMAIL],
        required_context=[],  # No extra context needed
        email_template='welcome',
        push_template=None,
        sms_template=None,
        user_configurable=False,  # Mandatory
        enabled=True,
    ),
}
```

### E-commerce Notifications

```python
NOTIFICATION_TYPES = {
    'order_confirmed': NotificationTypeConfig(
        name='order_confirmed',
        display_name='Order Confirmation',
        description='Sent when your order is confirmed',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL],
        required_context=['order_id', 'order_total', 'items'],
        email_template='order_confirmed',
        push_template=None,
        sms_template=None,
        user_configurable=False,  # Financial confirmation
        enabled=True,
    ),

    'order_shipped': NotificationTypeConfig(
        name='order_shipped',
        display_name='Order Shipped',
        description='Notification when your order ships with tracking',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=['order_id', 'tracking_url', 'carrier'],
        email_template='order_shipped',
        push_template=None,
        sms_template=None,
        user_configurable=True,  # User may disable shipping updates
        enabled=True,
    ),

    'order_delivered': NotificationTypeConfig(
        name='order_delivered',
        display_name='Order Delivered',
        description='Notification when your order is delivered',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=['order_id'],
        email_template='order_delivered',
        push_template=None,
        sms_template=None,
        user_configurable=True,
        enabled=True,
    ),
}
```

### Social Features

```python
NOTIFICATION_TYPES = {
    'comment_reply': NotificationTypeConfig(
        name='comment_reply',
        display_name='Comment Replies',
        description='Notification when someone replies to your comment',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL, Channel.PUSH],
        required_context=['post_title', 'comment_author', 'comment_text', 'post_url'],
        email_template='comment_reply',
        push_template=None,
        sms_template=None,
        user_configurable=True,
        enabled=True,
    ),

    'friend_request': NotificationTypeConfig(
        name='friend_request',
        display_name='Friend Requests',
        description='Notification when someone sends you a friend request',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.PUSH],  # Push only by default
        required_context=['requester_name', 'requester_profile_url'],
        email_template='friend_request',
        push_template=None,
        sms_template=None,
        user_configurable=True,
        enabled=True,
    ),

    'post_liked': NotificationTypeConfig(
        name='post_liked',
        display_name='Post Likes',
        description='Notification when someone likes your post',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.PUSH],  # Low priority, push only
        required_context=['liker_name', 'post_title', 'post_url'],
        email_template='post_liked',
        push_template=None,
        sms_template=None,
        user_configurable=True,
        enabled=True,
    ),
}
```

### Subscription Management

```python
NOTIFICATION_TYPES = {
    'subscription_expiring': NotificationTypeConfig(
        name='subscription_expiring',
        display_name='Subscription Expiring',
        description='Notification when your subscription is about to expire',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL],
        required_context=['expiry_date', 'renewal_url', 'plan_name'],
        email_template='subscription_expiring',
        push_template=None,
        sms_template=None,
        user_configurable=False,  # Financial/account management
        enabled=True,
    ),

    'subscription_renewed': NotificationTypeConfig(
        name='subscription_renewed',
        display_name='Subscription Renewed',
        description='Confirmation when your subscription renews',
        category=Category.TRANSACTIONAL,
        default_channels=[Channel.EMAIL],
        required_context=['next_billing_date', 'amount', 'plan_name'],
        email_template='subscription_renewed',
        push_template=None,
        sms_template=None,
        user_configurable=False,  # Financial confirmation
        enabled=True,
    ),
}
```

## Best Practices

### 1. Naming Conventions

**Use descriptive, action-based names**:
```python
# Good
'password_reset'
'order_shipped'
'comment_reply'

# Bad
'notification1'
'user_email'
'update'
```

### 2. Required Context

**Only require what's truly necessary**:
```python
# Good - specific requirements
required_context=['reset_link']

# Bad - over-specifying
required_context=['user_id', 'user_email', 'user_name', 'reset_link']
# (user_email and user_name are auto-added)
```

### 3. User Configurability

**Make it configurable unless mandatory**:
```python
# Mandatory (security, legal, financial)
user_configurable=False  # password_reset, verify_email, payment_received

# Optional (everything else)
user_configurable=True   # newsletters, shipping updates, social notifications
```

### 4. Default Channels

**Choose appropriate defaults**:
```python
# High priority, important
default_channels=[Channel.EMAIL]

# Medium priority, timely
default_channels=[Channel.PUSH]

# High priority, urgent
default_channels=[Channel.EMAIL, Channel.PUSH]

# Low priority, social
default_channels=[Channel.PUSH]  # Email would be too noisy
```

### 5. Categories

**Use appropriate category**:
```python
# Clear categorization helps users find preferences
Category.AUTH          # Registration, login, verification
Category.SECURITY      # Alerts, warnings, suspicious activity
Category.TRANSACTIONAL # Orders, payments, bookings
Category.MARKETING     # Newsletters, promotions
Category.SYSTEM        # Maintenance, updates
```

### 6. Template Naming

**Match template name to notification type**:
```python
# Good - names match
name='order_shipped'
email_template='order_shipped'

# Acceptable - descriptive variation
name='subscription_expiring'
email_template='subscription_expiring_reminder'

# Bad - unrelated names
name='order_shipped'
email_template='email_template_1'
```

### 7. Enabling/Disabling Types

**Use `enabled` flag for temporary disabling**:
```python
# Good - temporarily disable without removing code
'beta_feature_notification': NotificationTypeConfig(
    name='beta_feature_notification',
    enabled=False,  # Will re-enable when beta ends
    ...
)

# Bad - commenting out entire config
# 'beta_feature_notification': NotificationTypeConfig(...)
```

### 8. Multi-Channel Strategy

**Start with email, add channels later**:
```python
# Initial implementation
default_channels=[Channel.EMAIL]

# Later, when push is implemented
default_channels=[Channel.EMAIL, Channel.PUSH]

# Eventually, for critical notifications
default_channels=[Channel.EMAIL, Channel.PUSH, Channel.SMS]
```

## Validation Checklist

Before adding a new notification type, verify:

- [ ] `name` is unique and descriptive (snake_case)
- [ ] `display_name` is user-friendly (Title Case)
- [ ] `description` explains when notification is sent
- [ ] `category` is appropriate for the use case
- [ ] `default_channels` includes at least one channel
- [ ] `required_context` lists only truly required fields
- [ ] `email_template` matches template name in admin (if using email)
- [ ] `user_configurable` is `False` only for mandatory notifications
- [ ] `enabled` is `True` unless intentionally disabled
- [ ] Email template exists in admin with matching name
- [ ] Template variables match `required_context` fields
