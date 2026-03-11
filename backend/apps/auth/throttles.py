"""
Auth Throttles
==============
Rate limiting for authentication endpoints.

Throttles:
    - LoginRateThrottle: Limits login attempts
    - PasswordResetRateThrottle: Limits password reset requests
    - VerificationRateThrottle: Limits verification email requests

Usage:
    class LoginView(APIView):
        throttle_classes = [LoginRateThrottle]
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """
    Rate limit for login attempts.

    Default: 5 attempts per minute per IP.
    """
    scope = 'login'


class PasswordResetRateThrottle(AnonRateThrottle):
    """
    Rate limit for password reset requests.

    Default: 3 requests per hour per IP.
    """
    scope = 'password_reset'


class VerificationRateThrottle(AnonRateThrottle):
    """
    Rate limit for verification email requests.

    Default: 5 requests per hour per IP.
    """
    scope = 'verification'


class OAuthRateThrottle(AnonRateThrottle):
    """
    Rate limit for OAuth initiation.

    Default: 10 requests per minute per IP.
    """
    scope = 'oauth'


class RefreshRateThrottle(AnonRateThrottle):
    """
    Rate limit for token refresh requests.

    Separate from global anon bucket so refresh calls don't compete
    with other anonymous traffic (explore, public pages, etc.).

    Default: 30 requests per minute per IP.
    """
    scope = 'refresh'
