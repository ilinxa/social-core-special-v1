# Email Template Management Reference

Complete guide for creating and managing email templates in the notification system.

## Table of Contents

1. [Template Model Structure](#template-model-structure)
2. [Creating Templates](#creating-templates)
3. [Template Syntax](#template-syntax)
4. [Variable Schema](#variable-schema)
5. [Versioning](#versioning)
6. [Best Practices](#best-practices)
7. [Testing Templates](#testing-templates)

## Template Model Structure

Email templates are managed via Django Admin and stored in the `EmailTemplate` model:

```python
class EmailTemplate(models.Model):
    name = CharField(unique for current version)
    subject = CharField(supports {{ variables }})
    html_body = TextField(supports {{ variables }})
    text_body = TextField(auto-generated if empty)
    variables = JSONField(schema for validation)
    description = TextField
    category = CharField(auth, transactional, marketing, system)
    is_active = BooleanField(must be True to use)
    version = PositiveIntegerField(auto-incremented)
    is_current = BooleanField(only one current per name)
```

## Creating Templates

### Via Django Admin

Navigate to `/admin/email/emailtemplate/add/`

**Required Fields**:

1. **Name** (CharField)
   - Unique identifier
   - Must match `email_template` in NotificationTypeConfig
   - Use snake_case (e.g., `password_reset`, `order_shipped`)

2. **Subject** (CharField)
   - Email subject line
   - Supports Django template syntax
   - Example: `Reset your password for {{ app_name }}`

3. **HTML Body** (TextField)
   - HTML content of email
   - Supports Django template syntax
   - Use full HTML structure or snippet

4. **Text Body** (TextField, optional)
   - Plain text version
   - Auto-generated from HTML if left empty
   - Recommended for better deliverability

5. **Variables** (JSONField)
   - Schema defining expected variables
   - Used for validation
   - Format:
     ```json
     {
       "field_name": {
         "type": "string",
         "required": true
       }
     }
     ```

6. **Category** (CharField)
   - `auth` - Authentication templates
   - `transactional` - Business transactions
   - `marketing` - Promotional content
   - `system` - System announcements

7. **Is Active** (BooleanField)
   - Must be `True` for template to be usable
   - Set to `False` to disable without deleting

### Example: Password Reset Template

```
Name: password_reset

Subject: Reset your password

HTML Body:
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Password Reset</title>
</head>
<body>
    <h1>Password Reset Request</h1>
    <p>Hello {{ user_name }},</p>
    <p>You requested to reset your password. Click the button below to proceed:</p>
    <p><a href="{{ reset_link }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
    <p>This link will expire in 24 hours.</p>
    <p>If you didn't request this, please ignore this email.</p>
    <p>Thanks,<br>The Team</p>
</body>
</html>

Text Body: (leave empty for auto-generation)

Variables:
{
  "reset_link": {
    "type": "string",
    "required": true
  }
}

Category: auth
Is Active: ✓ (checked)
```

## Template Syntax

Templates use **Django template engine** syntax.

### Variables

```django
{{ variable_name }}
```

**Examples**:
```django
Hello {{ user_name }}
Your order {{ order_id }} has shipped
Reset link: {{ reset_link }}
```

### Filters

```django
{{ variable|filter }}
```

**Common filters**:
```django
{{ user_name|title }}               {# Title Case #}
{{ order_total|floatformat:2 }}     {# 2 decimal places #}
{{ created_at|date:"M d, Y" }}      {# Format date #}
{{ description|truncatewords:50 }}  {# Truncate #}
```

### Conditionals

```django
{% if condition %}
  Content when true
{% else %}
  Content when false
{% endif %}
```

**Example**:
```django
{% if has_discount %}
  <p>Your discount: {{ discount_amount }}</p>
{% endif %}
```

### Loops

```django
{% for item in items %}
  {{ item.name }}: {{ item.price }}
{% endfor %}
```

**Example**:
```django
<h2>Order Items:</h2>
<ul>
{% for item in order_items %}
  <li>{{ item.name }} - ${{ item.price }}</li>
{% endfor %}
</ul>
```

### Auto-Available Variables

These are automatically added to all templates:

- `user_email` - Recipient's email address
- `user_name` - User's display name from profile

**Usage**:
```django
<p>Hello {{ user_name }},</p>
<p>This email was sent to {{ user_email }}</p>
```

## Variable Schema

Define expected variables in the `variables` JSON field.

### Schema Format

```json
{
  "variable_name": {
    "type": "string",
    "required": true
  }
}
```

### Type Options

- `"string"` - Text value
- `"number"` - Numeric value
- `"boolean"` - True/False
- `"object"` - Nested object
- `"array"` - List of items

### Required Flag

- `"required": true` - Must be provided
- `"required": false` - Optional

### Examples

#### Simple Variables
```json
{
  "reset_link": {
    "type": "string",
    "required": true
  },
  "expires_at": {
    "type": "string",
    "required": false
  }
}
```

#### Multiple Variables
```json
{
  "order_id": {
    "type": "string",
    "required": true
  },
  "order_total": {
    "type": "number",
    "required": true
  },
  "tracking_url": {
    "type": "string",
    "required": true
  },
  "estimated_delivery": {
    "type": "string",
    "required": false
  }
}
```

#### Complex Variables (Objects/Arrays)
```json
{
  "order_items": {
    "type": "array",
    "required": true
  },
  "shipping_address": {
    "type": "object",
    "required": true
  }
}
```

**Template usage**:
```django
{% for item in order_items %}
  <li>{{ item.name }} - ${{ item.price }}</li>
{% endfor %}

<p>
  Shipping to: {{ shipping_address.street }},
  {{ shipping_address.city }}, {{ shipping_address.state }}
</p>
```

## Versioning

Email templates use automatic versioning to preserve history.

### How Versioning Works

1. **Create New Template**:
   - `version = 1`
   - `is_current = True`

2. **Edit Template** (click Save):
   - Old row: `is_current = False`
   - New row: `version = 2`, `is_current = True`

3. **Query Current Template**:
   - System always uses `is_current=True`
   - Old versions preserved for audit

### Version History

View all versions in admin:
```python
from apps.email.selectors import EmailTemplateSelector

history = EmailTemplateSelector.get_version_history('password_reset')
for template in history:
    print(f"Version {template.version}: {template.updated_at}")
```

### Benefits

- **Audit Trail**: See what content was sent historically
- **Rollback**: Copy old version if needed
- **Debug**: Check which version was used for a specific email

### Version in EmailLog

Each sent email records:
```python
email_log.template_name = 'password_reset'
email_log.template_version = 2  # Version used at send time
```

## Best Practices

### 1. HTML Structure

**Use semantic HTML**:
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ subject }}</title>
</head>
<body>
    <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
        <!-- Content here -->
    </div>
</body>
</html>
```

### 2. Inline Styles

Email clients don't support external CSS. Use inline styles:

```html
<!-- Good -->
<p style="color: #333; font-size: 16px; line-height: 1.5;">Content</p>

<!-- Bad -->
<link rel="stylesheet" href="styles.css">
<p class="content">Content</p>
```

### 3. Responsive Design

Use table layouts for better email client compatibility:

```html
<table width="100%" cellpadding="0" cellspacing="0">
    <tr>
        <td style="padding: 20px;">
            <h1 style="margin: 0;">{{ title }}</h1>
        </td>
    </tr>
</table>
```

### 4. Clear Call-to-Action

Make primary action prominent:

```html
<table cellpadding="0" cellspacing="0">
    <tr>
        <td style="background-color: #007bff; border-radius: 5px; text-align: center;">
            <a href="{{ action_link }}" style="color: #ffffff; text-decoration: none; padding: 12px 24px; display: inline-block; font-weight: bold;">
                {{ action_text }}
            </a>
        </td>
    </tr>
</table>
```

### 5. Fallback Text Links

Always provide plain text link as fallback:

```html
<p>
    <a href="{{ reset_link }}" style="...">Reset Password</a>
</p>
<p style="font-size: 12px; color: #666;">
    Or copy this link: {{ reset_link }}
</p>
```

### 6. Branding Consistency

Use consistent colors, fonts, and layout:

```html
<!-- Define brand colors -->
{% comment %}
  Primary: #007bff
  Text: #333333
  Light: #f8f9fa
{% endcomment %}

<body style="background-color: #f8f9fa; font-family: Arial, sans-serif;">
    <!-- Content with consistent styling -->
</body>
```

### 7. Unsubscribe Links (Marketing)

Marketing emails must include unsubscribe:

```html
<p style="font-size: 12px; color: #666; text-align: center;">
    Don't want these emails?
    <a href="{{ unsubscribe_link }}">Unsubscribe</a>
</p>
```

### 8. Plain Text Version

Provide plain text for better deliverability:

**Auto-generated** (leave text_body empty):
```
System auto-converts:
<h1>Hello</h1> → Hello
<a href="...">Click</a> → Click: [URL]
```

**Manual** (recommended for important emails):
```
Hello {{ user_name }},

You requested to reset your password. Click the link below:

{{ reset_link }}

This link expires in 24 hours.

Thanks,
The Team
```

### 9. Testing Variables

Include all required variables in schema:

```json
{
  "order_id": {"type": "string", "required": true},
  "items": {"type": "array", "required": true},
  "total": {"type": "number", "required": true}
}
```

Validation will fail if context missing these fields.

### 10. Descriptive Names

Use clear, descriptive names:

```
Good:
- password_reset
- order_shipped
- subscription_expiring

Bad:
- email1
- template_new
- user_notification
```

## Testing Templates

### 1. Admin Preview

Django admin shows rendered preview (if configured).

### 2. Manual Test Send

```python
from apps.email.services import EmailService

EmailService.send(
    template_name='password_reset',
    to_email='test@example.com',
    context={
        'reset_link': 'https://example.com/reset?token=test',
    },
    async_send=False  # Synchronous for testing
)
```

### 3. Unit Tests

```python
from apps.email.services import EmailService
from apps.email.selectors import EmailLogSelector

def test_password_reset_template():
    log = EmailService.send(
        template_name='password_reset',
        to_email='test@example.com',
        context={'reset_link': 'https://example.com/reset'},
        async_send=False
    )

    assert log.status == 'SENT'
    assert 'Reset Password' in log.subject
    assert 'https://example.com/reset' in log.html_body
```

### 4. Visual Testing

Send to real email and check:
- [ ] Subject renders correctly
- [ ] HTML displays properly in Gmail/Outlook
- [ ] Links are clickable
- [ ] Images load (if any)
- [ ] Text version is readable
- [ ] Mobile responsive

### 5. Variable Validation Testing

```python
# Should succeed
EmailService.send(
    template_name='password_reset',
    to_email='test@example.com',
    context={'reset_link': 'https://...'}  # All required variables
)

# Should fail with ValidationError
EmailService.send(
    template_name='password_reset',
    to_email='test@example.com',
    context={}  # Missing required 'reset_link'
)
```

## Common Template Patterns

### 1. Simple Notification

```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1>{{ title }}</h1>
    <p>Hello {{ user_name }},</p>
    <p>{{ message }}</p>
    <p>Thanks,<br>The Team</p>
</body>
</html>
```

### 2. Action Required

```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1>{{ title }}</h1>
    <p>Hello {{ user_name }},</p>
    <p>{{ description }}</p>

    <table cellpadding="0" cellspacing="0" style="margin: 20px 0;">
        <tr>
            <td style="background-color: #007bff; border-radius: 5px; text-align: center;">
                <a href="{{ action_link }}" style="color: #ffffff; text-decoration: none; padding: 12px 24px; display: inline-block; font-weight: bold;">
                    {{ action_text }}
                </a>
            </td>
        </tr>
    </table>

    <p style="font-size: 12px; color: #666;">
        Or copy this link: {{ action_link }}
    </p>
</body>
</html>
```

### 3. Transactional Confirmation

```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1>{{ title }}</h1>
    <p>Hello {{ user_name }},</p>
    <p>{{ confirmation_message }}</p>

    <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
        <tr style="background-color: #f8f9fa;">
            <th style="text-align: left; padding: 10px; border-bottom: 2px solid #dee2e6;">Item</th>
            <th style="text-align: right; padding: 10px; border-bottom: 2px solid #dee2e6;">Amount</th>
        </tr>
        {% for item in items %}
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #dee2e6;">{{ item.name }}</td>
            <td style="text-align: right; padding: 10px; border-bottom: 1px solid #dee2e6;">${{ item.price }}</td>
        </tr>
        {% endfor %}
        <tr style="font-weight: bold;">
            <td style="padding: 10px;">Total</td>
            <td style="text-align: right; padding: 10px;">${{ total }}</td>
        </tr>
    </table>

    <p>Transaction ID: {{ transaction_id }}</p>
</body>
</html>
```

### 4. Multi-Action Template

```html
<!DOCTYPE html>
<html>
<body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
    <h1>{{ title }}</h1>
    <p>Hello {{ user_name }},</p>
    <p>{{ message }}</p>

    <div style="margin: 20px 0;">
        <a href="{{ primary_action_link }}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block; margin-right: 10px;">
            {{ primary_action_text }}
        </a>
        <a href="{{ secondary_action_link }}" style="background-color: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
            {{ secondary_action_text }}
        </a>
    </div>
</body>
</html>
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Template not found | Check `name` matches exactly (case-sensitive) |
| Variables not rendering | Check context includes variable, verify spelling |
| HTML not displaying | Check email client compatibility, use inline styles |
| Validation error | Verify all required variables in context dict |
| Old template version used | Check `is_current=True` for latest version |
| Text body missing | Leave blank for auto-generation or provide manually |

## Template Checklist

Before deploying a template:

- [ ] Name matches NotificationTypeConfig.email_template
- [ ] Subject is clear and concise
- [ ] HTML body uses inline styles
- [ ] All variables are in {{ double_braces }}
- [ ] Variables schema includes all required fields
- [ ] Links are absolute URLs (https://...)
- [ ] Call-to-action is prominent
- [ ] Plain text fallback link provided
- [ ] Category is appropriate
- [ ] is_active = True
- [ ] Tested in Gmail and Outlook
- [ ] Mobile responsive
- [ ] Unsubscribe link (for marketing)
