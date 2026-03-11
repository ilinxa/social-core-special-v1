"""
Tests for the PENDING_REVIEW transaction flow.

Covers:
- Invitation acceptance with form mapping → PENDING_REVIEW + PENDING_APPROVAL membership
- Invitation acceptance without form mapping → ACCEPTED (unchanged behavior)
- Business approves PENDING_REVIEW → ACCEPTED + ACTIVE membership
- Business denies PENDING_REVIEW → DENIED + membership revoked
- Cancel from PENDING_REVIEW (by target and by initiator)
- Request info from PENDING_REVIEW → INFO_REQUESTED
- Resubmit from INFO_REQUESTED → PENDING_REVIEW (not PENDING)
- Error cases: approve wrong status, approve by non-member
- PENDING_APPROVAL membership counts toward quota
"""

import pytest
from uuid import uuid4

from apps.core.constants import AccountType, MembershipStatus, OwnerType
from apps.core.exceptions import ValidationError, PermissionDenied
from apps.core.types import ActorContext
from apps.forms.services import FormResponseService
from apps.forms.tests.factories import (
    ActiveFormTemplateFactory,
    FormFieldFactory,
)
from apps.rbac.models import Membership, Permission, Role, RolePermission
from apps.rbac.selectors import MembershipSelector
from apps.rbac.services import RBACService
from apps.rbac.tests.factories import (
    BusinessAccountFactory,
    BaseMemberRoleFactory,
    MembershipFactory,
    OwnerRoleFactory,
    PlatformAccountFactory,
)
from apps.transaction.constants import (
    TransactionMode,
    TransactionStatus,
    PartyType,
)
from apps.transaction.models import TransactionFormMapping
from apps.transaction.services import TransactionService
from apps.users.tests.factories import UserFactory


# =========================================================================
# Helpers
# =========================================================================


def _setup_business_with_owner():
    """Create a business with initialized RBAC (owner role, base member role, owner membership).

    Returns (owner, business, owner_membership, owner_actor_context).
    """
    owner = UserFactory()
    business = BusinessAccountFactory(created_by=owner)
    owner_membership = RBACService.initialize_business_account(
        business_id=business.id, owner=owner,
    )

    # Grant can_invite_member permission to owner role
    perm, _ = Permission.objects.get_or_create(
        code="can_invite_member",
        defaults={
            "name": "Invite Member",
            "description": "Invite new members",
            "category": "membership",
            "applicable_scopes": ["business", "platform_only", "global_only"],
        },
    )
    RolePermission.objects.get_or_create(
        role=owner_membership.role,
        permission=perm,
        defaults={"scope": "business"},
    )

    # Grant can_approve_membership_request permission to owner role
    approve_perm, _ = Permission.objects.get_or_create(
        code="can_approve_membership_request",
        defaults={
            "name": "Approve Membership Request",
            "description": "Approve membership requests",
            "category": "membership",
            "applicable_scopes": ["business", "platform_only"],
        },
    )
    RolePermission.objects.get_or_create(
        role=owner_membership.role,
        permission=approve_perm,
        defaults={"scope": "business"},
    )

    owner_ctx = RBACService.build_actor_context(
        membership=owner_membership, request=None,
    )
    return owner, business, owner_membership, owner_ctx


def _create_form_template_with_fields():
    """Create an active form template with fields for testing."""
    template = ActiveFormTemplateFactory(
        slug="membership-application-form",
        owner_type=OwnerType.BUSINESS,
        name="Membership Application Form",
    )
    FormFieldFactory(
        form_template=template,
        field_key="reason",
        label="Reason for Joining",
        is_required=True,
        order=0,
    )
    FormFieldFactory(
        form_template=template,
        field_key="experience",
        label="Experience",
        is_required=False,
        order=1,
    )
    return template


def _create_submitted_response(template, user):
    """Create and submit a form response via the service."""
    actor_context = ActorContext.for_user_context(user, request=None)
    return FormResponseService.create_and_submit(
        form_template=template,
        data={
            "reason": "I want to join this business",
            "experience": "5 years",
        },
        actor_context=actor_context,
        actor=user,
    )


