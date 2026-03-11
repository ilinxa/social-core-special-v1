# apps/forms/tests/test_transaction_integration.py
"""
Tests for the Form Builder side of Form-Transaction integration.

Covers:
- FormResponseService: create_and_submit, link_to_transaction,
  mark_info_requested, update_after_info_request
- FormTemplateSelector: get_by_slug_or_none
- FormResponseSelector: get_by_transaction_id
"""

import pytest
from uuid import uuid4

from apps.forms.services import FormResponseService
from apps.forms.selectors import FormTemplateSelector, FormResponseSelector
from apps.forms.models import TextFieldIndex
from apps.forms.tests.factories import (
    ActiveFormTemplateFactory,
    FormFieldFactory,
    FormResponseFactory,
    SubmittedFormResponseFactory,
)
from apps.transaction.tests.factories import TransactionFactory
from apps.transaction.constants import TransactionStatus
from apps.core.types import ActorContext
from apps.core.constants import (
    ResponseStatus,
    FormStatus,
    OwnerType,
    FormScope,
    FieldType,
)
from apps.core.exceptions import (
    ValidationError,
    ConflictError,
    PermissionDenied,
    BusinessRuleViolation,
)
from apps.users.tests.factories import UserFactory


# =============================================================================
# Helpers
# =============================================================================


def _make_active_template_with_fields(user, *, required_keys=None, indexed_keys=None):
    """Create an active form template with the specified fields.

    Args:
        user: The user who creates the template.
        required_keys: List of field_keys that are required (text type).
        indexed_keys: List of field_keys that are indexed (text type).

    Returns:
        The created ActiveFormTemplate (with fields attached).
    """
    required_keys = required_keys or []
    indexed_keys = indexed_keys or []
    all_keys = list(dict.fromkeys(required_keys + indexed_keys))  # deduplicate, preserve order

    template = ActiveFormTemplateFactory(created_by=user)

    for i, key in enumerate(all_keys):
        FormFieldFactory(
            form_template=template,
            field_key=key,
            field_type=FieldType.TEXT,
            label=key.replace("_", " ").title(),
            order=i,
            is_required=key in required_keys,
            is_indexed=key in indexed_keys,
        )

    return template


# =============================================================================
# TestCreateAndSubmit
# =============================================================================


