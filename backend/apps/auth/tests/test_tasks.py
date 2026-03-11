# apps/auth/tests/test_tasks.py
"""
Tests for Auth Celery tasks.

Tests cover:
    - cleanup_expired_tokens: Periodic cleanup of expired/used tokens
    - cleanup_inactive_sessions: Cleanup of old inactive device sessions
    - revoke_user_tokens: Bulk revocation of all user tokens and sessions
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.auth.models import (
    RefreshToken,
    DeviceSession,
    EmailVerificationToken,
    PasswordResetToken,
)
from apps.auth.tasks import (
    cleanup_expired_tokens,
    cleanup_inactive_sessions,
    revoke_user_tokens,
)
from apps.auth.tests.factories import (
    RefreshTokenFactory,
    ExpiredRefreshTokenFactory,
    DeviceSessionFactory,
    EmailVerificationTokenFactory,
    ExpiredVerificationTokenFactory,
    UsedVerificationTokenFactory,
    PasswordResetTokenFactory,
    ExpiredPasswordResetTokenFactory,
    UsedPasswordResetTokenFactory,
)
from apps.users.tests.factories import UserFactory


# =============================================================================
# cleanup_expired_tokens
# =============================================================================


class TestCleanupExpiredTokens:
    """Tests for the cleanup_expired_tokens Celery task."""

    @pytest.mark.django_db
    def test_deletes_refresh_tokens_expired_more_than_7_days_ago(self):
        """Refresh tokens expired 8+ days ago should be deleted."""
        old_token = RefreshTokenFactory(
            expires_at=timezone.now() - timedelta(days=8),
        )

        cleanup_expired_tokens()

        assert not RefreshToken.objects.filter(pk=old_token.pk).exists()

    @pytest.mark.django_db
    def test_keeps_refresh_tokens_expired_less_than_7_days_ago(self):
        """Refresh tokens expired less than 7 days ago are kept for audit trail."""
        recent_expired = ExpiredRefreshTokenFactory(
            expires_at=timezone.now() - timedelta(days=3),
        )

        cleanup_expired_tokens()

        assert RefreshToken.objects.filter(pk=recent_expired.pk).exists()

    @pytest.mark.django_db
    def test_keeps_non_expired_refresh_tokens(self):
        """Active, non-expired refresh tokens must not be deleted."""
        active_token = RefreshTokenFactory()  # default: expires in 7 days

        cleanup_expired_tokens()

        assert RefreshToken.objects.filter(pk=active_token.pk).exists()

    @pytest.mark.django_db
    def test_deletes_expired_verification_tokens_past_cutoff(self):
        """Verification tokens expired beyond the 7-day cutoff should be deleted."""
        old_verification = ExpiredVerificationTokenFactory(
            expires_at=timezone.now() - timedelta(days=8),
        )

        cleanup_expired_tokens()

        assert not EmailVerificationToken.objects.filter(pk=old_verification.pk).exists()

    @pytest.mark.django_db
    def test_deletes_used_verification_tokens_past_cutoff(self):
        """Used verification tokens with used_at beyond the cutoff should be deleted."""
        used_verification = UsedVerificationTokenFactory(
            used_at=timezone.now() - timedelta(days=8),
        )

        cleanup_expired_tokens()

        assert not EmailVerificationToken.objects.filter(pk=used_verification.pk).exists()

    @pytest.mark.django_db
    def test_deletes_expired_password_reset_tokens_past_cutoff(self):
        """Password reset tokens expired beyond the 7-day cutoff should be deleted."""
        old_reset = ExpiredPasswordResetTokenFactory(
            expires_at=timezone.now() - timedelta(days=8),
        )

        cleanup_expired_tokens()

        assert not PasswordResetToken.objects.filter(pk=old_reset.pk).exists()

    @pytest.mark.django_db
    def test_deletes_used_password_reset_tokens_past_cutoff(self):
        """Used password reset tokens with used_at beyond the cutoff should be deleted."""
        used_reset = UsedPasswordResetTokenFactory(
            used_at=timezone.now() - timedelta(days=8),
        )

        cleanup_expired_tokens()

        assert not PasswordResetToken.objects.filter(pk=used_reset.pk).exists()

    @pytest.mark.django_db
    def test_returns_correct_counts(self):
        """Task should return a dict with accurate deletion counts."""
        user = UserFactory()

        # 2 old refresh tokens (past cutoff)
        RefreshTokenFactory(
            user=user,
            expires_at=timezone.now() - timedelta(days=8),
        )
        RefreshTokenFactory(
            expires_at=timezone.now() - timedelta(days=10),
        )

        # 1 active refresh token (should be kept)
        RefreshTokenFactory()

        # 1 old expired verification token
        ExpiredVerificationTokenFactory(
            expires_at=timezone.now() - timedelta(days=8),
        )

        # 1 old used password reset token
        UsedPasswordResetTokenFactory(
            used_at=timezone.now() - timedelta(days=8),
        )

        result = cleanup_expired_tokens()

        assert result['refresh_tokens_deleted'] == 2
        assert result['verification_tokens_deleted'] == 1
        assert result['password_reset_tokens_deleted'] == 1


# =============================================================================
# cleanup_inactive_sessions
# =============================================================================


class TestCleanupInactiveSessions:
    """Tests for the cleanup_inactive_sessions Celery task."""

    @pytest.mark.django_db
    def test_deletes_inactive_sessions_with_old_last_activity(self):
        """Inactive sessions with last_activity > 30 days ago should be deleted."""
        session = DeviceSessionFactory(is_active=False)
        # Bypass auto_now on last_activity
        DeviceSession.objects.filter(pk=session.pk).update(
            last_activity=timezone.now() - timedelta(days=31),
        )

        cleanup_inactive_sessions()

        assert not DeviceSession.objects.filter(pk=session.pk).exists()

    @pytest.mark.django_db
    def test_keeps_inactive_sessions_with_recent_last_activity(self):
        """Inactive sessions with last_activity < 30 days ago are kept."""
        session = DeviceSessionFactory(is_active=False)
        # last_activity is auto_now, so it will be ~now which is < 30 days

        cleanup_inactive_sessions()

        assert DeviceSession.objects.filter(pk=session.pk).exists()

    @pytest.mark.django_db
    def test_keeps_active_sessions_even_with_old_last_activity(self):
        """Active sessions must NOT be deleted regardless of last_activity age."""
        session = DeviceSessionFactory(is_active=True)
        # Bypass auto_now to set old last_activity
        DeviceSession.objects.filter(pk=session.pk).update(
            last_activity=timezone.now() - timedelta(days=60),
        )

        cleanup_inactive_sessions()

        assert DeviceSession.objects.filter(pk=session.pk).exists()

    @pytest.mark.django_db
    def test_returns_correct_count(self):
        """Task should return a dict with the accurate deletion count."""
        # 2 old inactive sessions (should be deleted)
        s1 = DeviceSessionFactory(is_active=False)
        s2 = DeviceSessionFactory(is_active=False)
        DeviceSession.objects.filter(pk__in=[s1.pk, s2.pk]).update(
            last_activity=timezone.now() - timedelta(days=45),
        )

        # 1 active session with old activity (should be kept)
        s3 = DeviceSessionFactory(is_active=True)
        DeviceSession.objects.filter(pk=s3.pk).update(
            last_activity=timezone.now() - timedelta(days=45),
        )

        result = cleanup_inactive_sessions()

        assert result['sessions_deleted'] == 2

    @pytest.mark.django_db
    def test_does_not_affect_other_users_sessions(self):
        """Each user's sessions are handled independently; deletions of one
        user's inactive sessions must not affect another user's sessions."""
        user_a = UserFactory()
        user_b = UserFactory()

        # user_a: old inactive session (should be deleted)
        sa = DeviceSessionFactory(user=user_a, is_active=False)
        DeviceSession.objects.filter(pk=sa.pk).update(
            last_activity=timezone.now() - timedelta(days=31),
        )

        # user_b: old active session (should be kept)
        sb = DeviceSessionFactory(user=user_b, is_active=True)
        DeviceSession.objects.filter(pk=sb.pk).update(
            last_activity=timezone.now() - timedelta(days=31),
        )

        # user_b: recent inactive session (should be kept)
        sc = DeviceSessionFactory(
            user=user_b,
            device_id="device_other",
            is_active=False,
        )

        cleanup_inactive_sessions()

        assert not DeviceSession.objects.filter(pk=sa.pk).exists()
        assert DeviceSession.objects.filter(pk=sb.pk).exists()
        assert DeviceSession.objects.filter(pk=sc.pk).exists()


# =============================================================================
# revoke_user_tokens
# =============================================================================


class TestRevokeUserTokens:
    """Tests for the revoke_user_tokens Celery task."""

    @pytest.mark.django_db
    def test_revokes_all_active_tokens_for_user(self):
        """All non-revoked refresh tokens for the user should be revoked."""
        user = UserFactory()
        t1 = RefreshTokenFactory(user=user, is_revoked=False)
        t2 = RefreshTokenFactory(user=user, is_revoked=False)

        revoke_user_tokens(user.id)

        t1.refresh_from_db()
        t2.refresh_from_db()
        assert t1.is_revoked is True
        assert t1.revoked_reason == 'security'
        assert t1.revoked_at is not None
        assert t2.is_revoked is True

    @pytest.mark.django_db
    def test_deactivates_all_active_sessions_for_user(self):
        """All active device sessions for the user should be deactivated."""
        user = UserFactory()
        s1 = DeviceSessionFactory(user=user, is_active=True)
        s2 = DeviceSessionFactory(
            user=user,
            device_id="device_second",
            is_active=True,
        )

        revoke_user_tokens(user.id)

        s1.refresh_from_db()
        s2.refresh_from_db()
        assert s1.is_active is False
        assert s2.is_active is False

    @pytest.mark.django_db
    def test_does_not_affect_other_users_tokens(self):
        """Revoking one user's tokens must not touch another user's tokens."""
        user = UserFactory()
        other_user = UserFactory()
        RefreshTokenFactory(user=user, is_revoked=False)
        other_token = RefreshTokenFactory(user=other_user, is_revoked=False)

        revoke_user_tokens(user.id)

        other_token.refresh_from_db()
        assert other_token.is_revoked is False

    @pytest.mark.django_db
    def test_does_not_affect_other_users_sessions(self):
        """Revoking one user's sessions must not touch another user's sessions."""
        user = UserFactory()
        other_user = UserFactory()
        DeviceSessionFactory(user=user, is_active=True)
        other_session = DeviceSessionFactory(user=other_user, is_active=True)

        revoke_user_tokens(user.id)

        other_session.refresh_from_db()
        assert other_session.is_active is True

    @pytest.mark.django_db
    def test_returns_correct_counts(self):
        """Task should return accurate counts of revoked tokens and deactivated sessions."""
        user = UserFactory()
        RefreshTokenFactory(user=user, is_revoked=False)
        RefreshTokenFactory(user=user, is_revoked=False)
        DeviceSessionFactory(user=user, is_active=True)
        DeviceSessionFactory(
            user=user,
            device_id="device_second",
            is_active=True,
        )

        result = revoke_user_tokens(user.id)

        assert result['tokens_revoked'] == 2
        assert result['sessions_deactivated'] == 2

    @pytest.mark.django_db
    def test_handles_user_with_no_tokens_or_sessions(self):
        """Calling revoke for a user with no tokens/sessions should return zeros."""
        user = UserFactory()

        result = revoke_user_tokens(user.id)

        assert result['tokens_revoked'] == 0
        assert result['sessions_deactivated'] == 0
