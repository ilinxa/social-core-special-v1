"""
Apple OAuth Backend
===================
Apple Sign In implementation with nonce validation.

Apple-specific considerations:
    - Uses POST for callback (not GET like most OAuth providers)
    - ID token contains user info (no userinfo endpoint)
    - First sign-in includes user name in POST body, subsequent sign-ins don't
    - Requires nonce validation to prevent ID token replay attacks
    - Requires generating client_secret JWT on each request

OAuth Flow:
    1. GET /oauth/apple/ → Redirect to Apple authorization URL
    2. User authorizes on Apple
    3. POST /oauth/apple/callback/ with code, id_token, state, user (first time)

Security:
    - Nonce validation: Prevents ID token replay attacks
    - PKCE: Authorization code interception protection
    - State: CSRF protection

Configuration Required:
    APPLE_OAUTH_CLIENT_ID: Apple Services ID (com.example.app)
    APPLE_OAUTH_TEAM_ID: Apple Developer Team ID
    APPLE_OAUTH_KEY_ID: Key ID for Sign In with Apple private key
    APPLE_OAUTH_PRIVATE_KEY: Private key content (PEM format)
"""

import logging
import time
from urllib.parse import urlencode

import jwt
import requests
from django.conf import settings

from apps.core.exceptions import OAuthError

logger = logging.getLogger(__name__)


