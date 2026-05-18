"""
Auth Views
==========
API views for authentication endpoints.

Endpoints:
    - Registration and login
    - Token refresh and logout
    - Email verification
    - Password reset and change
    - Session management
    - OAuth flows

Security:
    - Rate limiting via throttle classes
    - CSRF protection for web clients (via cookie)
    - Proper error messages (don't reveal existence of users)
"""

import uuid

from django.conf import settings
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auth import serializers
from apps.auth.backends import AppleOAuthBackend, GoogleOAuthBackend
from apps.auth.models import DeviceSession
from apps.auth.services import (
    AuthService,
    DeviceInfo,
    GovernanceAuthService,
    PasswordService,
    VerificationService,
)
from apps.auth.services.oauth_service import OAuthService, OAuthStateManager
from apps.auth.throttles import (
    LoginRateThrottle,
    PasswordResetRateThrottle,
    RefreshRateThrottle,
    VerificationRateThrottle,
)
from apps.core.exceptions import TokenExpired, TokenInvalid
from apps.core.observability import get_logger
from apps.core.utils.request import get_client_ip, parse_user_agent
from apps.users.selectors import UserSelector
from apps.users.services import UserService

logger = get_logger(__name__)


def _build_device_info(
    data: dict, request, fallback_device_id: str = "unknown"
) -> DeviceInfo:
    """Build DeviceInfo from request data, parsing User-Agent for device name when not provided."""
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    device_name = data.get("device_name", "")

    # If client didn't provide a device_name, parse it from User-Agent
    if not device_name and user_agent:
        parsed = parse_user_agent(user_agent)
        device_name = parsed["device_name"]

    return DeviceInfo(
        device_id=data.get("device_id") or fallback_device_id,
        device_type=data.get("device_type", "unknown"),
        device_name=device_name,
        user_agent=user_agent,
        ip_address=get_client_ip(request),
    )


# =============================================================================
# REGISTRATION
# =============================================================================