@pytest.mark.django_db
class TestCreateAndSubmit:
    """Tests for FormResponseService.create_and_submit."""

    def test_create_and_submit_success(self):
        """Creates response with SUBMITTED status, data populated, IndexService called."""
        user = UserFactory()
        template = _make_active_template_with_fields(
            user, required_keys=["name"], indexed_keys=["name"],
        )
        actor_context = ActorContext.for_user_context(user)

        response = FormResponseService.create_and_submit(
            form_template=template,
            data={"name": "Alice"},
            actor_context=actor_context,
            actor=user,
        )

        assert response.status == ResponseStatus.SUBMITTED
        assert response.data == {"name": "Alice"}
        assert response.submitted_by == user
        assert response.submitted_at is not None
        assert response.revision == 1
        # Index entry created for the indexed field
        assert TextFieldIndex.objects.filter(
            response=response, field_key="name", value="Alice",
        ).exists()

    def test_create_and_submit_validates_required_fields(self):
        """Missing required field raises ValidationError."""
        user = UserFactory()
        template = _make_active_template_with_fields(
            user, required_keys=["email"],
        )
        actor_context = ActorContext.for_user_context(user)

        with pytest.raises(ValidationError, match="Required fields missing"):
            FormResponseService.create_and_submit(
                form_template=template,
                data={},
                actor_context=actor_context,
                actor=user,
            )

    def test_create_and_submit_inactive_form_raises(self):
        """Form template not accepting responses raises BusinessRuleViolation."""
        user = UserFactory()
        # Draft form does not accept responses (accepts_responses = ACTIVE + is_current)
        from apps.forms.tests.factories import FormTemplateFactory
        draft_template = FormTemplateFactory(
            status=FormStatus.DRAFT, is_current=True, created_by=user,
        )
        actor_context = ActorContext.for_user_context(user)

        with pytest.raises(BusinessRuleViolation, match="not accepting responses"):
            FormResponseService.create_and_submit(
                form_template=draft_template,
                data={"field_1": "value"},
                actor_context=actor_context,
                actor=user,
            )

    def test_create_and_submit_sets_context(self):
        """context_type and context_id are set on response."""
        user = UserFactory()
        template = _make_active_template_with_fields(user)
        actor_context = ActorContext.for_user_context(user)
        ctx_id = uuid4()

        response = FormResponseService.create_and_submit(
            form_template=template,
            data={},
            actor_context=actor_context,
            actor=user,
            context_type="business",
            context_id=ctx_id,
        )

        assert response.context_type == "business"
        assert response.context_id == ctx_id

    def test_create_and_submit_extracts_indexes(self):
        """Indexed fields are extracted after creation."""
        user = UserFactory()
        template = _make_active_template_with_fields(
            user, indexed_keys=["company", "city"],
        )
        actor_context = ActorContext.for_user_context(user)

        response = FormResponseService.create_and_submit(
            form_template=template,
            data={"company": "Acme", "city": "Denver"},
            actor_context=actor_context,
            actor=user,
        )

        assert TextFieldIndex.objects.filter(response=response).count() == 2
        assert TextFieldIndex.objects.filter(
            response=response, field_key="company", value="Acme",
        ).exists()
        assert TextFieldIndex.objects.filter(
            response=response, field_key="city", value="Denver",
        ).exists()


# =============================================================================
# TestLinkToTransaction
# =============================================================================


@pytest.mark.django_db
class TestLinkToTransaction:
    """Tests for FormResponseService.link_to_transaction."""

    def test_link_to_transaction_sets_id(self):
        """FormResponse.transaction_id is set."""
        response = SubmittedFormResponseFactory()
        txn_id = uuid4()

        result = FormResponseService.link_to_transaction(
            response_id=response.id,
            transaction_id=txn_id,
        )

        result.refresh_from_db()
        assert result.transaction_id == txn_id

    def test_link_already_linked_different_txn_raises(self):
        """Already linked to different transaction raises ConflictError."""
        txn_id_1 = uuid4()
        txn_id_2 = uuid4()
        response = SubmittedFormResponseFactory(transaction_id=txn_id_1)

        with pytest.raises(ConflictError, match="already linked"):
            FormResponseService.link_to_transaction(
                response_id=response.id,
                transaction_id=txn_id_2,
            )

    def test_link_same_transaction_idempotent(self):
        """Already linked to same transaction succeeds without error."""
        txn_id = uuid4()
        response = SubmittedFormResponseFactory(transaction_id=txn_id)

        result = FormResponseService.link_to_transaction(
            response_id=response.id,
            transaction_id=txn_id,
        )

        assert result.transaction_id == txn_id

    def test_link_to_transaction_preserves_data(self):
        """Other fields remain unchanged after linking."""
        original_data = {"field_1": "original_value"}
        response = SubmittedFormResponseFactory(data=original_data)
        txn_id = uuid4()

        result = FormResponseService.link_to_transaction(
            response_id=response.id,
            transaction_id=txn_id,
        )

        result.refresh_from_db()
        assert result.data == original_data
        assert result.status == ResponseStatus.SUBMITTED


# =============================================================================
# TestMarkInfoRequested
# =============================================================================


