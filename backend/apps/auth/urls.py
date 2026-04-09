"""
Auth URLs
=========
URL configuration for authentication endpoints.

Base URL: /api/v1/auth/

Endpoints:
    Core Auth:
        POST /register/              - Create account
        POST /login/                 - Get tokens
        POST /logout/                - Revoke current session
        POST /logout-all/            - Revoke all sessions
        POST /refresh/               - Rotate tokens

    Email Verification:
        POST /verify-email/          - Verify with 6-digit code
        GET  /verify-email/<uuid>/   - Verify with magic link
        POST /resend-verification/   - Resend verification email

    Password:
        POST /password/reset/        - Request password reset
        POST /password/reset/confirm/ - Confirm reset with new password
        POST /password/change/       - Change password (authenticated)

    Sessions:
        GET    /sessions/            - List active sessions
        DELETE /sessions/<uuid>/     - Revoke specific session

    OAuth:
        GET  /oauth/google/          - Start Google OAuth
        GET  /oauth/google/callback/ - Google OAuth callback
        GET  /oauth/apple/           - Start Apple OAuth
        POST /oauth/apple/callback/  - Apple OAuth callback (POST!)
"""

from django.urls import path

from apps.auth import views

app_name = "authentication"

urlpatterns = [
    # Core auth
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("logout-all/", views.LogoutAllView.as_view(), name="logout-all"),
    path("refresh/", views.RefreshView.as_view(), name="refresh"),
    # Email verification
    path(
        "verify-email/", views.VerifyEmailCodeView.as_view(), name="verify-email-code"
    ),
    path(
        "verify-email/<uuid:token>/",
        views.VerifyEmailLinkView.as_view(),
        name="verify-email-link",
    ),
    path(
        "resend-verification/",
        views.ResendVerificationView.as_view(),
        name="resend-verification",
    ),
    # Password
    path(
        "password/reset/",
        views.PasswordResetRequestView.as_view(),
        name="password-reset",
    ),
    path(
        "password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path(
        "password/change/", views.PasswordChangeView.as_view(), name="password-change"
    ),
    # Sessions
    path("sessions/", views.SessionListView.as_view(), name="sessions"),
    path(
        "sessions/<uuid:pk>/", views.SessionRevokeView.as_view(), name="session-revoke"
    ),
    # OAuth
    path("oauth/google/", views.GoogleOAuthView.as_view(), name="oauth-google"),
    path(
        "oauth/google/callback/",
        views.GoogleOAuthCallbackView.as_view(),
        name="oauth-google-callback",
    ),
    path("oauth/apple/", views.AppleOAuthView.as_view(), name="oauth-apple"),
    path(
        "oauth/apple/callback/",
        views.AppleOAuthCallbackView.as_view(),
        name="oauth-apple-callback",
    ),
    # Governance step-up auth
    path(
        "governance/authenticate/",
        views.GovernancePasswordAuthView.as_view(),
        name="governance-auth",
    ),
    path(
        "governance/otp/send/",
        views.GovernanceOTPSendView.as_view(),
        name="governance-otp-send",
    ),
    path(
        "governance/otp/verify/",
        views.GovernanceOTPVerifyView.as_view(),
        name="governance-otp-verify",
    ),
]
