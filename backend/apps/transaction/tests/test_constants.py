# apps/transaction/tests/test_constants.py
"""
Tests for transaction constants.

Tests cover:
- TERMINAL_STATES membership and exclusions
- VALID_TRANSITIONS mapping correctness
- TransactionMode choices
- TransactionStatus choices
- PartyType choices
- ApproverPolicy choices
"""

import pytest

from apps.transaction.constants import (
    TERMINAL_STATES,
    VALID_TRANSITIONS,
    ApproverPolicy,
    PartyType,
    TransactionMode,
    TransactionStatus,
)


class TestTerminalStates:
    """Tests for TERMINAL_STATES frozenset."""

    def test_terminal_states_contains_accepted(self):
        """TERMINAL_STATES includes ACCEPTED."""
        assert TransactionStatus.ACCEPTED in TERMINAL_STATES

    def test_terminal_states_contains_denied(self):
        """TERMINAL_STATES includes DENIED."""
        assert TransactionStatus.DENIED in TERMINAL_STATES

    def test_terminal_states_contains_cancelled(self):
        """TERMINAL_STATES includes CANCELLED."""
        assert TransactionStatus.CANCELLED in TERMINAL_STATES

    def test_terminal_states_contains_expired(self):
        """TERMINAL_STATES includes EXPIRED."""
        assert TransactionStatus.EXPIRED in TERMINAL_STATES

    def test_terminal_states_contains_dismissed(self):
        """TERMINAL_STATES includes DISMISSED."""
        assert TransactionStatus.DISMISSED in TERMINAL_STATES

    def test_terminal_states_contains_invalidated(self):
        """TERMINAL_STATES includes INVALIDATED."""
        assert TransactionStatus.INVALIDATED in TERMINAL_STATES

    def test_terminal_states_has_exactly_six_members(self):
        """TERMINAL_STATES contains exactly 6 statuses."""
        assert len(TERMINAL_STATES) == 6

    def test_terminal_states_does_not_contain_created(self):
        """TERMINAL_STATES does NOT include CREATED."""
        assert TransactionStatus.CREATED not in TERMINAL_STATES

    def test_terminal_states_does_not_contain_pending(self):
        """TERMINAL_STATES does NOT include PENDING."""
        assert TransactionStatus.PENDING not in TERMINAL_STATES

    def test_terminal_states_exact_membership(self):
        """TERMINAL_STATES contains exactly the 6 expected statuses."""
        expected = frozenset(
            [
                TransactionStatus.ACCEPTED,
                TransactionStatus.DENIED,
                TransactionStatus.CANCELLED,
                TransactionStatus.EXPIRED,
                TransactionStatus.DISMISSED,
                TransactionStatus.INVALIDATED,
            ]
        )

        assert TERMINAL_STATES == expected


class TestValidTransitions:
    """Tests for VALID_TRANSITIONS mapping."""

    def test_created_transitions_contain_pending(self):
        """VALID_TRANSITIONS[CREATED] includes PENDING."""
        assert TransactionStatus.PENDING in VALID_TRANSITIONS[TransactionStatus.CREATED]

    def test_created_transitions_contain_expired(self):
        """VALID_TRANSITIONS[CREATED] includes EXPIRED."""
        assert TransactionStatus.EXPIRED in VALID_TRANSITIONS[TransactionStatus.CREATED]

    def test_created_transitions_contain_invalidated(self):
        """VALID_TRANSITIONS[CREATED] includes INVALIDATED."""
        assert (
            TransactionStatus.INVALIDATED
            in VALID_TRANSITIONS[TransactionStatus.CREATED]
        )

    def test_created_transitions_has_exactly_three_targets(self):
        """VALID_TRANSITIONS[CREATED] has exactly 3 valid targets."""
        assert len(VALID_TRANSITIONS[TransactionStatus.CREATED]) == 3

    def test_pending_transitions_contain_all_terminal_states(self):
        """VALID_TRANSITIONS[PENDING] includes all 6 terminal states."""
        pending_targets = VALID_TRANSITIONS[TransactionStatus.PENDING]

        for status in TERMINAL_STATES:
            assert status in pending_targets

    def test_pending_transitions_has_exactly_eight_targets(self):
        """VALID_TRANSITIONS[PENDING] has 8 valid targets (incl. INFO_REQUESTED + PENDING_REVIEW)."""
        assert len(VALID_TRANSITIONS[TransactionStatus.PENDING]) == 8

    def test_pending_review_transitions(self):
        """VALID_TRANSITIONS[PENDING_REVIEW] allows ACCEPTED, DENIED, CANCELLED, EXPIRED, INVALIDATED, INFO_REQUESTED."""
        pr_targets = VALID_TRANSITIONS[TransactionStatus.PENDING_REVIEW]
        assert TransactionStatus.ACCEPTED in pr_targets
        assert TransactionStatus.DENIED in pr_targets
        assert TransactionStatus.CANCELLED in pr_targets
        assert TransactionStatus.EXPIRED in pr_targets
        assert TransactionStatus.INVALIDATED in pr_targets
        assert TransactionStatus.INFO_REQUESTED in pr_targets
        assert len(pr_targets) == 6

    def test_info_requested_can_go_to_pending_review(self):
        """INFO_REQUESTED can transition to PENDING_REVIEW (for invitations)."""
        ir_targets = VALID_TRANSITIONS[TransactionStatus.INFO_REQUESTED]
        assert TransactionStatus.PENDING_REVIEW in ir_targets

    def test_pending_can_go_to_pending_review(self):
        """PENDING can transition to PENDING_REVIEW (for invitation acceptance with form)."""
        p_targets = VALID_TRANSITIONS[TransactionStatus.PENDING]
        assert TransactionStatus.PENDING_REVIEW in p_targets

    def test_terminal_states_only_allow_dismiss(self):
        """Terminal states in VALID_TRANSITIONS may only transition to DISMISSED."""
        dismissable = {TransactionStatus.ACCEPTED, TransactionStatus.DENIED}
        for status in TERMINAL_STATES:
            if status in VALID_TRANSITIONS:
                assert (
                    status in dismissable
                ), f"{status} should not be in VALID_TRANSITIONS"
                assert VALID_TRANSITIONS[status] == [TransactionStatus.DISMISSED]
            elif status not in dismissable:
                assert status not in VALID_TRANSITIONS


