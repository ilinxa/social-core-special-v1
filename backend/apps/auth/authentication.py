"""
JWT Authentication
==================
DRF authentication class for JWT-based authentication.

Usage:
    Configure in settings.py:
        REST_FRAMEWORK = {
            'DEFAULT_AUTHENTICATION_CLASSES': [
                'apps.auth.authentication.JWTAuthentication',
            ],
        }

    Or per-view:
        class MyView(APIView):
            authentication_classes = [JWTAuthentication]

Token Format:
    Authorization: Bearer <access_token>
"""

from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.core.observability import get_logger

# Note: Import exceptions inside methods to avoid circular import during app loading

logger = get_logger(__name__)


class JWTAuthentication(BaseAuthentication):
    """
    JWT authentication for Django REST Framework.

    Extracts and validates JWT from Authorization header.
    Returns (user, payload) tuple on success.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        """
        Authenticate the request and return (user, payload) or None.

        Args:
            request: DRF Request object

        Returns:
            Tuple of (user, payload) if authenticated, None if no auth header

        Raises:
            AuthenticationFailed: If token is invalid or expired
        """
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header:
            return None

        # Check for Bearer prefix
        parts = auth_header.split()

        if len(parts) == 0:
            return None

        if parts[0].lower() != self.keyword.lower():
            return None

        if len(parts) == 1:
            raise AuthenticationFailed("Invalid token header. No credentials provided.")

        if len(parts) > 2:
            raise AuthenticationFailed(
                "Invalid token header. Token string should not contain spaces."
            )

        token = parts[1]

        try:
            from apps.auth.services import AuthService
            from apps.core.exceptions import TokenExpired, TokenInvalid

            user, payload = AuthService.validate_access_token(token)

            # Log successful auth (debug level)
            logger.debug("auth.jwt.success", extra={"user_id": user.id})

            return (user, payload)

        except AuthenticationFailed:
            raise

        except Exception as e:
            # Import here to check exception types
            from apps.core.exceptions import (
                ServiceUnavailable,
                TokenAlreadyUsed,
                TokenExpired,
                TokenInvalid,
            )

            if isinstance(e, TokenExpired):
                raise AuthenticationFailed(
                    detail="Token has expired", code="token_expired"
                )
            elif isinstance(e, TokenAlreadyUsed):
                raise AuthenticationFailed(
                    detail=str(e) or "Token has already been used",
                    code="token_already_used",
                )
            elif isinstance(e, TokenInvalid):
                raise AuthenticationFailed(
                    detail=str(e) or "Invalid token", code="token_invalid"
                )
            elif isinstance(e, ServiceUnavailable):
                raise AuthenticationFailed(
                    detail="Service temporarily unavailable. Please try again.",
                    code="service_unavailable",
                )
            else:
                logger.error(f"JWT authentication error: {e}")
                raise AuthenticationFailed("Authentication failed")

    def authenticate_header(self, request):
        """
        Return string to be used as the value of the WWW-Authenticate
        header in a 401 response.
        """
        return self.keyword


class JWTAuthenticationOptional(JWTAuthentication):
    """
    Optional JWT authentication.

    Same as JWTAuthentication but returns None instead of raising
    AuthenticationFailed when token is invalid/expired.

    Use for endpoints that support both authenticated and anonymous access.

    Usage:
        class MyView(APIView):
            authentication_classes = [JWTAuthenticationOptional]
            permission_classes = [AllowAny]
    """

    def authenticate(self, request):
        """
        Authenticate or return None (never raises AuthenticationFailed).
        """
        try:
            return super().authenticate(request)
        except AuthenticationFailed:
            return None
