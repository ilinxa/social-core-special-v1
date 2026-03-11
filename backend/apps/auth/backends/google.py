"""
Google OAuth Backend
====================
Google OAuth 2.0 implementation with PKCE support.

OAuth Flow:
    1. GET /oauth/google/ → Redirect to Google authorization URL
    2. User authorizes on Google
    3. GET /oauth/google/callback/?code=...&state=... → Exchange code for tokens

Security:
    - PKCE (code_challenge/code_verifier) for authorization code protection
    - State parameter for CSRF protection
    - ID token verification with Google's public keys

Configuration Required:
    GOOGLE_OAUTH_CLIENT_ID: Google OAuth client ID
    GOOGLE_OAUTH_CLIENT_SECRET: Google OAuth client secret
    BACKEND_URL: Backend base URL for callback

Usage:
    from apps.auth.backends import GoogleOAuthBackend
    from apps.auth.services.oauth_service import OAuthStateManager

    # Start OAuth
    state_params = OAuthStateManager.create_state('google')
    url = GoogleOAuthBackend.get_authorization_url(state_params)

    # In callback
    tokens = GoogleOAuthBackend.exchange_code(code, code_verifier)
    user_info = GoogleOAuthBackend.verify_id_token(tokens['id_token'])
"""

import logging
from typing import Optional
from urllib.parse import urlencode

import requests
from django.conf import settings

from apps.core.exceptions import OAuthError

logger = logging.getLogger(__name__)


class GoogleOAuthBackend:
    """
    Google OAuth 2.0 with PKCE.

    Implements authorization code flow with PKCE for secure OAuth.
    """

    AUTHORIZATION_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
    TOKEN_URL = 'https://oauth2.googleapis.com/token'
    USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo'

    @classmethod
    def get_authorization_url(cls, state_params: dict, redirect_uri: str = None) -> str:
        """
        Build Google authorization URL with PKCE.

        Args:
            state_params: Dict from OAuthStateManager.create_state()
            redirect_uri: Optional custom redirect URI

        Returns:
            Authorization URL to redirect user to
        """
        client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
        if not client_id:
            raise OAuthError(message="Google OAuth not configured", provider='google')

        backend_url = getattr(settings, 'BACKEND_URL', 'http://localhost:8000')
        default_redirect = f"{backend_url}/api/v1/auth/oauth/google/callback/"

        params = {
            'client_id': client_id,
            'redirect_uri': redirect_uri or default_redirect,
            'response_type': 'code',
            'scope': 'openid email profile',
            'state': state_params['state_token'],
            'code_challenge': state_params['code_challenge'],
            'code_challenge_method': 'S256',
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent'  # Always show consent screen (for refresh token)
        }

        return f"{cls.AUTHORIZATION_URL}?{urlencode(params)}"

    @classmethod
    def exchange_code(
        cls,
        code: str,
        code_verifier: str,
        redirect_uri: str = None
    ) -> dict:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from callback
            code_verifier: PKCE code verifier from state
            redirect_uri: Must match the redirect_uri used in authorization

        Returns:
            Dict with access_token, id_token, refresh_token, etc.

        Raises:
            OAuthError: If exchange fails
        """
        client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)
        client_secret = getattr(settings, 'GOOGLE_OAUTH_CLIENT_SECRET', None)

        if not client_id or not client_secret:
            raise OAuthError(message="Google OAuth not configured", provider='google')

        backend_url = getattr(settings, 'BACKEND_URL', 'http://localhost:8000')
        default_redirect = f"{backend_url}/api/v1/auth/oauth/google/callback/"

        try:
            response = requests.post(
                cls.TOKEN_URL,
                data={
                    'client_id': client_id,
                    'client_secret': client_secret,
                    'code': code,
                    'code_verifier': code_verifier,  # PKCE verification
                    'grant_type': 'authorization_code',
                    'redirect_uri': redirect_uri or default_redirect
                },
                timeout=30
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                logger.error(
                    "oauth.google.exchange_failed",
                    extra={'status': response.status_code, 'error': error_data}
                )
                raise OAuthError(
                    message="Failed to exchange authorization code",
                    provider='google',
                    oauth_error=error_data.get('error_description', 'Unknown error')
                )

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Google OAuth request failed: {e}")
            raise OAuthError(
                message="Failed to connect to Google",
                provider='google'
            )

    @classmethod
    def verify_id_token(cls, id_token: str) -> dict:
        """
        Verify and decode Google ID token.

        Uses google-auth library if available, falls back to manual verification.

        Args:
            id_token: ID token from token exchange

        Returns:
            Dict with user info (sub, email, name, picture, etc.)

        Raises:
            OAuthError: If verification fails
        """
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests

            client_id = getattr(settings, 'GOOGLE_OAUTH_CLIENT_ID', None)

            idinfo = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                client_id
            )

            return idinfo

        except ImportError:
            # google-auth not installed, use userinfo endpoint instead
            logger.warning("google-auth not installed, using userinfo endpoint")
            return cls._get_userinfo_fallback(id_token)

        except ValueError as e:
            logger.error(f"Google ID token verification failed: {e}")
            raise OAuthError(
                message=f"Invalid ID token: {e}",
                provider='google'
            )

    @classmethod
    def _get_userinfo_fallback(cls, access_token: str) -> dict:
        """
        Fallback: Get user info using userinfo endpoint.

        Less secure than ID token verification but works without google-auth.
        """
        try:
            response = requests.get(
                cls.USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30
            )

            if response.status_code != 200:
                raise OAuthError(
                    message="Failed to get user info from Google",
                    provider='google'
                )

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Google userinfo request failed: {e}")
            raise OAuthError(
                message="Failed to connect to Google",
                provider='google'
            )

    @classmethod
    def get_user_info(cls, access_token: str) -> dict:
        """
        Get user profile information using access token.

        Args:
            access_token: OAuth access token

        Returns:
            Dict with user profile (sub, email, name, picture, etc.)
        """
        try:
            response = requests.get(
                cls.USERINFO_URL,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30
            )

            if response.status_code != 200:
                raise OAuthError(
                    message="Failed to get user info from Google",
                    provider='google'
                )

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Google userinfo request failed: {e}")
            raise OAuthError(
                message="Failed to connect to Google",
                provider='google'
            )