def _create_form_mapping(business, template, is_required=True):
    """Create a TransactionFormMapping linking invitation type to form template."""
    return TransactionFormMapping.objects.create(
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        transaction_type="business_membership_invitation",
        form_template=template,
        is_required=is_required,
    )


def _create_invitation_and_accept_with_form(owner, business, owner_ctx, target_user, template):
    """Helper: create invitation, set up form mapping, target accepts with form response.

    Returns (txn, form_response).
    """
    # Get the base member role for the invitation payload
    from apps.rbac.models import Role
    base_role = Role.objects.get(
        account_type=AccountType.BUSINESS,
        account_id=business.id,
        name="Base Member",
    )

    # Create the invitation
    txn = TransactionService.create_invitation(
        transaction_type="business_membership_invitation",
        initiator_context=owner_ctx,
        target_user_id=target_user.id,
        payload={"role_id": str(base_role.id)},
    )

    # Create form mapping for this business
    _create_form_mapping(business, template)

    # Target user fills form and accepts
    form_response = _create_submitted_response(template, target_user)
    target_ctx = ActorContext.for_user_context(target_user, request=None)
    txn = TransactionService.accept(
        transaction_id=txn.id,
        actor_context=target_ctx,
        acceptance_payload={"form_response_id": form_response.id},
    )
    return txn, form_response


# =========================================================================
# TestAcceptInvitationWithForm
# =========================================================================


@pytest.mark.django_db
class TestAcceptInvitationWithForm:
    """Tests for accept() when a form mapping exists."""

    def test_accept_invitation_with_form_goes_to_pending_review(self):
        """User accepts invitation with form mapping and form_response_id
        -> status=PENDING_REVIEW, membership created with PENDING_APPROVAL.
        """
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, form_response = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )

        # Transaction should be PENDING_REVIEW
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Membership should be PENDING_APPROVAL
        membership = Membership.objects.filter(
            user=target_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            is_deleted=False,
        ).first()
        assert membership is not None
        assert membership.status == MembershipStatus.PENDING_APPROVAL

    def test_accept_invitation_without_form_stays_accepted(self):
        """User accepts invitation without form mapping
        -> status=ACCEPTED, membership ACTIVE (unchanged behavior).
        """
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()

        from apps.rbac.models import Role
        base_role = Role.objects.get(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            name="Base Member",
        )

        # Create invitation (NO form mapping)
        txn = TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_ctx,
            target_user_id=target_user.id,
            payload={"role_id": str(base_role.id)},
        )

        # Target accepts normally (no form)
        target_ctx = ActorContext.for_user_context(target_user, request=None)
        txn = TransactionService.accept(
            transaction_id=txn.id,
            actor_context=target_ctx,
        )

        # Transaction should be ACCEPTED
        assert txn.status == TransactionStatus.ACCEPTED

        # Membership should be ACTIVE
        membership = Membership.objects.filter(
            user=target_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            status=MembershipStatus.ACTIVE,
            is_deleted=False,
        ).first()
        assert membership is not None


# =========================================================================
# TestApprovePendingReview
# =========================================================================


