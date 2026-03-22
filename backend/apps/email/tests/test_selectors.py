# apps/email/tests/test_selectors.py
"""
Tests for Email selectors.

Covers:
    - EmailTemplateSelector: template lookup, filtering, versioning, existence
    - EmailLogSelector: log lookup, status filtering, retry, bounce/complaint queries
"""

import uuid
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.email.models import EmailLog
from apps.email.selectors import EmailLogSelector, EmailTemplateSelector
from apps.email.tests.factories import (
    ArchivedEmailTemplateFactory,
    BouncedEmailLogFactory,
    ComplainedEmailLogFactory,
    EmailLogFactory,
    EmailTemplateFactory,
    FailedEmailLogFactory,
    InactiveEmailTemplateFactory,
    QueuedEmailLogFactory,
    SentEmailLogFactory,
)

# =============================================================================
# EMAIL TEMPLATE SELECTOR
# =============================================================================


@pytest.mark.django_db
class TestEmailTemplateSelector:
    """Tests for EmailTemplateSelector."""

    # ----- get_by_name -----

    def test_get_by_name_returns_current_active(self):
        """get_by_name returns the current active template matching the name."""
        template = EmailTemplateFactory(name="welcome", is_active=True, is_current=True)

        result = EmailTemplateSelector.get_by_name("welcome")

        assert result is not None
        assert result.pk == template.pk
        assert result.name == "welcome"
        assert result.is_active is True
        assert result.is_current is True

    def test_get_by_name_returns_none_for_nonexistent(self):
        """get_by_name returns None when no template matches the name."""
        result = EmailTemplateSelector.get_by_name("nonexistent_template")

        assert result is None

    def test_get_by_name_returns_none_for_inactive(self):
        """get_by_name returns None for inactive templates (is_active=False)."""
        InactiveEmailTemplateFactory(name="deactivated")

        result = EmailTemplateSelector.get_by_name("deactivated")

        assert result is None

    def test_get_by_name_returns_none_for_archived(self):
        """get_by_name returns None for archived templates (is_current=False)."""
        ArchivedEmailTemplateFactory(name="old_version")

        result = EmailTemplateSelector.get_by_name("old_version")

        assert result is None

    # ----- get_all_current -----

    def test_get_all_current(self):
        """get_all_current returns all templates with is_current=True."""
        t1 = EmailTemplateFactory(name="tpl_a")
        t2 = EmailTemplateFactory(name="tpl_b")
        # Archived should not appear
        ArchivedEmailTemplateFactory(name="tpl_c")

        result = EmailTemplateSelector.get_all_current()
        result_pks = set(result.values_list("pk", flat=True))

        assert t1.pk in result_pks
        assert t2.pk in result_pks
        assert result.count() == 2

    def test_get_all_current_excludes_archived(self):
        """get_all_current excludes templates that are not current versions."""
        EmailTemplateFactory(name="current_tpl")
        archived = ArchivedEmailTemplateFactory(name="archived_tpl")

        result = EmailTemplateSelector.get_all_current()
        result_pks = set(result.values_list("pk", flat=True))

        assert archived.pk not in result_pks

    # ----- get_by_category -----

    def test_get_by_category(self):
        """get_by_category returns current templates in the given category."""
        auth1 = EmailTemplateFactory(name="welcome", category="auth")
        auth2 = EmailTemplateFactory(name="password_reset", category="auth")
        EmailTemplateFactory(name="receipt", category="transactional")

        result = EmailTemplateSelector.get_by_category("auth")
        result_pks = set(result.values_list("pk", flat=True))

        assert auth1.pk in result_pks
        assert auth2.pk in result_pks
        assert result.count() == 2

    def test_get_by_category_empty(self):
        """get_by_category returns empty queryset for non-matching category."""
        EmailTemplateFactory(name="receipt", category="transactional")

        result = EmailTemplateSelector.get_by_category("marketing")

        assert result.count() == 0

    # ----- get_version_history -----

    def test_get_version_history(self):
        """get_version_history returns all versions of a template ordered by -version."""
        # Create multiple versions of the same template name
        v1 = ArchivedEmailTemplateFactory(name="versioned", version=1)
        v2 = ArchivedEmailTemplateFactory(name="versioned", version=2)
        v3 = EmailTemplateFactory(name="versioned", version=3)
        # Different template should not appear
        EmailTemplateFactory(name="other_tpl")

        result = list(EmailTemplateSelector.get_version_history("versioned"))

        assert len(result) == 3
        assert result[0].pk == v3.pk
        assert result[1].pk == v2.pk
        assert result[2].pk == v1.pk
        # Verify descending version order
        versions = [t.version for t in result]
        assert versions == [3, 2, 1]

    # ----- template_exists -----

    def test_template_exists_true(self):
        """template_exists returns True for a current template."""
        EmailTemplateFactory(name="exists_check")

        assert EmailTemplateSelector.template_exists("exists_check") is True

    def test_template_exists_false(self):
        """template_exists returns False when no current template matches."""
        ArchivedEmailTemplateFactory(name="archived_only")

        assert EmailTemplateSelector.template_exists("archived_only") is False
        assert EmailTemplateSelector.template_exists("never_created") is False


