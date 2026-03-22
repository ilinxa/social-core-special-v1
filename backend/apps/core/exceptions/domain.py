"""
Domain Exceptions
=================
Business/domain layer exceptions for consistent error handling.

These exceptions represent domain-level errors (not HTTP or framework errors).
They are caught by the exception handler and converted to appropriate HTTP responses.

Design Principles:
    - Each exception has a semantic code (not HTTP status)
    - HTTP status mapping happens in the handler, not here
    - All exceptions inherit from DomainException
    - Exceptions carry structured context for debugging

Usage:
    from apps.core.exceptions import NotFound, ValidationError

    def get_product(product_id: int):
        product = Product.objects.filter(id=product_id).first()
        if not product:
            raise NotFound(
                message="Product not found",
                resource="Product",
                resource_id=product_id
            )
        return product
"""

from typing import Any


class DomainException(Exception):
    """
    Base exception for all domain/business logic errors.

    All custom exceptions should inherit from this class.
    This allows unified exception handling at the API layer.

    Attributes:
        message: Human-readable error message
        code: Machine-readable error code (e.g., "not_found", "validation_error")
        details: Additional context as a dictionary

    Example:
        raise DomainException(
            message="Cannot process order",
            code="order_processing_failed",
            details={"order_id": 123, "reason": "insufficient_stock"}
        )
    """

    default_message = "A domain error occurred"
    default_code = "domain_error"

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        details: dict | None = None,
    ):
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict:
        """
        Convert exception to dictionary for API response.

        Returns:
            Dictionary with message, code, and details
        """
        return {
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }

    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} - {self.details}"
        return f"[{self.code}] {self.message}"


# =============================================================================
# NOT FOUND EXCEPTIONS
# =============================================================================


class NotFound(DomainException):
    """
    Raised when a requested resource does not exist.

    Maps to HTTP 404 in the exception handler.

    Attributes:
        resource: Type of resource that wasn't found (e.g., "User", "Product")
        resource_id: ID that was searched for

    Example:
        raise NotFound(
            message="User not found",
            resource="User",
            resource_id=456
        )
    """

    default_message = "Resource not found"
    default_code = "not_found"

    def __init__(
        self,
        message: str | None = None,
        resource: str | None = None,
        resource_id: Any | None = None,
    ):
        details = {}
        if resource:
            details["resource"] = resource
        if resource_id is not None:
            details["resource_id"] = str(resource_id)

        super().__init__(
            message=message
            or (f"{resource} not found" if resource else self.default_message),
            code=self.default_code,
            details=details,
        )


# =============================================================================
# PERMISSION EXCEPTIONS
# =============================================================================


class PermissionDenied(DomainException):
    """
    Raised when user lacks permission for an operation.

    Maps to HTTP 403 in the exception handler.

    Attributes:
        action: The action that was denied (e.g., "delete", "update")
        resource: The resource type involved

    Example:
        raise PermissionDenied(
            message="You cannot delete this organization",
            action="delete",
            resource="Organization"
        )
    """

    default_message = "Permission denied"
    default_code = "permission_denied"

    def __init__(
        self,
        message: str | None = None,
        action: str | None = None,
        resource: str | None = None,
    ):
        details = {}
        if action:
            details["action"] = action
        if resource:
            details["resource"] = resource

        super().__init__(message=message, code=self.default_code, details=details)


# =============================================================================
# VALIDATION EXCEPTIONS
# =============================================================================


class ValidationError(DomainException):
    """
    Raised when domain validation fails.

    Maps to HTTP 400 in the exception handler.
    Use this for business rule validation, not input format validation
    (DRF serializers handle input validation).

    Attributes:
        field: The field that failed validation (if applicable)
        value: The invalid value (if safe to include)

    Example:
        raise ValidationError(
            message="Email domain not allowed for enterprise accounts",
            field="email",
            value="user@gmail.com"
        )
    """

    default_message = "Validation failed"
    default_code = "validation_error"

    def __init__(
        self,
        message: str | None = None,
        field: str | None = None,
        value: Any | None = None,
    ):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = str(value)

        super().__init__(message=message, code=self.default_code, details=details)


# =============================================================================
# CONFLICT EXCEPTIONS
# =============================================================================


class ConflictError(DomainException):
    """
    Raised when operation conflicts with current state.

    Maps to HTTP 409 in the exception handler.
    Use for duplicate entries, concurrent modification conflicts, etc.

    Attributes:
        resource: The resource type with the conflict
        conflict_type: Type of conflict (e.g., "duplicate", "state_conflict")

    Example:
        raise ConflictError(
            message="User with this email already exists",
            resource="User",
            conflict_type="duplicate"
        )
    """

    default_message = "Resource conflict"
    default_code = "conflict"

    def __init__(
        self,
        message: str | None = None,
        resource: str | None = None,
        conflict_type: str | None = None,
    ):
        details = {}
        if resource:
            details["resource"] = resource
        if conflict_type:
            details["conflict_type"] = conflict_type

        super().__init__(message=message, code=self.default_code, details=details)