class RegisterView(APIView):
    """
    Register a new user.

    POST /api/v1/auth/register/
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Register a new user",
        description="""
        Create a new user account with email and password.

        **Flow:**
        1. Creates user account (unverified)
        2. Generates authentication tokens
        3. Sends verification email with 6-digit code and magic link

        **Token Handling:**
        - Web clients (default): Refresh token is set as HttpOnly cookie
        - Mobile clients (X-Client-Type: mobile): Refresh token is returned in response body

        **Rate Limiting:**
        - No explicit rate limit (relies on general API limits)
        """,
        tags=["Authentication"],
        request=serializers.RegisterSerializer,
        responses={
            201: OpenApiResponse(
                response=serializers.AuthResponseSerializer,
                description="User created successfully. Verification email sent.",
            ),
            400: OpenApiResponse(
                description="Validation error (invalid email, weak password, etc.)"
            ),
            409: OpenApiResponse(description="Email already registered"),
        },
    )
    def post(self, request):
        serializer = serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Create user
        user = UserService.create_user(
            email=data["email"],
            password=data["password"],
            username=data.get("username"),
            referred_by_id=data.get("referred_by") if data.get("referred_by") else None,
            request=request,
        )

        # Build device info
        device_info = _build_device_info(
            data, request, fallback_device_id=f"reg_{user.id}"
        )

        # Create session and tokens
        _, tokens, session = AuthService.login(
            email=data["email"],
            password=data["password"],
            device_info=device_info,
            request=request,
        )

        # Send verification email
        VerificationService.create_token(user=user, request=request)

        # Build response
        response_data = {
            "user": user,
            "tokens": {
                "access_token": tokens.access_token,
                "access_expires_in": tokens.access_expires_in,
                "refresh_expires_in": tokens.refresh_expires_in,
                "token_type": "Bearer",
            },
            "is_new_user": True,
        }

        # Add refresh token based on client type
        client_type = request.META.get("HTTP_X_CLIENT_TYPE", "web")
        response = Response(
            serializers.AuthResponseSerializer(response_data).data,
            status=status.HTTP_201_CREATED,
        )

        if client_type == "web":
            # Set refresh token in HttpOnly cookie
            response.set_cookie(
                key="refresh_token",
                value=tokens.refresh_token,
                max_age=tokens.refresh_expires_in,
                httponly=True,
                secure=not settings.DEBUG,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
                path="/api/",
            )
        else:
            # Include refresh token in body for mobile
            response.data["tokens"]["refresh_token"] = tokens.refresh_token

        return response


# =============================================================================
# LOGIN
# =============================================================================


class LoginView(APIView):
    """
    Login with email and password.

    POST /api/v1/auth/login/
    """

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(
        summary="Login with email and password",
        description="""
        Authenticate user with email and password credentials.

        **Token Handling:**
        - Web clients (default): Refresh token is set as HttpOnly cookie
        - Mobile clients (X-Client-Type: mobile): Refresh token is returned in response body

        **Device Tracking:**
        - Provide device_id for consistent session tracking across logins
        - Sessions are limited per user (default: 5). Oldest session is revoked when limit is exceeded.

        **Security:**
        - Rate limited to prevent brute force attacks (5 attempts/minute)
        - New device login triggers notification email
        """,
        tags=["Authentication"],
        request=serializers.LoginSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.AuthResponseSerializer,
                description="Login successful",
            ),
            400: OpenApiResponse(description="Validation error"),
            401: OpenApiResponse(description="Invalid credentials"),
            403: OpenApiResponse(description="Account inactive or not verified"),
            429: OpenApiResponse(
                description="Too many login attempts. Try again later."
            ),
        },
    )
    def post(self, request):
        serializer = serializers.LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Build device info
        device_info = _build_device_info(data, request)

        # Authenticate
        user, tokens, session = AuthService.login(
            email=data["email"],
            password=data["password"],
            device_info=device_info,
            request=request,
        )

        # Build response
        response_data = {
            "user": user,
            "tokens": {
                "access_token": tokens.access_token,
                "access_expires_in": tokens.access_expires_in,
                "refresh_expires_in": tokens.refresh_expires_in,
                "token_type": "Bearer",
            },
        }

        # Handle refresh token based on client type
        client_type = request.META.get("HTTP_X_CLIENT_TYPE", "web")
        response = Response(
            serializers.AuthResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )

        if client_type == "web":
            response.set_cookie(
                key="refresh_token",
                value=tokens.refresh_token,
                max_age=tokens.refresh_expires_in,
                httponly=True,
                secure=not settings.DEBUG,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
                path="/api/",
            )
        else:
            response.data["tokens"]["refresh_token"] = tokens.refresh_token

        return response


# =============================================================================
# TOKEN MANAGEMENT
# =============================================================================


class RefreshView(APIView):
    """
    Refresh access token.

    POST /api/v1/auth/refresh/
    """

    permission_classes = [AllowAny]
    throttle_classes = [RefreshRateThrottle]

    @extend_schema(
        summary="Refresh access token",
        description="""
        Exchange a valid refresh token for a new access token and refresh token pair.

        **Token Sources:**
        - Web clients: Refresh token is read from HttpOnly cookie (automatic)
        - Mobile clients: Refresh token must be provided in request body

        **Token Rotation:**
        - Each refresh token can only be used ONCE
        - A new refresh token is always issued
        - Reusing an old refresh token triggers security alert and revokes all user tokens

        **Security:**
        - Implements token rotation for enhanced security
        - Old refresh tokens are immediately invalidated
        """,
        tags=["Authentication"],
        request=serializers.RefreshTokenSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.TokenResponseSerializer,
                description="New tokens issued",
            ),
            400: OpenApiResponse(description="Refresh token required"),
            401: OpenApiResponse(description="Invalid or expired refresh token"),
        },
    )
    def post(self, request):
        serializer = serializers.RefreshTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Get refresh token from body or cookie
        refresh_token = data.get("refresh_token") or request.COOKIES.get(
            "refresh_token"
        )
        if not refresh_token:
            return Response(
                {"message": "Refresh token required", "code": "missing_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Build device info
        device_info = _build_device_info(data, request)

        # Refresh tokens
        tokens = AuthService.refresh_tokens(
            refresh_token=refresh_token,
            device_info=device_info,
            request=request,
        )

        # Build response
        response_data = {
            "access_token": tokens.access_token,
            "access_expires_in": tokens.access_expires_in,
            "refresh_expires_in": tokens.refresh_expires_in,
            "token_type": "Bearer",
        }

        client_type = request.META.get("HTTP_X_CLIENT_TYPE", "web")
        response = Response(response_data)

        if client_type == "web":
            response.set_cookie(
                key="refresh_token",
                value=tokens.refresh_token,
                max_age=tokens.refresh_expires_in,
                httponly=True,
                secure=not settings.DEBUG,
                samesite=settings.REFRESH_TOKEN_COOKIE_SAMESITE,
                path="/api/",
            )
        else:
            response.data["refresh_token"] = tokens.refresh_token

        return response


class LogoutView(APIView):
    """
    Logout current session.

    POST /api/v1/auth/logout/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Logout current session",
        description="""
        Revoke the current session's refresh token.

        **Token Sources:**
        - Web clients: Refresh token is read from HttpOnly cookie
        - Mobile clients: Refresh token should be provided in request body

        The associated access token JTI is added to the blacklist, immediately
        invalidating the access token.
        """,
        tags=["Authentication"],
        request=serializers.LogoutSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.MessageSerializer,
                description="Logged out successfully",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = serializers.LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Get refresh token from body or cookie
        refresh_token = data.get("refresh_token") or request.COOKIES.get(
            "refresh_token"
        )
        if refresh_token:
            AuthService.logout(
                refresh_token=refresh_token,
                user=request.user,
                request=request,
            )

        response = Response({"message": "Logged out successfully"})

        # Clear cookie
        response.delete_cookie("refresh_token", path="/api/")

        return response