class TestTransactionMode:
    """Tests for TransactionMode enum."""

    def test_has_invitation(self):
        """TransactionMode includes INVITATION."""
        assert TransactionMode.INVITATION == "invitation"

    def test_has_request(self):
        """TransactionMode includes REQUEST."""
        assert TransactionMode.REQUEST == "request"

    def test_has_exactly_two_choices(self):
        """TransactionMode has exactly 2 choices."""
        assert len(TransactionMode.choices) == 2


class TestTransactionStatus:
    """Tests for TransactionStatus enum."""

    def test_has_all_ten_values(self):
        """TransactionStatus has exactly 10 values (incl. INFO_REQUESTED + PENDING_REVIEW)."""
        expected_values = {
            "created",
            "pending",
            "pending_review",
            "accepted",
            "denied",
            "cancelled",
            "expired",
            "dismissed",
            "invalidated",
            "info_requested",
        }

        actual_values = {choice[0] for choice in TransactionStatus.choices}

        assert actual_values == expected_values

    def test_has_exactly_ten_choices(self):
        """TransactionStatus has exactly 10 choices."""
        assert len(TransactionStatus.choices) == 10


class TestPartyType:
    """Tests for PartyType enum."""

    def test_has_user(self):
        """PartyType includes USER."""
        assert PartyType.USER == "user"

    def test_has_account(self):
        """PartyType includes ACCOUNT."""
        assert PartyType.ACCOUNT == "account"

    def test_has_membership_actor(self):
        """PartyType includes MEMBERSHIP_ACTOR."""
        assert PartyType.MEMBERSHIP_ACTOR == "membership_actor"

    def test_has_system(self):
        """PartyType includes SYSTEM."""
        assert PartyType.SYSTEM == "system"

    def test_has_exactly_four_choices(self):
        """PartyType has exactly 4 choices."""
        assert len(PartyType.choices) == 4


class TestApproverPolicy:
    """Tests for ApproverPolicy enum."""

    def test_has_target_acceptance(self):
        """ApproverPolicy includes TARGET_ACCEPTANCE."""
        assert ApproverPolicy.TARGET_ACCEPTANCE == "target_acceptance"

    def test_has_account_authority(self):
        """ApproverPolicy includes ACCOUNT_AUTHORITY."""
        assert ApproverPolicy.ACCOUNT_AUTHORITY == "account_authority"

    def test_has_platform_authority(self):
        """ApproverPolicy includes PLATFORM_AUTHORITY."""
        assert ApproverPolicy.PLATFORM_AUTHORITY == "platform_authority"

    def test_has_auto_approval(self):
        """ApproverPolicy includes AUTO_APPROVAL."""
        assert ApproverPolicy.AUTO_APPROVAL == "auto_approval"

    def test_has_exactly_four_choices(self):
        """ApproverPolicy has exactly 4 choices."""
        assert len(ApproverPolicy.choices) == 4
