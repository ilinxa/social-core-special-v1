"""
Audit Constants
===============
Constants used by the audit logging system.

Note: Action types are defined in models.py as AuditLog.Action.
This file contains other audit-related constants.
"""

# Fields that must be redacted from audit log details/changes
# Re-exported here for external use if needed
REDACTED_FIELDS = frozenset(
    [
        "password",
        "password1",
        "password2",
        "old_password",
        "new_password",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "authorization",
        "cookie",
        "session_id",
        "csrf",
        "credit_card",
        "card_number",
        "cvv",
        "ssn",
        "otp",
        "verification_code",
    ]
)

# Maximum length for various fields
MAX_USER_AGENT_LENGTH = 500
MAX_RESOURCE_REPR_LENGTH = 255
MAX_REQUEST_ID_LENGTH = 36
