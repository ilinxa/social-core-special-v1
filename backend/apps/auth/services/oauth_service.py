"""
OAuth Service
=============
OAuth state management and common OAuth utilities.

Security Features:
    - State parameter: CSRF protection
    - PKCE: Authorization code interception protection
    - Nonce: ID token replay protection (Apple)

Usage:
    # Create OAuth state
    state_params = OAuthStateManager.create_state('google')

    # Build authorization URL with state_params
    url = GoogleOAuthBackend.get_authorization_url(state_params)

    # In callback, validate and consume state
    state_data = OAuthStateManager.validate_and_consume_state(state_token)
"""

import base64
import hashlib
import secrets

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone

from apps.core.exceptions import OAuthError

# Observability
from apps.core.observability import get_logger
from apps.core.observability.audit import AuditLog, AuditService

logger = get_logger(__name__)


class OAuthStateManager:
    """
    Secure state management for OAuth flows.

    State includes:
        - Random token for CSRF protection
        - PKCE code verifier
        - Nonce (for Apple)
        - Redirect destination
        - Device info
    """

    STATE_CACHE_PREFIX = "oauth_state:"
    STATE_TTL = 600  # 10 minutes

    @classmethod
    def generate_pkce_pair(cls) -> tuple[str, str]:
        """
        Generate PKCE code verifier and challenge.

        PKCE (Proof Key for Code Exchange) prevents authorization code
        interception attacks.

        Returns:
            Tuple of (code_verifier, code_challenge)
        """
        # Generate 43-128 character code verifier
        code_verifier = secrets.token_urlsafe(32)

        # Generate SHA256 challenge
        digest = hashlib.sha256(code_verifier.encode()).digest()
        code_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()

        return code_verifier, code_challenge

    @classmethod
    def create_state(
        cls, provider: str, redirect_to: str = None, device_info: dict = None
    ) -> dict:
        """
        Create OAuth state with all security parameters.

        Args:
            provider: OAuth provider name ('google', 'apple')
            redirect_to: Where to redirect after OAuth completion
            device_info: Client device information

        Returns:
            Dict with state_token, code_verifier, code_challenge, nonce
        """
        state_token = secrets.token_urlsafe(32)
        code_verifier, code_challenge = cls.generate_pkce_pair()
        nonce = secrets.token_urlsafe(16)  # Required for Apple

        # Store in cache
        state_data = {
            "provider": provider,
            "code_verifier": code_verifier,
            "nonce": nonce,
            "redirect_to": redirect_to,
            "device_info": device_info,
            "created_at": timezone.now().isoformat(),
        }

        cache_key = f"{cls.STATE_CACHE_PREFIX}{state_token}"
        cache.set(cache_key, state_data, cls.STATE_TTL)

        logger.debug(
            "oauth.state.created",
            provider=provider,
            state_hash=hash(state_token),
        )

        return {
            "state_token": state_token,
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "nonce": nonce,
        }

    @classmethod
    def validate_and_consume_state(cls, state_token: str) -> dict:
        """
        Validate state token and return stored data.

        State is consumed (deleted) after validation to prevent replay.

        Args:
            state_token: State token from OAuth callback

        Returns:
            Dict with provider, code_verifier, nonce, redirect_to, device_info

        Raises:
            OAuthError: If state is invalid or expired
        """
        cache_key = f"{cls.STATE_CACHE_PREFIX}{state_token}"
        state_data = cache.get(cache_key)

        if not state_data:
            logger.warning(
                "oauth.state.invalid",
                state_hash=hash(state_token),
            )
            raise OAuthError(
                message="Invalid or expired OAuth state",
            )

        # Consume state (one-time use)
        cache.delete(cache_key)

        logger.debug(
            "oauth.state.consumed",
            provider=state_data.get("provider"),
        )

        return state_data