@pytest.mark.django_db
class TestMarkInfoRequested:
    """Tests for FormResponseService.mark_info_requested."""

    def test_mark_info_requested_sets_timestamp(self):
        """info_requested_at is set to approximately now."""
        response = SubmittedFormResponseFactory()
        actor = UserFactory()

        result = FormResponseService.mark_info_requested(
            response_id=response.id,
            actor=actor,
        )

        result.refresh_from_db()
        assert result.info_requested_at is not None

    def test_mark_info_requested_sets_updated_by(self):
        """updated_by is set to the actor."""
        response = SubmittedFormResponseFactory()
        actor = UserFactory()

        result = FormResponseService.mark_info_requested(
            response_id=response.id,
            actor=actor,
        )

        result.refresh_from_db()
        assert result.updated_by == actor


# =============================================================================
# TestUpdateAfterInfoRequest
# =============================================================================


@pytest.mark.django_db
class TestUpdateAfterInfoRequest:
    """Tests for FormResponseService.update_after_info_request."""

    def _create_info_requested_response(self, *, user=None, data=None):
        """Helper: create a submitted response linked to an INFO_REQUESTED transaction.

        Returns (response, transaction, user).
        """
        user = user or UserFactory()
        template = _make_active_template_with_fields(
            user, required_keys=["name"], indexed_keys=["name"],
        )
        actor_context = ActorContext.for_user_context(user)

        response = FormResponseService.create_and_submit(
            form_template=template,
            data=data or {"name": "Original"},
            actor_context=actor_context,
            actor=user,
        )

        txn = TransactionFactory(status=TransactionStatus.INFO_REQUESTED)

        FormResponseService.link_to_transaction(
            response_id=response.id,
            transaction_id=txn.id,
        )

        FormResponseService.mark_info_requested(
            response_id=response.id,
            actor=user,
        )

        response.refresh_from_db()
        return response, txn, user

    def test_update_success(self):
        """Updates data, increments revision, saves history."""
        response, txn, user = self._create_info_requested_response()
        actor_context = ActorContext.for_user_context(user)

        updated = FormResponseService.update_after_info_request(
            response_id=response.id,
            data={"name": "Updated"},
            actor_context=actor_context,
            actor=user,
        )

        assert updated.data == {"name": "Updated"}
        assert updated.revision == 2

    def test_update_saves_revision_history(self):
        """Previous data saved in revision_history."""
        response, txn, user = self._create_info_requested_response(
            data={"name": "Rev1"},
        )
        actor_context = ActorContext.for_user_context(user)

        updated = FormResponseService.update_after_info_request(
            response_id=response.id,
            data={"name": "Rev2"},
            actor_context=actor_context,
            actor=user,
        )

        assert len(updated.revision_history) == 1
        assert updated.revision_history[0]["revision"] == 1
        assert updated.revision_history[0]["data"] == {"name": "Rev1"}

    def test_update_re_extracts_indexes(self):
        """Old indexes cleared, new ones created."""
        response, txn, user = self._create_info_requested_response(
            data={"name": "OldValue"},
        )
        actor_context = ActorContext.for_user_context(user)

        # Verify old index exists
        assert TextFieldIndex.objects.filter(
            response=response, field_key="name", value="OldValue",
        ).exists()

        FormResponseService.update_after_info_request(
            response_id=response.id,
            data={"name": "NewValue"},
            actor_context=actor_context,
            actor=user,
        )

        # Old index gone, new index present
        assert not TextFieldIndex.objects.filter(
            response=response, field_key="name", value="OldValue",
        ).exists()
        assert TextFieldIndex.objects.filter(
            response=response, field_key="name", value="NewValue",
        ).exists()

    def test_update_validates_transaction_status(self):
        """Transaction not in INFO_REQUESTED raises ValidationError."""
        user = UserFactory()
        template = _make_active_template_with_fields(
            user, required_keys=["name"],
        )
        actor_context = ActorContext.for_user_context(user)

        response = FormResponseService.create_and_submit(
            form_template=template,
            data={"name": "Test"},
            actor_context=actor_context,
            actor=user,
        )

        # Link to a PENDING transaction (not INFO_REQUESTED)
        txn = TransactionFactory(status=TransactionStatus.PENDING)
        FormResponseService.link_to_transaction(
            response_id=response.id,
            transaction_id=txn.id,
        )

        with pytest.raises(ValidationError, match="INFO_REQUESTED"):
            FormResponseService.update_after_info_request(
                response_id=response.id,
                data={"name": "Updated"},
                actor_context=actor_context,
                actor=user,
            )

    def test_update_validates_submitter(self):
        """Different user raises PermissionDenied."""
        response, txn, original_user = self._create_info_requested_response()
        other_user = UserFactory()
        actor_context = ActorContext.for_user_context(other_user)

        with pytest.raises(PermissionDenied, match="original submitter"):
            FormResponseService.update_after_info_request(
                response_id=response.id,
                data={"name": "Updated"},
                actor_context=actor_context,
                actor=other_user,
            )

    def test_update_validates_required_fields(self):
        """Missing required field raises ValidationError."""
        response, txn, user = self._create_info_requested_response()
        actor_context = ActorContext.for_user_context(user)

        with pytest.raises(ValidationError, match="Required fields missing"):
            FormResponseService.update_after_info_request(
                response_id=response.id,
                data={},
                actor_context=actor_context,
                actor=user,
            )

    def test_update_no_transaction_raises(self):
        """No transaction_id on response raises ValidationError."""
        user = UserFactory()
        template = _make_active_template_with_fields(user)
        actor_context = ActorContext.for_user_context(user)

        response = FormResponseService.create_and_submit(
            form_template=template,
            data={},
            actor_context=actor_context,
            actor=user,
        )

        # Response has no transaction_id linked
        with pytest.raises(ValidationError, match="not linked to a transaction"):
            FormResponseService.update_after_info_request(
                response_id=response.id,
                data={},
                actor_context=actor_context,
                actor=user,
            )

    def test_update_clears_info_requested_at(self):
        """info_requested_at set to None after update."""
        response, txn, user = self._create_info_requested_response()
        actor_context = ActorContext.for_user_context(user)

        # Confirm info_requested_at was set
        assert response.info_requested_at is not None

        updated = FormResponseService.update_after_info_request(
            response_id=response.id,
            data={"name": "Updated"},
            actor_context=actor_context,
            actor=user,
        )

        updated.refresh_from_db()
        assert updated.info_requested_at is None