@pytest.mark.django_db
class TestApprovePendingReview:
    """Tests for approve_pending_review(): PENDING_REVIEW -> ACCEPTED."""

    def test_approve_pending_review_activates_membership(self):
        """Business owner approves -> status=ACCEPTED, membership -> ACTIVE."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Owner approves
        txn = TransactionService.approve_pending_review(
            transaction_id=txn.id,
            actor_context=owner_ctx,
        )

        # Transaction should be ACCEPTED
        assert txn.status == TransactionStatus.ACCEPTED
        assert txn.resolved_at is not None
        assert txn.outcome_executed is True

        # Membership should be ACTIVE
        membership = Membership.objects.filter(
            user=target_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            is_deleted=False,
        ).first()
        assert membership is not None
        assert membership.status == MembershipStatus.ACTIVE

    def test_approve_wrong_status_raises(self):
        """Calling approve_pending_review on a PENDING transaction raises ValidationError."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()

        from apps.rbac.models import Role
        base_role = Role.objects.get(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            name="Base Member",
        )

        # Create a PENDING invitation (no form mapping -> stays PENDING after accept attempt)
        # Actually we need it to stay PENDING, so we just create and don't accept
        txn = TransactionService.create_invitation(
            transaction_type="business_membership_invitation",
            initiator_context=owner_ctx,
            target_user_id=target_user.id,
            payload={"role_id": str(base_role.id)},
        )
        assert txn.status == TransactionStatus.PENDING

        # Try to approve PENDING -> should raise
        with pytest.raises(ValidationError, match="not pending review"):
            TransactionService.approve_pending_review(
                transaction_id=txn.id,
                actor_context=owner_ctx,
            )

    def test_approve_by_non_member_raises(self):
        """Non-member trying to approve raises PermissionDenied."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Create a random user who is NOT a member
        outsider = UserFactory()
        outsider_ctx = ActorContext.for_user_context(outsider, request=None)

        with pytest.raises(PermissionDenied):
            TransactionService.approve_pending_review(
                transaction_id=txn.id,
                actor_context=outsider_ctx,
            )


# =========================================================================
# TestDenyFromPendingReview
# =========================================================================


@pytest.mark.django_db
class TestDenyFromPendingReview:
    """Tests for deny() from PENDING_REVIEW status."""

    def test_deny_from_pending_review_revokes_membership(self):
        """Business denies -> status=DENIED, PENDING_APPROVAL membership soft-deleted."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Verify PENDING_APPROVAL membership exists before deny
        pa_membership = Membership.objects.filter(
            user=target_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            status=MembershipStatus.PENDING_APPROVAL,
            is_deleted=False,
        ).first()
        assert pa_membership is not None

        # Owner denies
        txn = TransactionService.deny(
            transaction_id=txn.id,
            actor_context=owner_ctx,
            reason="Application not satisfactory",
        )

        assert txn.status == TransactionStatus.DENIED
        assert txn.resolved_at is not None

        # PENDING_APPROVAL membership should be soft-deleted
        pa_membership.refresh_from_db()
        assert pa_membership.is_deleted is True


# =========================================================================
# TestCancelFromPendingReview
# =========================================================================


@pytest.mark.django_db
class TestCancelFromPendingReview:
    """Tests for cancel() from PENDING_REVIEW status."""

    def test_cancel_from_pending_review_by_target(self):
        """Target user cancels -> status=CANCELLED, membership revoked."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Target user cancels
        target_ctx = ActorContext.for_user_context(target_user, request=None)
        txn = TransactionService.cancel(
            transaction_id=txn.id,
            actor_context=target_ctx,
        )

        assert txn.status == TransactionStatus.CANCELLED

        # PENDING_APPROVAL membership should be soft-deleted (use all_objects to find it)
        membership = Membership.all_objects.filter(
            user=target_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            status=MembershipStatus.PENDING_APPROVAL,
        ).first()
        assert membership is not None
        assert membership.is_deleted is True

    def test_cancel_from_pending_review_by_initiator(self):
        """Business initiator cancels -> status=CANCELLED, membership revoked."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Owner (initiator) cancels
        txn = TransactionService.cancel(
            transaction_id=txn.id,
            actor_context=owner_ctx,
        )

        assert txn.status == TransactionStatus.CANCELLED

        # PENDING_APPROVAL membership should be soft-deleted (use all_objects to find it)
        membership = Membership.all_objects.filter(
            user=target_user,
            account_type=AccountType.BUSINESS,
            account_id=business.id,
            status=MembershipStatus.PENDING_APPROVAL,
        ).first()
        assert membership is not None
        assert membership.is_deleted is True

    def test_cancel_from_pending_review_by_outsider_raises(self):
        """An unrelated user cannot cancel a PENDING_REVIEW transaction."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )

        outsider = UserFactory()
        outsider_ctx = ActorContext.for_user_context(outsider, request=None)

        with pytest.raises(PermissionDenied, match="Only the initiator or target"):
            TransactionService.cancel(
                transaction_id=txn.id,
                actor_context=outsider_ctx,
            )


# =========================================================================
# TestRequestInfoFromPendingReview
# =========================================================================


@pytest.mark.django_db
class TestRequestInfoFromPendingReview:
    """Tests for request_info() from PENDING_REVIEW status."""

    def test_request_info_from_pending_review(self):
        """Business requests info from PENDING_REVIEW -> status=INFO_REQUESTED."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Owner requests info
        txn = TransactionService.request_info(
            transaction_id=txn.id,
            message="Please elaborate on your experience",
            requested_fields=["experience"],
            actor_context=owner_ctx,
        )

        assert txn.status == TransactionStatus.INFO_REQUESTED
        assert txn.info_requested_at is not None
        assert txn.info_requested_by == owner
        assert txn.info_requested_message == "Please elaborate on your experience"
        assert txn.info_requested_fields == ["experience"]


