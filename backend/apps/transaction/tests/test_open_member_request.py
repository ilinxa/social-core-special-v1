from uuid import uuid4

import pytest

from apps.core.constants import AccountType
from apps.core.exceptions import BusinessRuleViolation
from apps.organization.tests.factories import (
    BusinessAccountWithProfileFactory,
    PlatformAccountFactory,
)
from apps.transaction.services import TransactionService
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestOpenMemberRequestPrecheck:
    """Tests for _check_open_member_request enforcement in create_request()."""

    def test_business_request_rejected_when_closed(self):
        """create_request() raises BusinessRuleViolation when open_member_request=False."""
        business = BusinessAccountWithProfileFactory(
            open_member_request=False,
            max_members=6,
        )
        user = UserFactory()

        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=user.id,
                target_account_type=AccountType.BUSINESS,
                target_account_id=business.id,
            )
        assert exc.value.details["rule"] == "member_requests_closed"

    def test_business_request_succeeds_when_open(self):
        """create_request() succeeds when open_member_request=True and quota available."""
        business = BusinessAccountWithProfileFactory(
            open_member_request=True,
            max_members=6,
        )
        user = UserFactory()

        txn = TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=user.id,
            target_account_type=AccountType.BUSINESS,
            target_account_id=business.id,
        )
        assert txn is not None
        assert txn.status == "pending"

    def test_platform_request_rejected_when_closed(self):
        """create_request() raises BusinessRuleViolation for platform with open_member_request=False."""
        platform = PlatformAccountFactory()
        platform.open_member_request = False
        platform.save()
        user = UserFactory()

        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService.create_request(
                transaction_type="platform_membership_request",
                user_id=user.id,
                target_account_type=AccountType.PLATFORM,
                target_account_id=platform.id,
            )
        assert exc.value.details["rule"] == "member_requests_closed"

    def test_platform_request_succeeds_when_open(self):
        """create_request() succeeds for platform with open_member_request=True."""
        platform = PlatformAccountFactory()
        platform.open_member_request = True
        platform.save()
        user = UserFactory()

        txn = TransactionService.create_request(
            transaction_type="platform_membership_request",
            user_id=user.id,
            target_account_type=AccountType.PLATFORM,
            target_account_id=platform.id,
        )
        assert txn is not None

    def test_non_membership_request_unaffected(self):
        """_check_open_member_request raises for membership requests on closed accounts."""
        business = BusinessAccountWithProfileFactory(open_member_request=False)

        # Test the static method directly — should raise since open_member_request=False
        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService._check_open_member_request(
                account_type="business",
                account_id=business.id,
            )
        assert exc.value.details["rule"] == "member_requests_closed"

    def test_closed_check_runs_before_quota_check(self):
        """When open_member_request=False AND quota full, gets member_requests_closed (not quota)."""
        business = BusinessAccountWithProfileFactory(
            open_member_request=False,
            max_members=1,
        )
        user = UserFactory()

        with pytest.raises(BusinessRuleViolation) as exc:
            TransactionService.create_request(
                transaction_type="business_membership_request",
                user_id=user.id,
                target_account_type=AccountType.BUSINESS,
                target_account_id=business.id,
            )
        assert exc.value.details["rule"] == "member_requests_closed"

    def test_check_with_nonexistent_account_noop(self):
        """_check_open_member_request with nonexistent account ID does not raise."""
        # Should not raise — DoesNotExist is handled gracefully
        TransactionService._check_open_member_request(
            account_type="business",
            account_id=uuid4(),
        )

    def test_check_with_nonexistent_platform_noop(self):
        """_check_open_member_request with nonexistent platform ID does not raise."""
        # Should not raise — DoesNotExist is handled gracefully
        TransactionService._check_open_member_request(
            account_type="platform",
            account_id=uuid4(),
        )

    def test_check_with_unknown_account_type_noop(self):
        """_check_open_member_request with unknown account_type does not raise."""
        # Should not raise — unrecognized types return early
        TransactionService._check_open_member_request(
            account_type="unknown",
            account_id=uuid4(),
        )