# =============================================================================
# TestNewSelectors
# =============================================================================


@pytest.mark.django_db
class TestNewSelectors:
    """Tests for transaction-related selector methods."""

    def test_get_by_slug_or_none_found(self):
        """Returns template when it exists."""
        user = UserFactory()
        owner_id = uuid4()
        template = ActiveFormTemplateFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=owner_id,
            slug="intake-form",
            created_by=user,
        )

        result = FormTemplateSelector.get_by_slug_or_none(
            owner_type=OwnerType.BUSINESS,
            owner_id=owner_id,
            slug="intake-form",
        )

        assert result is not None
        assert result.id == template.id

    def test_get_by_slug_or_none_not_found(self):
        """Returns None when doesn't exist."""
        result = FormTemplateSelector.get_by_slug_or_none(
            owner_type=OwnerType.BUSINESS,
            owner_id=uuid4(),
            slug="nonexistent-slug",
        )

        assert result is None

    def test_get_by_transaction_id_found(self):
        """Returns response when it exists for the given transaction_id."""
        txn_id = uuid4()
        response = SubmittedFormResponseFactory(transaction_id=txn_id)

        result = FormResponseSelector.get_by_transaction_id(
            transaction_id=txn_id,
        )

        assert result is not None
        assert result.id == response.id

    def test_get_by_transaction_id_not_found(self):
        """Returns None when no response exists for the given transaction_id."""
        result = FormResponseSelector.get_by_transaction_id(
            transaction_id=uuid4(),
        )

        assert result is None