class AppleOAuthBackend:
    """
    Apple Sign In with PKCE and nonce validation.

    Apple Sign In is more complex than other OAuth providers due to:
    - Client secret must be generated as a JWT
    - User info is only provided on first sign-in
    - Callback uses POST (form_post response mode)
    - Nonce is required for ID token validation
    """

    AUTHORIZATION_URL = "https://appleid.apple.com/auth/authorize"
    TOKEN_URL = "https://appleid.apple.com/auth/token"
    KEYS_URL = "https://appleid.apple.com/auth/keys"

    @classmethod
    def get_authorization_url(cls, state_params: dict, redirect_uri: str = None) -> str:
        """
        Build Apple authorization URL.

        Args:
            state_params: Dict from OAuthStateManager.create_state()
            redirect_uri: Optional custom redirect URI

        Returns:
            Authorization URL to redirect user to
        """
        client_id = getattr(settings, "APPLE_OAUTH_CLIENT_ID", None)
        if not client_id:
            raise OAuthError(message="Apple OAuth not configured", provider="apple")

        backend_url = getattr(settings, "BACKEND_URL", "http://localhost:8000")
        default_redirect = f"{backend_url}/api/v1/auth/oauth/apple/callback/"

        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri or default_redirect,
            "response_type": "code id_token",
            "response_mode": "form_post",  # Apple uses POST callback
            "scope": "name email",
            "state": state_params["state_token"],
            "nonce": state_params["nonce"],  # Required for Apple
            "code_challenge": state_params["code_challenge"],
            "code_challenge_method": "S256",
        }

        return f"{cls.AUTHORIZATION_URL}?{urlencode(params)}"

    @classmethod
    def generate_client_secret(cls) -> str:
        """
        Generate client secret JWT for Apple.

        Apple requires the client_secret to be a JWT signed with your
        private key. This JWT is valid for up to 6 months.

        Returns:
            Client secret JWT string

        Raises:
            OAuthError: If configuration is missing
        """
        team_id = getattr(settings, "APPLE_OAUTH_TEAM_ID", None)
        client_id = getattr(settings, "APPLE_OAUTH_CLIENT_ID", None)
        key_id = getattr(settings, "APPLE_OAUTH_KEY_ID", None)
        private_key = getattr(settings, "APPLE_OAUTH_PRIVATE_KEY", None)

        if not all([team_id, client_id, key_id, private_key]):
            raise OAuthError(message="Apple OAuth not configured", provider="apple")

        now = int(time.time())

        payload = {
            "iss": team_id,
            "iat": now,
            "exp": now + 86400 * 180,  # 180 days max
            "aud": "https://appleid.apple.com",
            "sub": client_id,
        }

        headers = {"kid": key_id, "alg": "ES256"}

        return jwt.encode(payload, private_key, algorithm="ES256", headers=headers)

    @classmethod
    def exchange_code(
        cls, code: str, code_verifier: str, redirect_uri: str = None
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
        client_id = getattr(settings, "APPLE_OAUTH_CLIENT_ID", None)
        if not client_id:
            raise OAuthError(message="Apple OAuth not configured", provider="apple")

        backend_url = getattr(settings, "BACKEND_URL", "http://localhost:8000")
        default_redirect = f"{backend_url}/api/v1/auth/oauth/apple/callback/"

        try:
            client_secret = cls.generate_client_secret()

            response = requests.post(
                cls.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "code_verifier": code_verifier,
                    "grant_type": "authorization_code",
                    "redirect_uri": redirect_uri or default_redirect,
                },
                timeout=30,
            )

            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                logger.error(
                    "oauth.apple.exchange_failed",
                    extra={"status": response.status_code, "error": error_data},
                )
                raise OAuthError(
                    message="Failed to exchange authorization code",
                    provider="apple",
                    oauth_error=error_data.get("error", "Unknown error"),
                )

            return response.json()

        except requests.RequestException as e:
            logger.error(f"Apple OAuth request failed: {e}")
            raise OAuthError(
                message="Failed to connect to Apple", provider="apple"
            ) from e

    @classmethod
    def verify_id_token(cls, id_token_str: str, expected_nonce: str) -> dict:
        """
        Verify Apple ID token with nonce validation.

        Apple ID tokens are JWTs signed with Apple's private keys.
        We need to:
        1. Fetch Apple's public keys
        2. Verify signature
        3. Validate audience (our client_id)
        4. Validate issuer (https://appleid.apple.com)
        5. Validate nonce (CRITICAL for security)

        Args:
            id_token_str: The ID token from Apple
            expected_nonce: The nonce we sent in authorization request

        Returns:
            Dict with user info (sub, email, email_verified, etc.)

        Raises:
            OAuthError: If verification fails
        """
        client_id = getattr(settings, "APPLE_OAUTH_CLIENT_ID", None)

        try:
            # Get Apple's public keys
            keys_response = requests.get(cls.KEYS_URL, timeout=30)
            if keys_response.status_code != 200:
                raise OAuthError(
                    message="Failed to fetch Apple public keys", provider="apple"
                )

            apple_keys = keys_response.json()["keys"]

            # Decode header to get key ID
            header = jwt.get_unverified_header(id_token_str)
            kid = header.get("kid")

            # Find matching key
            apple_key = next((k for k in apple_keys if k["kid"] == kid), None)
            if not apple_key:
                raise OAuthError(message="Apple public key not found", provider="apple")

            # Convert JWK to PEM
            public_key = jwt.algorithms.RSAAlgorithm.from_jwk(apple_key)

            # Verify and decode
            payload = jwt.decode(
                id_token_str,
                public_key,
                algorithms=["RS256"],
                audience=client_id,
                issuer="https://appleid.apple.com",
            )

            # Validate nonce (CRITICAL for Apple)
            if payload.get("nonce") != expected_nonce:
                logger.error(
                    "oauth.apple.nonce_mismatch",
                    extra={"expected_hash": hash(expected_nonce)},
                )
                raise OAuthError(
                    message="Nonce mismatch - possible replay attack", provider="apple"
                )

            return payload

        except jwt.InvalidTokenError as e:
            logger.error(f"Apple ID token verification failed: {e}")
            raise OAuthError(
                message=f"Invalid Apple ID token: {e}", provider="apple"
            ) from e

        except requests.RequestException as e:
            logger.error(f"Apple keys request failed: {e}")
            raise OAuthError(
                message="Failed to connect to Apple", provider="apple"
            ) from e

    @classmethod
    def parse_user_data(cls, user_data: str | None) -> dict:
        """
        Parse user data from Apple callback.

        Apple only sends user data (name) on the first authorization.
        The data comes as a JSON string in the 'user' POST parameter.

        Args:
            user_data: JSON string from 'user' POST parameter (may be None)

        Returns:
            Dict with name info, empty dict if no data
        """
        if not user_data:
            return {}

        try:
            import json

            data = json.loads(user_data)

            # Extract name if present
            name = data.get("name", {})
            return {
                "first_name": name.get("firstName", ""),
                "last_name": name.get("lastName", ""),
                "email": data.get("email", ""),
            }

        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse Apple user data")
            return {}