# =========================================================================
# TestResubmitReturnsToPendingReview
# =========================================================================


@pytest.mark.django_db
class TestResubmitReturnsToPendingReview:
    """Tests for resubmit_after_info_request() returning to PENDING_REVIEW."""

    def test_resubmit_returns_to_pending_review(self):
        """User resubmits after INFO_REQUESTED on an invitation
        -> status=PENDING_REVIEW (not PENDING).
        """
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, form_response = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Owner requests info
        txn = TransactionService.request_info(
            transaction_id=txn.id,
            message="Need more detail",
            actor_context=owner_ctx,
        )
        assert txn.status == TransactionStatus.INFO_REQUESTED

        # Target user resubmits
        target_ctx = ActorContext.for_user_context(target_user, request=None)
        txn = TransactionService.resubmit_after_info_request(
            transaction_id=txn.id,
            actor_context=target_ctx,
        )

        # Should go to PENDING_REVIEW, NOT PENDING
        assert txn.status == TransactionStatus.PENDING_REVIEW

    def test_resubmit_by_non_target_raises(self):
        """A user who is not the target cannot resubmit an invitation."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )

        # Owner requests info
        txn = TransactionService.request_info(
            transaction_id=txn.id,
            message="Need more detail",
            actor_context=owner_ctx,
        )

        # Random user tries to resubmit
        random_user = UserFactory()
        random_ctx = ActorContext.for_user_context(random_user, request=None)

        with pytest.raises(PermissionDenied, match="Only the target user"):
            TransactionService.resubmit_after_info_request(
                transaction_id=txn.id,
                actor_context=random_ctx,
            )


# =========================================================================
# TestPendingApprovalQuota
# =========================================================================


@pytest.mark.django_db
class TestPendingApprovalQuota:
    """Tests that PENDING_APPROVAL memberships count toward the member quota."""

    def test_pending_approval_membership_counts_toward_quota(self):
        """PENDING_APPROVAL membership counts in count_active_members."""
        owner, business, _, owner_ctx = _setup_business_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        # Count before (just the owner)
        count_before = MembershipSelector.count_active_members(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )

        # Accept invitation with form -> PENDING_APPROVAL membership created
        txn, _ = _create_invitation_and_accept_with_form(
            owner, business, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        # Count after (owner + pending_approval member)
        count_after = MembershipSelector.count_active_members(
            account_type=AccountType.BUSINESS,
            account_id=business.id,
        )

        assert count_after == count_before + 1


# =========================================================================
# Platform Pending Review Helpers
# =========================================================================


def _setup_platform_with_owner():
    """Create a platform with initialized RBAC and an owner membership.

    Returns (owner, platform, owner_membership, owner_actor_context).
    """
    owner = UserFactory()
    platform = PlatformAccountFactory()
    platform.open_member_request = True
    platform.save(update_fields=["open_member_request"])

    RBACService.initialize_platform_account(platform_id=platform.id)

    owner_role = Role.objects.get(
        name="Platform Owner",
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
    )

    owner_membership = Membership.objects.create(
        user=owner,
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        role=owner_role,
        is_owner=True,
    )

    owner_ctx = RBACService.build_actor_context(
        membership=owner_membership, request=None,
    )
    return owner, platform, owner_membership, owner_ctx


def _create_platform_form_mapping(platform, template, is_required=True):
    """Create a TransactionFormMapping for platform invitation type."""
    return TransactionFormMapping.objects.create(
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        transaction_type="platform_membership_invitation",
        form_template=template,
        is_required=is_required,
    )


def _create_platform_invitation_and_accept_with_form(
    owner, platform, owner_ctx, target_user, template,
):
    """Helper: create platform invitation, set up form mapping, target accepts with form.

    Returns (txn, form_response).
    """
    base_role = Role.objects.get(
        account_type=AccountType.PLATFORM,
        account_id=platform.id,
        name="Base Member",
    )

    txn = TransactionService.create_invitation(
        transaction_type="platform_membership_invitation",
        initiator_context=owner_ctx,
        target_user_id=target_user.id,
        payload={"role_id": str(base_role.id)},
    )

    _create_platform_form_mapping(platform, template)

    form_response = _create_submitted_response(template, target_user)
    target_ctx = ActorContext.for_user_context(target_user, request=None)
    txn = TransactionService.accept(
        transaction_id=txn.id,
        actor_context=target_ctx,
        acceptance_payload={"form_response_id": form_response.id},
    )
    return txn, form_response


# =========================================================================
# TestPlatformPendingReview
# =========================================================================


@pytest.mark.django_db
class TestPlatformPendingReview:
    """Platform equivalents of pending review tests."""

    def test_platform_accept_with_required_form_enters_pending_review(self):
        """Platform invitation accepted with form -> PENDING_REVIEW + PENDING_APPROVAL."""
        owner, platform, _, owner_ctx = _setup_platform_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_platform_invitation_and_accept_with_form(
            owner, platform, owner_ctx, target_user, template,
        )

        assert txn.status == TransactionStatus.PENDING_REVIEW

        membership = Membership.objects.filter(
            user=target_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            is_deleted=False,
        ).first()
        assert membership is not None
        assert membership.status == MembershipStatus.PENDING_APPROVAL

    def test_platform_approve_pending_review_activates_membership(self):
        """Platform owner approves PENDING_REVIEW -> ACCEPTED + ACTIVE membership."""
        owner, platform, _, owner_ctx = _setup_platform_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_platform_invitation_and_accept_with_form(
            owner, platform, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        txn = TransactionService.approve_pending_review(
            transaction_id=txn.id,
            actor_context=owner_ctx,
        )

        assert txn.status == TransactionStatus.ACCEPTED
        assert txn.resolved_at is not None
        assert txn.outcome_executed is True

        membership = Membership.objects.filter(
            user=target_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            is_deleted=False,
        ).first()
        assert membership is not None
        assert membership.status == MembershipStatus.ACTIVE

    def test_platform_deny_pending_review_deletes_membership(self):
        """Platform owner denies PENDING_REVIEW -> DENIED + membership soft-deleted."""
        owner, platform, _, owner_ctx = _setup_platform_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_platform_invitation_and_accept_with_form(
            owner, platform, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        pa_membership = Membership.objects.filter(
            user=target_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            status=MembershipStatus.PENDING_APPROVAL,
            is_deleted=False,
        ).first()
        assert pa_membership is not None

        txn = TransactionService.deny(
            transaction_id=txn.id,
            actor_context=owner_ctx,
            reason="Not suitable",
        )

        assert txn.status == TransactionStatus.DENIED
        assert txn.resolved_at is not None

        pa_membership.refresh_from_db()
        assert pa_membership.is_deleted is True

    def test_platform_cancel_from_pending_review(self):
        """Target cancels from PENDING_REVIEW -> CANCELLED + membership soft-deleted."""
        owner, platform, _, owner_ctx = _setup_platform_with_owner()
        target_user = UserFactory()
        template = _create_form_template_with_fields()

        txn, _ = _create_platform_invitation_and_accept_with_form(
            owner, platform, owner_ctx, target_user, template,
        )
        assert txn.status == TransactionStatus.PENDING_REVIEW

        target_ctx = ActorContext.for_user_context(target_user, request=None)
        txn = TransactionService.cancel(
            transaction_id=txn.id,
            actor_context=target_ctx,
        )

        assert txn.status == TransactionStatus.CANCELLED

        membership = Membership.all_objects.filter(
            user=target_user,
            account_type=AccountType.PLATFORM,
            account_id=platform.id,
            status=MembershipStatus.PENDING_APPROVAL,
        ).first()
        assert membership is not None
        assert membership.is_deleted is True
