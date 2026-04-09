# apps/cms/tests/test_outcome_handlers.py
"""
Tests for CMS activation outcome handler.
"""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from apps.cms.constants import TemplateOrgType
from apps.cms.models import BlockTemplateActivation, SectionTemplateActivation
from apps.cms.outcome_handlers import CMSActivationOutcomeHandler
from apps.cms.tests.factories import BlockTemplateFactory, SectionTemplateFactory
from apps.core.constants import AccountType, OwnerType
from apps.core.types import ActorContext
from apps.organization.tests.factories import BusinessAccountFactory
from apps.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestCMSActivationOutcomeHandler:
    @pytest.fixture
    def business(self, db):
        user = UserFactory()
        biz = BusinessAccountFactory(created_by=user, updated_by=user)
        assert biz.cms_enabled is False
        return biz

    @pytest.fixture
    def mock_transaction(self, business):
        txn = MagicMock()
        txn.id = uuid4()
        txn.initiator_id = business.created_by.id
        txn.payload = {"business_id": str(business.id)}
        return txn

    @pytest.fixture
    def mock_actor_context(self):
        ctx = MagicMock(spec=ActorContext)
        ctx.user_id = uuid4()
        return ctx

    def test_activation_approved_enables_cms(
        self, business, mock_transaction, mock_actor_context
    ):
        """Sets business.cms_enabled = True."""
        CMSActivationOutcomeHandler.handle_approved(
            transaction=mock_transaction,
            actor_context=mock_actor_context,
        )
        business.refresh_from_db()
        assert business.cms_enabled is True

    def test_activation_approved_provisions_defaults(
        self, business, mock_transaction, mock_actor_context
    ):
        """Auto-provisions default templates."""
        st = SectionTemplateFactory(org_type=TemplateOrgType.ALL, is_default=True)
        bt = BlockTemplateFactory(org_type=TemplateOrgType.BUSINESS, is_default=True)

        CMSActivationOutcomeHandler.handle_approved(
            transaction=mock_transaction,
            actor_context=mock_actor_context,
        )

        assert SectionTemplateActivation.objects.filter(
            org_type=OwnerType.BUSINESS, org_id=business.id, template=st
        ).exists()
        assert BlockTemplateActivation.objects.filter(
            org_type=OwnerType.BUSINESS, org_id=business.id, template=bt
        ).exists()

    def test_activation_approved_only_eligible_templates(
        self, business, mock_transaction, mock_actor_context
    ):
        """Skips platform-only and system templates."""
        SectionTemplateFactory(org_type=TemplateOrgType.PLATFORM, is_default=True)
        SectionTemplateFactory(org_type=TemplateOrgType.SYSTEM, is_default=True)
        eligible = SectionTemplateFactory(org_type=TemplateOrgType.ALL, is_default=True)

        CMSActivationOutcomeHandler.handle_approved(
            transaction=mock_transaction,
            actor_context=mock_actor_context,
        )

        activations = SectionTemplateActivation.objects.filter(
            org_type=OwnerType.BUSINESS, org_id=business.id
        )
        assert activations.count() == 1
        assert activations.first().template == eligible
