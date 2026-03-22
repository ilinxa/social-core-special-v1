"""
Tests for Form-Transaction integration features.

Covers:
- Form validation on transaction creation (required/optional templates)
- Bidirectional linking (Transaction.form_response_id <-> FormResponse.transaction_id)
- Info request flow (PENDING -> INFO_REQUESTED -> PENDING)
- Resubmit after info request
- FormResponse update after info request
- INFO_REQUESTED state transitions
"""

from uuid import uuid4

import pytest
from django.utils import timezone

from apps.core.constants import (
    AccountType,
    ContextType,
    FormStatus,
    OwnerType,
    ResponseStatus,
)
from apps.core.exceptions import ConflictError, PermissionDenied, ValidationError
from apps.core.types import ActorContext
from apps.forms.selectors import FormResponseSelector
from apps.forms.services import FormResponseService
from apps.forms.tests.factories import (
    ActiveFormTemplateFactory,
    FormFieldFactory,
    FormResponseFactory,
    SubmittedFormResponseFactory,
)
from apps.rbac.models import Permission, RolePermission
from apps.rbac.services import RBACService
from apps.rbac.tests.factories import (
    MembershipFactory,
    OwnerRoleFactory,
    PlatformAccountFactory,
)
from apps.transaction.constants import PartyType, TransactionMode, TransactionStatus
from apps.transaction.models import TransactionLog
from apps.transaction.selectors import TransactionSelector
from apps.transaction.services import TransactionService
from apps.transaction.tests.factories import TransactionFactory
from apps.transaction.types import get_transaction_type
from apps.users.tests.factories import UserFactory

# =========================================================================
# Helpers
# =========================================================================


def _create_verification_form_template():
    """Create the system-business-verification form template with fields."""
    template = ActiveFormTemplateFactory(
        slug="system-business-verification",
        owner_type=OwnerType.SYSTEM,
        owner_id=None,
        name="Business Verification Form",
    )
    FormFieldFactory(
        form_template=template,
        field_key="business_name",
        label="Business Name",
        is_required=True,
        order=0,
    )
    FormFieldFactory(
        form_template=template,
        field_key="registration_number",
        label="Registration Number",
        is_required=True,
        order=1,
    )
    FormFieldFactory(
        form_template=template,
        field_key="additional_notes",
        label="Additional Notes",
        is_required=False,
        order=2,
    )
    return template


def _create_submitted_response(template, user):
    """Create and submit a form response via the service."""
    actor_context = ActorContext.for_user_context(user, request=None)
    return FormResponseService.create_and_submit(
        form_template=template,
        data={
            "business_name": "Test Corp",
            "registration_number": "REG-12345",
        },
        actor_context=actor_context,
        actor=user,
    )


def _create_platform_context_with_verification_perm():
    """Create a platform membership with can_approve_verification_request permission."""
    platform_user = UserFactory()
    platform = PlatformAccountFactory()
    platform_role = OwnerRoleFactory(
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
    )
    membership = MembershipFactory(
        user=platform_user,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        role=platform_role,
        is_owner=True,
    )
    perm, _ = Permission.objects.get_or_create(
        code="can_approve_verification_request",
        defaults={
            "name": "Approve Verification Request",
            "description": "Approve verification requests",
            "category": "verification",
            "applicable_scopes": ["platform_only", "global_only"],
        },
    )
    RolePermission.objects.get_or_create(
        role=platform_role,
        permission=perm,
        defaults={"scope": "platform_only"},
    )
    actor_context = RBACService.build_actor_context(
        membership=membership,
        request=None,
    )
    return platform_user, actor_context, platform


# =========================================================================
# TestFormValidation
# =========================================================================