class LogoutAllView(APIView):
    """
    Logout all sessions.

    POST /api/v1/auth/logout-all/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = None  # No request body needed

    @extend_schema(
        summary="Logout all sessions",
        description="""
        Revoke all active sessions for the current user.

        This is useful when:
        - User suspects account compromise
        - User wants to sign out from all devices
        - After password change (done automatically)

        All refresh tokens are revoked and all access token JTIs are blacklisted.
        """,
        tags=["Authentication"],
        responses={
            200: OpenApiResponse(
                response=serializers.LogoutAllResponseSerializer,
                description="All sessions logged out",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        count = AuthService.logout_all(
            user=request.user,
            reason="logout_all",
            request=request,
        )

        response = Response(
            {
                "message": f"Logged out from {count} session(s)",
                "sessions_revoked": count,
            }
        )

        response.delete_cookie("refresh_token", path="/api/")

        return response


# =============================================================================
# EMAIL VERIFICATION
# =============================================================================


class VerifyEmailCodeView(APIView):
    """
    Verify email with 6-digit code.

    POST /api/v1/auth/verify-email/
    """

    permission_classes = [AllowAny]
    throttle_classes = [VerificationRateThrottle]

    @extend_schema(
        summary="Verify email with code",
        description="""
        Verify user's email address using the 6-digit code sent via email.

        **Flow:**
        1. User receives email with 6-digit code
        2. User enters code in app
        3. If valid, user's email is marked as verified
        4. Welcome notification is sent

        **Code Validity:**
        - Codes expire after 24 hours
        - Only the most recent code is valid
        - Rate limited to prevent brute-force OTP guessing
        """,
        tags=["Email Verification"],
        request=serializers.VerifyEmailCodeSerializer,
        responses={
            200: OpenApiResponse(description="Email verified successfully"),
            400: OpenApiResponse(description="Invalid or expired code"),
            404: OpenApiResponse(description="No pending verification for this email"),
            429: OpenApiResponse(description="Too many attempts. Try again later."),
        },
    )
    def post(self, request):
        serializer = serializers.VerifyEmailCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            user = VerificationService.verify_by_code(
                email=data["email"],
                code=data["code"],
                request=request,
            )
        except TokenInvalid:
            return Response(
                {
                    "error": {
                        "message": "Invalid verification code. Please check the code and try again.",
                        "code": "invalid_code",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except TokenExpired:
            return Response(
                {
                    "error": {
                        "message": "Verification code has expired. Please request a new code.",
                        "code": "code_expired",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"message": "Email verified successfully", "user_id": user.id})


class VerifyEmailLinkView(APIView):
    """
    Verify email with magic link token.

    GET /api/v1/auth/verify-email/<uuid:token>/
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Verify email with magic link",
        description="""
        Verify user's email address using the magic link token from the verification email.

        **Flow:**
        1. User clicks verification link in email
        2. Backend validates token
        3. If valid, user's email is marked as verified
        4. User is redirected to frontend success page (if FRONTEND_URL is configured)

        **Token Validity:**
        - Tokens expire after 24 hours
        - Each token can only be used once
        """,
        tags=["Email Verification"],
        parameters=[
            OpenApiParameter(
                name="token",
                type=str,
                location=OpenApiParameter.PATH,
                description="UUID verification token from email link",
            )
        ],
        responses={
            200: OpenApiResponse(description="Email verified successfully"),
            302: OpenApiResponse(description="Redirect to frontend success page"),
            400: OpenApiResponse(description="Invalid verification link"),
            404: OpenApiResponse(description="Token not found or already used"),
        },
    )
    def get(self, request, token):
        try:
            token_uuid = uuid.UUID(str(token))
        except ValueError:
            return Response(
                {"message": "Invalid verification link", "code": "invalid_token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = VerificationService.verify_by_token(token_uuid, request=request)

        # Optionally redirect to frontend
        frontend_url = getattr(settings, "FRONTEND_URL", None)
        if frontend_url:
            from django.shortcuts import redirect

            return redirect(f"{frontend_url}/verify-success")

        return Response({"message": "Email verified successfully", "user_id": user.id})


class ResendVerificationView(APIView):
    """
    Resend verification email.

    POST /api/v1/auth/resend-verification/
    """

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]  # Reuse throttle

    @extend_schema(
        summary="Resend verification email",
        description="""
        Request a new verification email to be sent.

        **Security:**
        - Always returns success (doesn't reveal if email exists)
        - Rate limited to prevent abuse (3 requests/hour)
        - Only sends if user exists and is not already verified
        - Invalidates any previous verification tokens
        """,
        tags=["Email Verification"],
        request=serializers.ResendVerificationSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.MessageSerializer,
                description="Verification email sent (if applicable)",
            ),
            429: OpenApiResponse(description="Too many requests. Try again later."),
        },
    )
    def post(self, request):
        serializer = serializers.ResendVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = UserSelector.get_by_email_or_none(email=data["email"])

        # Always return success (don't reveal if user exists)
        if user and not user.is_verified:
            VerificationService.resend_verification(user, request=request)

        return Response(
            {
                "message": "If an account exists with this email, a verification link has been sent"
            }
        )