# =============================================================================
# EMAIL LOG SELECTOR
# =============================================================================


@pytest.mark.django_db
class TestEmailLogSelector:
    """Tests for EmailLogSelector."""

    # ----- get_by_id -----

    def test_get_by_id_found(self):
        """get_by_id returns the log entry matching the given UUID."""
        log = EmailLogFactory()

        result = EmailLogSelector.get_by_id(str(log.id))

        assert result is not None
        assert result.pk == log.pk

    def test_get_by_id_not_found(self):
        """get_by_id returns None for a non-existent UUID."""
        fake_id = str(uuid.uuid4())

        result = EmailLogSelector.get_by_id(fake_id)

        assert result is None

    # ----- get_by_message_id -----

    def test_get_by_message_id_found(self):
        """get_by_message_id returns the log matching the provider message ID."""
        log = SentEmailLogFactory(message_id="ses-abc-123")

        result = EmailLogSelector.get_by_message_id("ses-abc-123")

        assert result is not None
        assert result.pk == log.pk
        assert result.message_id == "ses-abc-123"

    def test_get_by_message_id_not_found(self):
        """get_by_message_id returns None for a non-existent message ID."""
        result = EmailLogSelector.get_by_message_id("ses-nonexistent")

        assert result is None

    # ----- get_by_email -----

    def test_get_by_email_returns_matching(self):
        """get_by_email returns logs for the given recipient email address."""
        target = "user@example.com"
        log1 = EmailLogFactory(to_email=target)
        log2 = EmailLogFactory(to_email=target)
        EmailLogFactory(to_email="other@example.com")

        result = EmailLogSelector.get_by_email(target)
        result_pks = {entry.pk for entry in result}

        assert log1.pk in result_pks
        assert log2.pk in result_pks
        assert len(result) == 2

    def test_get_by_email_respects_limit(self):
        """get_by_email returns at most `limit` records."""
        target = "limited@example.com"
        for _ in range(5):
            EmailLogFactory(to_email=target)

        result = EmailLogSelector.get_by_email(target, limit=3)

        assert len(result) == 3

    def test_get_by_email_ordered_by_created_at_desc(self):
        """get_by_email returns logs ordered by created_at descending (newest first)."""
        target = "ordered@example.com"
        now = timezone.now()
        old = EmailLogFactory(to_email=target, created_at=now - timedelta(hours=2))
        mid = EmailLogFactory(to_email=target, created_at=now - timedelta(hours=1))
        new = EmailLogFactory(to_email=target, created_at=now)

        result = list(EmailLogSelector.get_by_email(target))

        assert result[0].pk == new.pk
        assert result[1].pk == mid.pk
        assert result[2].pk == old.pk

    # ----- get_failed_for_retry -----

    def test_get_failed_for_retry(self):
        """get_failed_for_retry returns failed logs with retries remaining."""
        retryable = FailedEmailLogFactory(
            retry_count=1,
            max_retries=3,
            next_retry_at=timezone.now() + timedelta(minutes=5),
        )
        # Not failed -- should not appear
        SentEmailLogFactory()

        result = EmailLogSelector.get_failed_for_retry()
        result_pks = set(result.values_list("pk", flat=True))

        assert retryable.pk in result_pks

    def test_get_failed_for_retry_excludes_max_retries(self):
        """get_failed_for_retry excludes logs that have reached max_retries."""
        exhausted = FailedEmailLogFactory(
            retry_count=3,
            max_retries=3,
            next_retry_at=timezone.now(),
        )
        still_retryable = FailedEmailLogFactory(
            retry_count=2,
            max_retries=3,
            next_retry_at=timezone.now(),
        )

        result = EmailLogSelector.get_failed_for_retry()
        result_pks = set(result.values_list("pk", flat=True))

        assert exhausted.pk not in result_pks
        assert still_retryable.pk in result_pks

    # ----- get_pending -----

    def test_get_pending(self):
        """get_pending returns logs with PENDING or QUEUED status, ordered by created_at."""
        now = timezone.now()
        pending = EmailLogFactory(
            status=EmailLog.Status.PENDING,
            created_at=now - timedelta(minutes=10),
        )
        queued = QueuedEmailLogFactory(
            created_at=now - timedelta(minutes=5),
        )
        # Sent logs should not appear
        SentEmailLogFactory()

        result = list(EmailLogSelector.get_pending())
        result_pks = [entry.pk for entry in result]

        assert pending.pk in result_pks
        assert queued.pk in result_pks
        # Verify ordering: oldest created_at first
        assert result_pks.index(pending.pk) < result_pks.index(queued.pk)

    # ----- get_by_status -----

    def test_get_by_status(self):
        """get_by_status returns logs matching the given status within the time window."""
        sent_log = SentEmailLogFactory()
        FailedEmailLogFactory()

        result = EmailLogSelector.get_by_status(EmailLog.Status.SENT)
        result_pks = set(result.values_list("pk", flat=True))

        assert sent_log.pk in result_pks
        assert result.count() == 1

    def test_get_by_status_respects_days(self):
        """get_by_status excludes logs older than the specified number of days."""
        now = timezone.now()
        recent = SentEmailLogFactory()
        old = SentEmailLogFactory()
        # Backdate created_at via .update() to bypass auto_now_add
        EmailLog.objects.filter(pk=old.pk).update(created_at=now - timedelta(days=10))

        result = EmailLogSelector.get_by_status(EmailLog.Status.SENT, days=3)
        result_pks = set(result.values_list("pk", flat=True))

        assert recent.pk in result_pks
        assert old.pk not in result_pks

    # ----- get_bounced -----

    def test_get_bounced(self):
        """get_bounced returns bounced logs within the time window, ordered by -bounced_at."""
        now = timezone.now()
        bounce1 = BouncedEmailLogFactory(bounced_at=now - timedelta(days=1))
        bounce2 = BouncedEmailLogFactory(bounced_at=now - timedelta(hours=1))
        old_bounce = BouncedEmailLogFactory(bounced_at=now - timedelta(days=45))
        SentEmailLogFactory()
        # Backdate created_at via .update() to bypass auto_now_add
        EmailLog.objects.filter(pk=old_bounce.pk).update(
            created_at=now - timedelta(days=45)
        )

        result = list(EmailLogSelector.get_bounced())
        result_pks = [entry.pk for entry in result]

        assert bounce2.pk in result_pks
        assert bounce1.pk in result_pks
        assert old_bounce.pk not in result_pks
        # Verify ordering: newest bounced_at first
        assert result_pks.index(bounce2.pk) < result_pks.index(bounce1.pk)

    # ----- get_complained -----

    def test_get_complained(self):
        """get_complained returns complained logs within the time window, ordered by -complained_at."""
        now = timezone.now()
        complaint1 = ComplainedEmailLogFactory(
            complained_at=now - timedelta(days=2),
            created_at=now - timedelta(days=2),
        )
        complaint2 = ComplainedEmailLogFactory(
            complained_at=now - timedelta(hours=3),
            created_at=now - timedelta(hours=3),
        )
        # Old complaint outside default 30-day window
        old_complaint = ComplainedEmailLogFactory(
            complained_at=now - timedelta(days=60),
        )
        # Backdate created_at via .update() to bypass auto_now_add
        EmailLog.objects.filter(pk=old_complaint.pk).update(
            created_at=now - timedelta(days=60)
        )
        # Non-complained log should not appear
        SentEmailLogFactory()

        result = list(EmailLogSelector.get_complained())
        result_pks = [entry.pk for entry in result]

        assert complaint2.pk in result_pks
        assert complaint1.pk in result_pks
        assert old_complaint.pk not in result_pks
        # Verify ordering: newest complained_at first
        assert result_pks.index(complaint2.pk) < result_pks.index(complaint1.pk)