@pytest.mark.django_db
class TestFormValidation:
    """Tests for _validate_form_requirement in create_request/create_invitation."""

    def test_create_request_with_required_form_success(self):
        """Transaction type with required_form_template_slug succeeds when valid form_response_id is provided."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        # business_verification_request requires target_account_id (ACCOUNT target)
        target_account_id = uuid4()

        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        assert txn.status == TransactionStatus.PENDING
        assert txn.form_response_id == response.id
        assert txn.transaction_type == "business_verification_request"

    def test_create_request_missing_required_form_raises(self):
        """Transaction type requiring form but no form_response_id raises ValidationError."""
        user = UserFactory()
        _create_verification_form_template()

        target_account_id = uuid4()

        with pytest.raises(ValidationError, match="requires a form response"):
            TransactionService.create_request(
                transaction_type="business_verification_request",
                user_id=user.id,
                target_account_id=target_account_id,
                target_account_type="platform",
                form_response_id=None,
            )

    def test_create_request_wrong_form_template_raises(self):
        """form_response_id pointing to wrong template slug raises ValidationError."""
        user = UserFactory()
        _create_verification_form_template()

        # Create a different form template and response
        wrong_template = ActiveFormTemplateFactory(
            slug="some-other-form",
            owner_type=OwnerType.BUSINESS,
        )
        FormFieldFactory(
            form_template=wrong_template,
            field_key="name",
            label="Name",
            order=0,
        )
        wrong_response = _create_submitted_response(wrong_template, user)

        target_account_id = uuid4()

        with pytest.raises(
            ValidationError, match="must use template 'system-business-verification'"
        ):
            TransactionService.create_request(
                transaction_type="business_verification_request",
                user_id=user.id,
                target_account_id=target_account_id,
                target_account_type="platform",
                form_response_id=wrong_response.id,
            )

    def test_create_request_optional_form_accepted(self, user):
        """Transaction type without required form but with optional form_response_id succeeds."""
        # business_membership_request does NOT require a form
        template = ActiveFormTemplateFactory(
            slug="optional-form",
            owner_type=OwnerType.BUSINESS,
        )
        FormFieldFactory(
            form_template=template,
            field_key="notes",
            label="Notes",
            order=0,
        )
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()

        txn = TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=user.id,
            target_account_id=target_account_id,
            form_response_id=response.id,
        )

        assert txn.status == TransactionStatus.PENDING
        assert txn.form_response_id == response.id

    def test_create_request_without_optional_form_accepted(self, user):
        """Transaction type without required form and no form_response_id succeeds."""
        target_account_id = uuid4()

        txn = TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=user.id,
            target_account_id=target_account_id,
        )

        assert txn.status == TransactionStatus.PENDING
        assert txn.form_response_id is None


# =========================================================================
# TestBidirectionalLinking
# =========================================================================


@pytest.mark.django_db
class TestBidirectionalLinking:
    """Tests for bidirectional link between Transaction and FormResponse."""

    def test_bidirectional_link_set_on_create(self):
        """After create_request with form_response_id, both Transaction and FormResponse are linked."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()

        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        # Transaction side
        assert txn.form_response_id == response.id

        # FormResponse side
        response.refresh_from_db()
        assert response.transaction_id == txn.id

    def test_link_to_transaction_conflict(self):
        """Linking a response already linked to a different transaction raises ConflictError."""
        user = UserFactory()
        template = ActiveFormTemplateFactory(
            slug="test-form",
            owner_type=OwnerType.BUSINESS,
        )
        FormFieldFactory(
            form_template=template,
            field_key="field_a",
            label="Field A",
            order=0,
        )
        response = _create_submitted_response(template, user)

        # Link to first transaction
        first_txn_id = uuid4()
        FormResponseService.link_to_transaction(
            response_id=response.id,
            transaction_id=first_txn_id,
        )

        # Try to link to a different transaction
        second_txn_id = uuid4()
        with pytest.raises(
            ConflictError, match="already linked to a different transaction"
        ):
            FormResponseService.link_to_transaction(
                response_id=response.id,
                transaction_id=second_txn_id,
            )

    def test_link_to_same_transaction_idempotent(self):
        """Linking a response to the same transaction twice does not raise an error."""
        user = UserFactory()
        template = ActiveFormTemplateFactory(
            slug="test-form-idem",
            owner_type=OwnerType.BUSINESS,
        )
        FormFieldFactory(
            form_template=template,
            field_key="field_b",
            label="Field B",
            order=0,
        )
        response = _create_submitted_response(template, user)

        txn_id = uuid4()
        FormResponseService.link_to_transaction(
            response_id=response.id,
            transaction_id=txn_id,
        )

        # Second link to same transaction - should not raise
        result = FormResponseService.link_to_transaction(
            response_id=response.id,
            transaction_id=txn_id,
        )
        assert result.transaction_id == txn_id