# =============================================================================
# PASSWORD MANAGEMENT
# =============================================================================


class PasswordResetRequestView(APIView):
    """
    Request password reset.

    POST /api/v1/auth/password/reset/
    """

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    @extend_schema(
        summary="Request password reset",
        description="""
        Request a password reset email to be sent.

        **Security:**
        - Always returns success (doesn't reveal if email exists)
        - Rate limited to prevent abuse (3 requests/hour)
        - Reset links expire after 1 hour
        - Only one active reset token per user

        **Email Content:**
        - Contains a unique reset link
        - Includes IP address that requested the reset
        """,
        tags=["Password Management"],
        request=serializers.PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.MessageSerializer,
                description="Reset email sent (if email exists)",
            ),
            429: OpenApiResponse(description="Too many requests. Try again later."),
        },
    )
    def post(self, request):
        serializer = serializers.PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        PasswordService.request_reset(
            email=data["email"],
            ip_address=get_client_ip(request),
            request=request,
        )

        # Always return success (don't reveal if user exists)
        return Response(
            {
                "message": "If an account exists with this email, a password reset link has been sent"
            }
        )


class PasswordResetConfirmView(APIView):
    """
    Confirm password reset with new password.

    POST /api/v1/auth/password/reset/confirm/
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Confirm password reset",
        description="""
        Set a new password using a valid reset token.

        **Flow:**
        1. User clicks reset link in email
        2. Frontend extracts token from URL
        3. User enters new password
        4. Backend validates token and sets new password

        **Security:**
        - Token can only be used once
        - All existing sessions are logged out
        - Confirmation email is sent
        """,
        tags=["Password Management"],
        request=serializers.PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.MessageSerializer,
                description="Password reset successful",
            ),
            400: OpenApiResponse(
                description="Invalid token or password doesn't meet requirements"
            ),
            404: OpenApiResponse(description="Token not found or expired"),
        },
    )
    def post(self, request):
        serializer = serializers.PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        PasswordService.confirm_reset(
            token_uuid=data["token"],
            new_password=data["new_password"],
            logout_all_sessions=True,
            request=request,
        )

        return Response({"message": "Password has been reset successfully"})


class PasswordChangeView(APIView):
    """
    Change password (authenticated).

    POST /api/v1/auth/password/change/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Change password",
        description="""
        Change password for the authenticated user.

        **Requirements:**
        - Must provide current password for verification
        - New password must meet security requirements (min 8 characters)

        **Security:**
        - All other sessions are logged out after password change
        - Confirmation notification is sent
        """,
        tags=["Password Management"],
        request=serializers.PasswordChangeSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.MessageSerializer,
                description="Password changed successfully",
            ),
            400: OpenApiResponse(
                description="Current password incorrect or new password invalid"
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def post(self, request):
        serializer = serializers.PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        PasswordService.change_password(
            user=request.user,
            current_password=data["current_password"],
            new_password=data["new_password"],
            logout_other_sessions=True,
            request=request,
        )

        return Response({"message": "Password changed successfully"})


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================


class SessionListView(APIView):
    """
    List active sessions.

    GET /api/v1/auth/sessions/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List active sessions",
        description="""
        Get a list of all active sessions (devices) for the current user.

        **Response includes:**
        - Device information (name, type, ID)
        - IP address and approximate location
        - Last activity timestamp
        - Whether it's the current session

        Users can use this to monitor account access and identify suspicious sessions.
        """,
        tags=["Session Management"],
        responses={
            200: OpenApiResponse(
                response=serializers.DeviceSessionSerializer(many=True),
                description="List of active sessions",
            ),
            401: OpenApiResponse(description="Not authenticated"),
        },
    )
    def get(self, request):
        sessions = DeviceSession.objects.filter(
            user=request.user, is_active=True
        ).order_by("-last_activity")

        serializer = serializers.DeviceSessionSerializer(
            sessions, many=True, context={"request": request}
        )

        return Response(serializer.data)


class SessionRevokeView(APIView):
    """
    Revoke a specific session.

    DELETE /api/v1/auth/sessions/<uuid:pk>/
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Revoke a session",
        description="""
        Revoke (log out) a specific session by its ID.

        Use this to remotely log out from another device.
        The session's refresh token is invalidated and access token JTI is blacklisted.
        """,
        tags=["Session Management"],
        parameters=[
            OpenApiParameter(
                name="pk",
                type=str,
                location=OpenApiParameter.PATH,
                description="Session UUID to revoke",
            )
        ],
        responses={
            200: OpenApiResponse(
                response=serializers.MessageSerializer,
                description="Session revoked successfully",
            ),
            401: OpenApiResponse(description="Not authenticated"),
            404: OpenApiResponse(description="Session not found"),
        },
    )
    def delete(self, request, pk):
        revoked = AuthService.revoke_session(
            user=request.user,
            session_id=str(pk),
            request=request,
        )

        if not revoked:
            return Response(
                {"message": "Session not found", "code": "not_found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"message": "Session revoked successfully"})


# =============================================================================
# OAUTH - GOOGLE
# =============================================================================


class GoogleOAuthView(APIView):
    """
    Start Google OAuth flow.

    GET /api/v1/auth/oauth/google/
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Start Google OAuth",
        description="""
        Initiate Google OAuth 2.0 authentication flow.

        **Flow:**
        1. Client calls this endpoint with optional redirect_to
        2. Backend returns Google authorization URL
        3. Client redirects user to Google
        4. After Google auth, user is redirected to callback endpoint
        5. Callback returns tokens or redirects with tokens in URL fragment

        **Security:**
        - Uses PKCE (Proof Key for Code Exchange)
        - State parameter prevents CSRF attacks
        """,
        tags=["OAuth"],
        parameters=[
            OpenApiParameter(
                name="redirect_to",
                type=str,
                location=OpenApiParameter.QUERY,
                description="URL to redirect to after OAuth completes",
                required=False,
            ),
            OpenApiParameter(
                name="device_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Device identifier for session tracking",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=serializers.OAuthInitResponseSerializer,
                description="Google authorization URL",
            ),
        },
    )
    def get(self, request):
        serializer = serializers.OAuthInitSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Create OAuth state
        state_params = OAuthStateManager.create_state(
            provider="google",
            redirect_to=data.get("redirect_to"),
            device_info={
                "device_id": data.get("device_id"),
                "device_type": data.get("device_type"),
                "device_name": data.get("device_name"),
            },
        )

        # Get authorization URL
        auth_url = GoogleOAuthBackend.get_authorization_url(state_params)

        return Response({"authorization_url": auth_url})


class GoogleOAuthCallbackView(APIView):
    """
    Google OAuth callback.

    GET /api/v1/auth/oauth/google/callback/
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Google OAuth callback",
        description="""
        Handle Google OAuth callback after user authorization.

        **This endpoint is called by Google, not directly by clients.**

        **Flow:**
        1. Google redirects here with authorization code
        2. Backend exchanges code for tokens
        3. Backend verifies ID token and extracts user info
        4. User is created (if new) or authenticated
        5. Backend redirects to frontend with tokens in URL fragment

        **New Users:**
        - Account is created with email from Google
        - Email is automatically marked as verified
        - Profile is populated with Google profile data
        """,
        tags=["OAuth"],
        parameters=[
            OpenApiParameter(
                name="code",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Authorization code from Google",
                required=True,
            ),
            OpenApiParameter(
                name="state",
                type=str,
                location=OpenApiParameter.QUERY,
                description="State parameter for CSRF verification",
                required=True,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=serializers.AuthResponseSerializer,
                description="Authentication successful (JSON response)",
            ),
            302: OpenApiResponse(description="Redirect to frontend with tokens"),
            400: OpenApiResponse(description="Invalid state or code"),
        },
    )
    def get(self, request):
        code = request.query_params.get("code")
        state = request.query_params.get("state")

        if not code or not state:
            return Response(
                {"message": "Missing code or state", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate and consume state
        state_data = OAuthStateManager.validate_and_consume_state(state)

        if state_data["provider"] != "google":
            return Response(
                {"message": "Invalid state provider", "code": "invalid_state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Exchange code for tokens
        tokens = GoogleOAuthBackend.exchange_code(
            code=code, code_verifier=state_data["code_verifier"]
        )

        # Verify ID token and get user info
        try:
            user_info = GoogleOAuthBackend.verify_id_token(tokens["id_token"])
        except Exception:
            # Fallback to access token
            user_info = GoogleOAuthBackend.get_user_info(tokens["access_token"])

        # Build device info from state
        device_data = state_data.get("device_info", {})
        device_info = _build_device_info(
            device_data, request, fallback_device_id=f"google_{user_info['sub'][:8]}"
        )

        # Authenticate or create user
        user, auth_tokens, session, is_new_user = (
            OAuthService.authenticate_or_create_user(
                provider="google",
                provider_uid=user_info["sub"],
                email=user_info["email"],
                email_verified=user_info.get("email_verified", False),
                provider_data=user_info,
                device_info=device_info,
                request=request,
            )
        )

        # Redirect to frontend with tokens
        redirect_to = state_data.get("redirect_to")
        if redirect_to:
            # Include tokens in URL fragment (not query params for security)
            from django.shortcuts import redirect

            return redirect(
                f"{redirect_to}#access_token={auth_tokens.access_token}"
                f"&expires_in={auth_tokens.access_expires_in}"
                f"&is_new_user={str(is_new_user).lower()}"
            )

        # Return JSON response
        response_data = {
            "user": user,
            "tokens": {
                "access_token": auth_tokens.access_token,
                "access_expires_in": auth_tokens.access_expires_in,
                "refresh_expires_in": auth_tokens.refresh_expires_in,
                "token_type": "Bearer",
            },
            "is_new_user": is_new_user,
        }

        return Response(serializers.AuthResponseSerializer(response_data).data)


# =============================================================================
# OAUTH - APPLE
# =============================================================================


class AppleOAuthView(APIView):
    """
    Start Apple OAuth flow.

    GET /api/v1/auth/oauth/apple/
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Start Apple OAuth",
        description="""
        Initiate Apple Sign In authentication flow.

        **Flow:**
        1. Client calls this endpoint with optional redirect_to
        2. Backend returns Apple authorization URL
        3. Client redirects user to Apple
        4. After Apple auth, user is redirected to callback endpoint (POST!)
        5. Callback returns tokens or redirects with tokens in URL fragment

        **Security:**
        - Uses PKCE (Proof Key for Code Exchange)
        - Nonce prevents replay attacks
        - State parameter prevents CSRF attacks

        **Note:** Apple uses form_post response mode, so callback is POST, not GET.
        """,
        tags=["OAuth"],
        parameters=[
            OpenApiParameter(
                name="redirect_to",
                type=str,
                location=OpenApiParameter.QUERY,
                description="URL to redirect to after OAuth completes",
                required=False,
            ),
            OpenApiParameter(
                name="device_id",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Device identifier for session tracking",
                required=False,
            ),
        ],
        responses={
            200: OpenApiResponse(
                response=serializers.OAuthInitResponseSerializer,
                description="Apple authorization URL",
            ),
        },
    )
    def get(self, request):
        serializer = serializers.OAuthInitSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Create OAuth state
        state_params = OAuthStateManager.create_state(
            provider="apple",
            redirect_to=data.get("redirect_to"),
            device_info={
                "device_id": data.get("device_id"),
                "device_type": data.get("device_type"),
                "device_name": data.get("device_name"),
            },
        )

        # Get authorization URL
        auth_url = AppleOAuthBackend.get_authorization_url(state_params)

        return Response({"authorization_url": auth_url})


class AppleOAuthCallbackView(APIView):
    """
    Apple OAuth callback.

    POST /api/v1/auth/oauth/apple/callback/
    (Apple uses form_post, not GET)
    """

    permission_classes = [AllowAny]

    @extend_schema(
        summary="Apple OAuth callback",
        description="""
        Handle Apple Sign In callback after user authorization.

        **This endpoint is called by Apple, not directly by clients.**

        Apple uses `form_post` response mode, so this endpoint accepts POST requests
        with form-encoded data (not JSON).

        **Important:** Apple only sends user data (name, email) on the FIRST authorization.
        Store this data immediately as it won't be sent again.

        **Flow:**
        1. Apple POSTs authorization data here
        2. Backend validates state and nonce
        3. Backend verifies ID token
        4. User is created (if new) or authenticated
        5. Backend redirects to frontend with tokens
        """,
        tags=["OAuth"],
        request=serializers.OAuthCallbackSerializer,
        responses={
            200: OpenApiResponse(
                response=serializers.AuthResponseSerializer,
                description="Authentication successful (JSON response)",
            ),
            302: OpenApiResponse(description="Redirect to frontend with tokens"),
            400: OpenApiResponse(description="Invalid state, nonce, or code"),
        },
    )
    def post(self, request):
        code = request.data.get("code")
        state = request.data.get("state")
        id_token = request.data.get("id_token")
        user_data = request.data.get("user")  # Only on first authorization

        if not code or not state:
            return Response(
                {"message": "Missing code or state", "code": "invalid_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate and consume state
        state_data = OAuthStateManager.validate_and_consume_state(state)

        if state_data["provider"] != "apple":
            return Response(
                {"message": "Invalid state provider", "code": "invalid_state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If we have id_token directly, verify it
        if id_token:
            user_info = AppleOAuthBackend.verify_id_token(
                id_token, expected_nonce=state_data["nonce"]
            )
        else:
            # Exchange code for tokens
            tokens = AppleOAuthBackend.exchange_code(
                code=code, code_verifier=state_data["code_verifier"]
            )

            # Verify ID token
            user_info = AppleOAuthBackend.verify_id_token(
                tokens["id_token"], expected_nonce=state_data["nonce"]
            )

        # Parse user data (only on first sign-in)
        extra_data = AppleOAuthBackend.parse_user_data(user_data)

        # Merge with user_info
        provider_data = {**user_info, **extra_data}

        # Build device info
        device_data = state_data.get("device_info", {})
        device_info = _build_device_info(
            device_data, request, fallback_device_id=f"apple_{user_info['sub'][:8]}"
        )

        # Authenticate or create user
        user, auth_tokens, session, is_new_user = (
            OAuthService.authenticate_or_create_user(
                provider="apple",
                provider_uid=user_info["sub"],
                email=user_info.get("email", ""),
                email_verified=user_info.get("email_verified", False),
                provider_data=provider_data,
                device_info=device_info,
                request=request,
            )
        )

        # Redirect to frontend
        redirect_to = state_data.get("redirect_to")

        if redirect_to:
            from django.shortcuts import redirect

            return redirect(
                f"{redirect_to}#access_token={auth_tokens.access_token}"
                f"&expires_in={auth_tokens.access_expires_in}"
                f"&is_new_user={str(is_new_user).lower()}"
            )

        # Return JSON response
        response_data = {
            "user": user,
            "tokens": {
                "access_token": auth_tokens.access_token,
                "access_expires_in": auth_tokens.access_expires_in,
                "refresh_expires_in": auth_tokens.refresh_expires_in,
                "token_type": "Bearer",
            },
            "is_new_user": is_new_user,
        }

        return Response(serializers.AuthResponseSerializer(response_data).data)


# =============================================================================
# GOVERNANCE STEP-UP AUTH
# =============================================================================


class GovernancePasswordAuthView(APIView):
    """
    Step-up authentication via password re-entry.

    POST /api/v1/auth/governance/authenticate/

    Requires standard authentication (IsAuthenticated).
    Returns a short-lived governance-scoped JWT.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=serializers.GovernancePasswordAuthSerializer,
        responses={200: serializers.GovernanceTokenResponseSerializer},
        tags=["Governance Auth"],
    )
    def post(self, request):
        serializer = serializers.GovernancePasswordAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = GovernanceAuthService.authenticate_with_password(
            user=request.user,
            password=serializer.validated_data["password"],
            request=request,
        )

        return Response(
            {
                "access": token.access_token,
                "expires_in": token.expires_in,
            }
        )


class GovernanceOTPSendView(APIView):
    """
    Send governance OTP code to user's email.

    POST /api/v1/auth/governance/otp/send/

    Requires standard authentication. No request body needed.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: inline_serializer("GovernanceOTPSendResponse", fields={})},
        tags=["Governance Auth"],
    )
    def post(self, request):
        GovernanceAuthService.send_otp(
            user=request.user,
            request=request,
        )

        return Response(
            {"message": "Governance OTP sent to your email"},
            status=status.HTTP_200_OK,
        )


class GovernanceOTPVerifyView(APIView):
    """
    Verify governance OTP code and issue governance token.

    POST /api/v1/auth/governance/otp/verify/

    Requires standard authentication.
    Returns a short-lived governance-scoped JWT.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=serializers.GovernanceOTPVerifySerializer,
        responses={200: serializers.GovernanceTokenResponseSerializer},
        tags=["Governance Auth"],
    )
    def post(self, request):
        serializer = serializers.GovernanceOTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = GovernanceAuthService.verify_otp(
            user=request.user,
            code=serializer.validated_data["code"],
            request=request,
        )

        return Response(
            {
                "access": token.access_token,
                "expires_in": token.expires_in,
            }
        )
