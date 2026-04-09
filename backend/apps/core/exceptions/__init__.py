"""
Core Exceptions
===============
Re-exports all domain exceptions for convenient importing.

Usage:
    from apps.core.exceptions import NotFound, ValidationError, PermissionDenied

Exception Hierarchy:
    DomainException (base)
    ├── NotFound (404)
    ├── PermissionDenied (403)
    ├── FeatureDisabled (403)
    ├── ValidationError (400)
    ├── ConflictError (409)
    ├── AuthenticationError (401)
    │   ├── InvalidCredentials
    │   ├── TokenExpired
    │   ├── TokenInvalid
    │   │   └── TokenAlreadyUsed
    │   ├── AccountNotVerified
    │   ├── AccountInactive
    │   └── AccountLocked
    ├── BusinessRuleViolation (400)
    │   └── SessionLimitExceeded
    ├── RateLimitExceeded (429)
    ├── ServiceUnavailable (503)
    └── OAuthError (400)
"""

from apps.core.exceptions.domain import (  # Base exception; Resource exceptions; Authentication exceptions; Business logic exceptions; OAuth exceptions
    AccountInactive,
    AccountLocked,
    AccountNotVerified,
    AuthenticationError,
    BusinessRuleViolation,
    ConflictError,
    DomainException,
    FeatureDisabled,
    InvalidCredentials,
    NotFound,
    OAuthError,
    PermissionDenied,
    RateLimitExceeded,
    ServiceUnavailable,
    SessionLimitExceeded,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    ValidationError,
)
from apps.core.exceptions.handler import exception_handler, get_status_code

__all__ = [
    # Base exception
    "DomainException",
    # Resource exceptions
    "NotFound",
    "PermissionDenied",
    "ValidationError",
    "ConflictError",
    # Feature gate exceptions
    "FeatureDisabled",
    # Authentication exceptions
    "AuthenticationError",
    "InvalidCredentials",
    "TokenExpired",
    "TokenInvalid",
    "TokenAlreadyUsed",
    "AccountNotVerified",
    "AccountInactive",
    "AccountLocked",
    # Business logic exceptions
    "BusinessRuleViolation",
    "SessionLimitExceeded",
    "RateLimitExceeded",
    "ServiceUnavailable",
    # OAuth exceptions
    "OAuthError",
    # Handler
    "exception_handler",
    "get_status_code",
]