class OAuthService:
    """
    OAuth authentication service.

    Handles user creation/login from OAuth providers.
    """

    @staticmethod
    def authenticate_or_create_user(
        *,
        provider: str,
        provider_uid: str,
        email: str,
        email_verified: bool = False,
        provider_data: dict = None,
        device_info=None,
        request: HttpRequest | None = None,
    ) -> tuple["User", "TokenPair", "DeviceSession", bool]:
        """
        Authenticate or create user from OAuth provider data.

        Args:
            provider: OAuth provider name ('google', 'apple')
            provider_uid: Unique ID from provider
            email: User's email from provider
            email_verified: Whether provider verified the email
            provider_data: Additional data from provider
            device_info: Device info for session creation
            request: HTTP request for audit context (optional)

        Returns:
            Tuple of (User, TokenPair, DeviceSession, is_new_user)

        Raises:
            OAuthError: If OAuth connection cannot be established
        """
        from django.db import transaction

        from apps.auth.models import OAuthConnection
        from apps.auth.services import AuthService, DeviceInfo
        from apps.users.selectors import UserSelector
        from apps.users.services import UserService

        provider_data = provider_data or {}

        with transaction.atomic():
            # Check if OAuth connection exists
            connection = (
                OAuthConnection.objects.filter(
                    provider=provider, provider_uid=provider_uid
                )
                .select_related("user")
                .first()
            )

            if connection:
                # Existing OAuth user - login
                user = connection.user

                if not user.is_active:
                    raise OAuthError(
                        message="Account is deactivated", provider=provider
                    )

                # Update connection data
                connection.provider_data = provider_data
                connection.provider_email = email
                connection.save(
                    update_fields=["provider_data", "provider_email", "updated_at"]
                )

                is_new_user = False

                logger.info(
                    "oauth.login.existing_connection",
                    provider=provider,
                    user_id=str(user.id),
                )

            else:
                # Check if user with this email exists
                existing_user = UserSelector.get_by_email_or_none(email=email)

                if existing_user:
                    # Block linking if provider did not verify the email
                    if not email_verified:
                        logger.warning(
                            "oauth.login.unverified_email_link_blocked",
                            provider=provider,
                        )
                        from apps.core.exceptions.domain import OAuthError

                        raise OAuthError(
                            message="Cannot link account: email not verified by provider.",
                            provider=provider,
                        )

                    # Link OAuth to existing account
                    user = existing_user

                    oauth_connection = OAuthConnection.objects.create(
                        user=user,
                        provider=provider,
                        provider_uid=provider_uid,
                        provider_data=provider_data,
                        provider_email=email,
                    )

                    is_new_user = False

                    logger.info(
                        "oauth.login.account_linked",
                        provider=provider,
                        user_id=str(user.id),
                    )

                    # Audit: OAuth account linked
                    AuditService.log(
                        action=AuditLog.Action.OAUTH_LINKED,
                        actor=user,
                        resource=oauth_connection,
                        request=request,
                        details={"provider": provider},
                    )

                else:
                    # Create new user
                    # Generate a random password (user won't use it - they login via OAuth)
                    random_password = secrets.token_urlsafe(32)

                    user = UserService.create_user(
                        email=email,
                        password=random_password,
                        request=request,
                    )

                    # If provider verified email, mark user as verified
                    if email_verified:
                        UserService.verify_email(user=user, request=request)

                    # Create OAuth connection
                    oauth_connection = OAuthConnection.objects.create(
                        user=user,
                        provider=provider,
                        provider_uid=provider_uid,
                        provider_data=provider_data,
                        provider_email=email,
                    )

                    is_new_user = True

                    logger.info(
                        "oauth.login.user_created",
                        provider=provider,
                        user_id=str(user.id),
                    )

                    # Audit: OAuth account linked (for new user)
                    AuditService.log(
                        action=AuditLog.Action.OAUTH_LINKED,
                        actor=user,
                        resource=oauth_connection,
                        request=request,
                        details={"provider": provider, "is_new_user": True},
                    )

        # Create session and tokens
        if device_info is None:
            device_info = DeviceInfo(
                device_id=f"oauth_{provider}_{provider_uid[:8]}",
                device_type="unknown",
                device_name=f"{provider.title()} Login",
            )

        # Create tokens directly (skip password verification)
        from apps.auth.models import DeviceSession, RefreshToken

        session, created = DeviceSession.objects.update_or_create(
            user=user,
            device_id=device_info.device_id,
            defaults={
                "device_type": device_info.device_type,
                "device_name": device_info.device_name,
                "user_agent": device_info.user_agent,
                "ip_address": device_info.ip_address,
                "is_active": True,
            },
        )

        # Create token pair
        refresh_token, raw_refresh = RefreshToken.create_token(
            user=user,
            device_id=device_info.device_id,
            device_info={
                "type": device_info.device_type,
                "name": device_info.device_name,
                "user_agent": device_info.user_agent,
            },
            ip_address=device_info.ip_address,
        )

        session.current_token = refresh_token
        session.save(update_fields=["current_token"])

        access_token = AuthService._create_access_token(user, refresh_token.jti)

        jwt_auth = getattr(settings, "JWT_AUTH", {})
        from apps.auth.services.auth_service import TokenPair

        tokens = TokenPair(
            access_token=access_token,
            refresh_token=raw_refresh,
            access_expires_in=jwt_auth.get("ACCESS_TOKEN_LIFETIME", 900),
            refresh_expires_in=jwt_auth.get("REFRESH_TOKEN_LIFETIME", 604800),
        )

        # Update last login
        UserService.update_last_login(user=user)

        # Audit: Login success via OAuth
        AuditService.log(
            action=AuditLog.Action.LOGIN_SUCCESS,
            actor=user,
            resource=session,
            request=request,
            details={
                "method": "oauth",
                "provider": provider,
                "is_new_user": is_new_user,
            },
        )

        # Audit: Session created (if new device)
        if created:
            AuditService.log(
                action=AuditLog.Action.SESSION_CREATED,
                actor=user,
                resource=session,
                request=request,
                details={
                    "method": "oauth",
                    "provider": provider,
                    "device_type": device_info.device_type,
                },
            )

        return user, tokens, session, is_new_user
