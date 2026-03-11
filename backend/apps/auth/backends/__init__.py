"""
OAuth Backends
==============
OAuth provider implementations for social login.

Supported Providers:
    - Google OAuth 2.0 with PKCE
    - Apple Sign In with nonce validation
"""

from apps.auth.backends.google import GoogleOAuthBackend
from apps.auth.backends.apple import AppleOAuthBackend

__all__ = [
    'GoogleOAuthBackend',
    'AppleOAuthBackend',
]
