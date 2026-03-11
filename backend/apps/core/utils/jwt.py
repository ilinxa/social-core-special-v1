"""
JWT Utilities
=============
JSON Web Token encoding and decoding utilities.

This module provides a thin wrapper around PyJWT with sensible defaults
and integration with Django settings.

Security Notes:
    - Uses HS256 algorithm (symmetric) by default
    - For production with multiple services, consider RS256 (asymmetric)
    - Tokens are NOT encrypted, only signed - don't put secrets in payload
    - Always validate tokens on the server, never trust client-side validation

Dependencies:
    pip install PyJWT

Configuration:
    Uses settings.SECRET_KEY for signing by default.
    Override by passing a custom secret to functions.

Usage:
    from apps.core.utils.jwt import encode_token, decode_token

    # Create token
    token = encode_token(
        payload={"user_id": 123, "type": "access"},
        expires_in=900  # 15 minutes
    )

    # Decode and validate
    try:
        payload = decode_token(token)
        user_id = payload["user_id"]
    except TokenExpired:
        # Handle expired token
    except TokenInvalid:
        # Handle invalid token
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from django.conf import settings

from apps.core.exceptions import TokenExpired, TokenInvalid


# =============================================================================
# CONFIGURATION
# =============================================================================

# Default algorithm - HS256 is secure for single-service applications
DEFAULT_ALGORITHM = "HS256"

# Algorithms we accept when decoding (prevent algorithm confusion attacks)
ALLOWED_ALGORITHMS = ["HS256"]


# =============================================================================
# ENCODING
# =============================================================================

def encode_token(
    payload: dict,
    expires_in: int = 900,
    secret: Optional[str] = None,
    algorithm: str = DEFAULT_ALGORITHM,
) -> str:
    """
    Encode a payload into a JWT token.

    Args:
        payload: Dictionary of claims to encode (user_id, type, etc.)
        expires_in: Seconds until token expires (default: 900 = 15 min)
        secret: Signing secret (default: settings.SECRET_KEY)
        algorithm: JWT algorithm (default: HS256)

    Returns:
        Encoded JWT string

    Example:
        token = encode_token(
            payload={"user_id": 123, "type": "access"},
            expires_in=3600  # 1 hour
        )

    Note:
        Automatically adds 'exp' (expiration) and 'iat' (issued at) claims.
    """
    now = datetime.now(timezone.utc)

    # Build full payload with standard claims
    token_payload = {
        **payload,
        "exp": now + timedelta(seconds=expires_in),
        "iat": now,
    }

    return jwt.encode(
        token_payload,
        secret or settings.SECRET_KEY,
        algorithm=algorithm
    )


# =============================================================================
# DECODING
# =============================================================================

def decode_token(
    token: str,
    secret: Optional[str] = None,
    algorithms: Optional[list] = None,
    verify_exp: bool = True,
) -> dict:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT string to decode
        secret: Signing secret (default: settings.SECRET_KEY)
        algorithms: Allowed algorithms (default: ["HS256"])
        verify_exp: Whether to verify expiration (default: True)

    Returns:
        Decoded payload dictionary

    Raises:
        TokenExpired: Token has expired
        TokenInvalid: Token is malformed or signature invalid

    Example:
        try:
            payload = decode_token(token)
            user_id = payload["user_id"]
        except TokenExpired:
            # Token expired - client should refresh
            pass
        except TokenInvalid:
            # Token is invalid - client should re-authenticate
            pass
    """
    try:
        return jwt.decode(
            token,
            secret or settings.SECRET_KEY,
            algorithms=algorithms or ALLOWED_ALGORITHMS,
            options={"verify_exp": verify_exp}
        )
    except jwt.ExpiredSignatureError:
        raise TokenExpired()
    except jwt.InvalidTokenError as e:
        raise TokenInvalid(message=str(e) if settings.DEBUG else None)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def decode_token_unverified(token: str) -> dict:
    """
    Decode a token WITHOUT verifying signature or expiration.

    WARNING: Use only for inspection/logging, never for authentication.

    Args:
        token: JWT string to decode

    Returns:
        Decoded payload dictionary (unverified)

    Raises:
        TokenInvalid: Token is malformed
    """
    try:
        return jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False}
        )
    except jwt.InvalidTokenError:
        raise TokenInvalid()


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get expiration time from a token without full verification.

    Useful for checking if a token needs refresh without full validation.

    Args:
        token: JWT string

    Returns:
        Expiration datetime (UTC) or None if no exp claim

    Raises:
        TokenInvalid: Token is malformed
    """
    payload = decode_token_unverified(token)
    exp = payload.get("exp")
    if exp:
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    return None


def is_token_expired(token: str, buffer_seconds: int = 0) -> bool:
    """
    Check if a token is expired or will expire soon.

    Args:
        token: JWT string
        buffer_seconds: Consider expired if within this many seconds of expiry

    Returns:
        True if expired or expiring soon, False otherwise

    Example:
        # Check if token needs refresh (expires in less than 5 minutes)
        if is_token_expired(token, buffer_seconds=300):
            token = refresh_token(...)
    """
    expiry = get_token_expiry(token)
    if not expiry:
        return True  # No expiry = treat as expired for safety
    return datetime.now(timezone.utc) >= expiry - timedelta(seconds=buffer_seconds)