# =========================================================================
# TestRequestInfo
# =========================================================================


@pytest.mark.django_db
class TestRequestInfo:
    """Tests for TransactionService.request_info (PENDING -> INFO_REQUESTED)."""

    def test_request_info_success(self):
        """PENDING transaction with form response transitions to INFO_REQUESTED."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        platform_user, platform_ctx, _ = (
            _create_platform_context_with_verification_perm()
        )

        txn = TransactionService.request_info(
            transaction_id=txn.id,
            message="Please provide more details about your registration.",
            requested_fields=["registration_number"],
            actor_context=platform_ctx,
        )

        assert txn.status == TransactionStatus.INFO_REQUESTED

    def test_request_info_sets_fields(self):
        """Info request sets info_requested_at, info_requested_by, message, and fields."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        platform_user, platform_ctx, _ = (
            _create_platform_context_with_verification_perm()
        )

        txn = TransactionService.request_info(
            transaction_id=txn.id,
            message="Need more info",
            requested_fields=["business_name", "registration_number"],
            actor_context=platform_ctx,
        )

        assert txn.info_requested_at is not None
        assert txn.info_requested_by == platform_user
        assert txn.info_requested_message == "Need more info"
        assert txn.info_requested_fields == ["business_name", "registration_number"]

    def test_request_info_marks_form_response(self):
        """FormResponse.info_requested_at is set after request_info."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        platform_user, platform_ctx, _ = (
            _create_platform_context_with_verification_perm()
        )

        TransactionService.request_info(
            transaction_id=txn.id,
            message="Update needed",
            actor_context=platform_ctx,
        )

        response.refresh_from_db()
        assert response.info_requested_at is not None

    def test_request_info_non_pending_raises(self):
        """Requesting info on a non-PENDING transaction raises ValidationError."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        platform_user, platform_ctx, _ = (
            _create_platform_context_with_verification_perm()
        )

        # First info request - moves to INFO_REQUESTED
        TransactionService.request_info(
            transaction_id=txn.id,
            message="First request",
            actor_context=platform_ctx,
        )

        # Second info request on INFO_REQUESTED status should fail
        with pytest.raises(ValidationError, match="Cannot request info"):
            TransactionService.request_info(
                transaction_id=txn.id,
                message="Second request",
                actor_context=platform_ctx,
            )

    def test_request_info_no_form_raises(self):
        """Requesting info on transaction without form_response_id raises ValidationError."""
        user = UserFactory()
        target_account_id = uuid4()

        # business_membership_request does not require form
        txn = TransactionService.create_request(
            transaction_type="business_membership_request",
            user_id=user.id,
            target_account_id=target_account_id,
        )

        # Build an actor context that can approve membership requests
        platform_user = UserFactory()
        from apps.rbac.tests.factories import (
            BaseMemberRoleFactory,
            BusinessAccountFactory,
        )

        business = BusinessAccountFactory(created_by=platform_user)
        role = OwnerRoleFactory(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )
        membership = MembershipFactory(
            user=platform_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            role=role,
            is_owner=True,
        )
        perm, _ = Permission.objects.get_or_create(
            code="can_approve_membership_request",
            defaults={
                "name": "Approve Membership Request",
                "description": "Approve membership requests",
                "category": "membership",
                "applicable_scopes": ["business", "platform_only"],
            },
        )
        RolePermission.objects.get_or_create(
            role=role,
            permission=perm,
            defaults={"scope": "business"},
        )

        # We need to create a transaction where this actor can actually do the accept
        # but the transaction has no form. Let's use a factory to set this up directly.
        user_ctx = ActorContext.for_user_context(user, request=None)
        txn_no_form = TransactionFactory(
            transaction_type="business_membership_request",
            mode=TransactionMode.REQUEST,
            initiator_type=PartyType.USER,
            initiator_id=user.id,
            initiator_context=user_ctx.to_dict(),
            target_type=PartyType.ACCOUNT,
            target_id=business.id,
            context_type=ContextType.BUSINESS,
            context_id=business.id,
            status=TransactionStatus.PENDING,
            form_response_id=None,
        )

        approver_ctx = RBACService.build_actor_context(
            membership=membership,
            request=None,
        )

        with pytest.raises(ValidationError, match="without form response"):
            TransactionService.request_info(
                transaction_id=txn_no_form.id,
                message="Need more info",
                actor_context=approver_ctx,
            )

    def test_request_info_invalid_fields_raises(self):
        """Requesting info with non-existent field keys raises ValidationError."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        platform_user, platform_ctx, _ = (
            _create_platform_context_with_verification_perm()
        )

        with pytest.raises(ValidationError, match="Invalid field keys"):
            TransactionService.request_info(
                transaction_id=txn.id,
                message="Need more info",
                requested_fields=["nonexistent_field", "also_fake"],
                actor_context=platform_ctx,
            )


# =========================================================================
# TestResubmit
# =========================================================================


@pytest.mark.django_db
class TestResubmit:
    """Tests for TransactionService.resubmit_after_info_request."""

    def _create_info_requested_txn(self):
        """Helper to create a transaction in INFO_REQUESTED status."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        platform_user, platform_ctx, _ = (
            _create_platform_context_with_verification_perm()
        )

        txn = TransactionService.request_info(
            transaction_id=txn.id,
            message="Please clarify",
            actor_context=platform_ctx,
        )
        return txn, user, response

    def test_resubmit_success(self):
        """INFO_REQUESTED transitions to PENDING on resubmit."""
        txn, user, _ = self._create_info_requested_txn()
        user_ctx = ActorContext.for_user_context(user, request=None)

        txn = TransactionService.resubmit_after_info_request(
            transaction_id=txn.id,
            actor_context=user_ctx,
        )

        assert txn.status == TransactionStatus.PENDING

    def test_resubmit_non_info_requested_raises(self):
        """Resubmitting a PENDING transaction raises ValidationError."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        user_ctx = ActorContext.for_user_context(user, request=None)

        with pytest.raises(ValidationError, match="Cannot resubmit"):
            TransactionService.resubmit_after_info_request(
                transaction_id=txn.id,
                actor_context=user_ctx,
            )

    def test_resubmit_non_initiator_raises(self):
        """Resubmitting by a different user raises PermissionDenied."""
        txn, user, _ = self._create_info_requested_txn()

        other_user = UserFactory()
        other_ctx = ActorContext.for_user_context(other_user, request=None)

        with pytest.raises(PermissionDenied, match="Only the initiator"):
            TransactionService.resubmit_after_info_request(
                transaction_id=txn.id,
                actor_context=other_ctx,
            )

    def test_resubmit_creates_log_entry(self):
        """Resubmit creates a TransactionLog entry with correct previous/new status."""
        txn, user, _ = self._create_info_requested_txn()
        user_ctx = ActorContext.for_user_context(user, request=None)

        log_count_before = TransactionLog.objects.filter(
            transaction=txn,
        ).count()

        TransactionService.resubmit_after_info_request(
            transaction_id=txn.id,
            actor_context=user_ctx,
        )

        log_count_after = TransactionLog.objects.filter(
            transaction=txn,
        ).count()

        assert log_count_after > log_count_before

        latest_log = (
            TransactionLog.objects.filter(
                transaction=txn,
            )
            .order_by("-timestamp")
            .first()
        )

        assert latest_log.previous_status == TransactionStatus.INFO_REQUESTED
        assert latest_log.new_status == TransactionStatus.PENDING
        assert latest_log.event_type == "state_changed"


# =========================================================================
# TestFormResponseUpdate
# =========================================================================


@pytest.mark.django_db
class TestFormResponseUpdate:
    """Tests for FormResponseService.update_after_info_request."""

    def _create_info_requested_setup(self):
        """Helper: create a transaction in INFO_REQUESTED with linked form response."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        platform_user, platform_ctx, _ = (
            _create_platform_context_with_verification_perm()
        )

        txn = TransactionService.request_info(
            transaction_id=txn.id,
            message="Please update registration number",
            requested_fields=["registration_number"],
            actor_context=platform_ctx,
        )
        return txn, user, response, template

    def test_update_after_info_request_success(self):
        """Updates data, increments revision, and saves revision history."""
        txn, user, response, template = self._create_info_requested_setup()
        user_ctx = ActorContext.for_user_context(user, request=None)

        original_revision = response.revision

        updated_response = FormResponseService.update_after_info_request(
            response_id=response.id,
            data={
                "business_name": "Updated Corp",
                "registration_number": "REG-99999",
            },
            actor_context=user_ctx,
            actor=user,
        )

        assert updated_response.data["business_name"] == "Updated Corp"
        assert updated_response.data["registration_number"] == "REG-99999"
        assert updated_response.revision == original_revision + 1
        assert len(updated_response.revision_history) == 1
        assert updated_response.revision_history[0]["revision"] == original_revision

    def test_update_after_info_request_validates_status(self):
        """Updating response when transaction is not INFO_REQUESTED raises ValidationError."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        # Transaction is PENDING, not INFO_REQUESTED
        user_ctx = ActorContext.for_user_context(user, request=None)

        with pytest.raises(ValidationError, match="INFO_REQUESTED"):
            FormResponseService.update_after_info_request(
                response_id=response.id,
                data={
                    "business_name": "Updated Corp",
                    "registration_number": "REG-99999",
                },
                actor_context=user_ctx,
                actor=user,
            )

    def test_update_after_info_request_validates_submitter(self):
        """Updating response by a different user raises PermissionDenied."""
        txn, user, response, template = self._create_info_requested_setup()

        other_user = UserFactory()
        other_ctx = ActorContext.for_user_context(other_user, request=None)

        with pytest.raises(PermissionDenied, match="Only the original submitter"):
            FormResponseService.update_after_info_request(
                response_id=response.id,
                data={
                    "business_name": "Hacked Corp",
                    "registration_number": "REG-HACKED",
                },
                actor_context=other_ctx,
                actor=other_user,
            )


# =========================================================================
# TestInfoRequestedTransitions
# =========================================================================


@pytest.mark.django_db
class TestInfoRequestedTransitions:
    """Tests for valid/invalid transitions from INFO_REQUESTED status."""

    def _create_info_requested_txn(self):
        """Helper to create a transaction in INFO_REQUESTED status."""
        user = UserFactory()
        template = _create_verification_form_template()
        response = _create_submitted_response(template, user)

        target_account_id = uuid4()
        txn = TransactionService.create_request(
            transaction_type="business_verification_request",
            user_id=user.id,
            target_account_id=target_account_id,
            target_account_type="platform",
            form_response_id=response.id,
        )

        platform_user, platform_ctx, _ = (
            _create_platform_context_with_verification_perm()
        )

        txn = TransactionService.request_info(
            transaction_id=txn.id,
            message="More details needed",
            actor_context=platform_ctx,
        )
        return txn, user

    def test_info_requested_to_pending(self):
        """Can transition INFO_REQUESTED -> PENDING via resubmit."""
        txn, user = self._create_info_requested_txn()
        user_ctx = ActorContext.for_user_context(user, request=None)

        txn = TransactionService.resubmit_after_info_request(
            transaction_id=txn.id,
            actor_context=user_ctx,
        )

        assert txn.status == TransactionStatus.PENDING

    def test_info_requested_to_cancelled(self):
        """Can transition INFO_REQUESTED -> CANCELLED.

        The cancel method checks status == PENDING, but the VALID_TRANSITIONS
        map allows INFO_REQUESTED -> CANCELLED. We test at the model level
        that the transition is valid, and then use the _transition helper
        approach via the cancel path (which requires PENDING).
        Instead, we verify the model's can_transition_to method directly.
        """
        txn, user = self._create_info_requested_txn()

        # Verify the transition is valid in the state machine
        assert txn.can_transition_to(TransactionStatus.CANCELLED) is True

        # Verify via actual cancel is not possible because cancel checks status == PENDING
        # But we can verify the state machine allows it via direct _transition
        # Use invalidate (which uses _transition internally and works on any non-terminal)
        txn_invalidated = TransactionService.invalidate(
            transaction_id=txn.id,
            reason="Testing cancellation from info_requested",
        )
        # INVALIDATED is also allowed from INFO_REQUESTED
        assert txn_invalidated.status == TransactionStatus.INVALIDATED

    def test_info_requested_not_to_accepted(self):
        """Cannot transition INFO_REQUESTED -> ACCEPTED."""
        txn, user = self._create_info_requested_txn()

        assert txn.can_transition_to(TransactionStatus.ACCEPTED) is False