# =============================================================================
# AUTHENTICATION EXCEPTIONS
# =============================================================================


class AuthenticationError(DomainException):
    """
    Raised when authentication fails or is required.

    Maps to HTTP 401 in the exception handler.

    Example:
        raise AuthenticationError(
            message="Invalid or expired token"
        )
    """

    default_message = "Authentication required"
    default_code = "authentication_error"


class InvalidCredentials(AuthenticationError):
    """
    Raised specifically when login credentials are invalid.

    Maps to HTTP 401 in the exception handler.

    Note:
        For security, avoid revealing whether email or password was wrong.
    """

    default_message = "Invalid email or password"
    default_code = "invalid_credentials"


class TokenExpired(AuthenticationError):
    """
    Raised when an authentication token has expired.

    Maps to HTTP 401 in the exception handler.
    """

    default_message = "Token has expired"
    default_code = "token_expired"


class TokenInvalid(AuthenticationError):
    """
    Raised when an authentication token is malformed or invalid.

    Maps to HTTP 401 in the exception handler.
    """

    default_message = "Invalid token"
    default_code = "token_invalid"


# =============================================================================
# BUSINESS LOGIC EXCEPTIONS
# =============================================================================


class BusinessRuleViolation(DomainException):
    """
    Raised when a business rule is violated.

    Maps to HTTP 400 in the exception handler.
    Use for domain-specific rules that don't fit other categories.

    Attributes:
        rule: The rule that was violated

    Example:
        raise BusinessRuleViolation(
            message="Cannot cancel order after shipping",
            rule="order_cancellation_policy"
        )
    """

    default_message = "Business rule violation"
    default_code = "business_rule_violation"

    def __init__(self, message: str | None = None, rule: str | None = None):
        details = {}
        if rule:
            details["rule"] = rule

        super().__init__(message=message, code=self.default_code, details=details)


class RateLimitExceeded(DomainException):
    """
    Raised when rate limit is exceeded at domain level.

    Maps to HTTP 429 in the exception handler.

    Note:
        Use this for domain-level rate limits (e.g., max password reset attempts).
        HTTP-level rate limiting is handled by DRF throttling.

    Attributes:
        retry_after: Seconds until the action can be retried
    """

    default_message = "Rate limit exceeded"
    default_code = "rate_limit_exceeded"

    def __init__(self, message: str | None = None, retry_after: int | None = None):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(message=message, code=self.default_code, details=details)


class ServiceUnavailable(DomainException):
    """
    Raised when a required service is temporarily unavailable.

    Maps to HTTP 503 in the exception handler.
    Use when external services (email, payment, etc.) are down.

    Attributes:
        service: Name of the unavailable service
        retry_after: Suggested retry time in seconds
    """

    default_message = "Service temporarily unavailable"
    default_code = "service_unavailable"

    def __init__(
        self,
        message: str | None = None,
        service: str | None = None,
        retry_after: int | None = None,
    ):
        details = {}
        if service:
            details["service"] = service
        if retry_after:
            details["retry_after"] = retry_after

        super().__init__(message=message, code=self.default_code, details=details)


# =============================================================================
# ADDITIONAL AUTHENTICATION EXCEPTIONS
# =============================================================================


class AccountNotVerified(AuthenticationError):
    """
    Raised when user tries to access resource requiring verified email.

    Maps to HTTP 401 in the exception handler.
    """

    default_message = "Email verification required"
    default_code = "account_not_verified"


class AccountInactive(AuthenticationError):
    """
    Raised when an inactive user tries to authenticate.

    Maps to HTTP 401 in the exception handler.
    """

    default_message = "Account is inactive"
    default_code = "account_inactive"


class AccountLocked(AuthenticationError):
    """
    Raised when a locked user tries to authenticate.

    Maps to HTTP 401 in the exception handler.
    Account is locked after too many failed login attempts.
    """

    default_message = "Account temporarily locked due to too many failed attempts"
    default_code = "account_locked"


class SessionLimitExceeded(BusinessRuleViolation):
    """
    Raised when user exceeds maximum allowed sessions.

    Maps to HTTP 400 in the exception handler.
    """

    default_message = "Maximum session limit exceeded"
    default_code = "session_limit_exceeded"


class TokenAlreadyUsed(TokenInvalid):
    """
    Raised when a one-time token has already been used.

    Maps to HTTP 401 in the exception handler.
    Used for refresh tokens, verification tokens, etc.
    """

    default_message = "Token has already been used"
    default_code = "token_already_used"


class OAuthError(DomainException):
    """
    Raised when OAuth authentication fails.

    Maps to HTTP 400 in the exception handler.

    Attributes:
        provider: OAuth provider name (e.g., 'google', 'apple')
        oauth_error: Error code from provider
    """

    default_message = "OAuth authentication failed"
    default_code = "oauth_error"

    def __init__(
        self,
        message: str | None = None,
        provider: str | None = None,
        oauth_error: str | None = None,
    ):
        details = {}
        if provider:
            details["provider"] = provider
        if oauth_error:
            details["oauth_error"] = oauth_error

        super().__init__(message=message, code=self.default_code, details=details)
