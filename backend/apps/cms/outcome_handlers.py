# apps/cms/outcome_handlers.py
"""
CMS Outcome Handlers
====================
Handle transaction outcomes for CMS-related transactions.
"""

from django.db import transaction as db_transaction

from apps.core.observability import AuditLog, AuditService, get_logger
from apps.core.types import ActorContext

logger = get_logger(__name__)


class CMSActivationOutcomeHandler:
    """Handles CMS activation request approval."""

    @staticmethod
    @db_transaction.atomic
    def handle_approved(
        *,
        transaction,
        actor_context: ActorContext,
        acceptance_payload: dict = None,
    ):
        """
        Enable CMS for the requesting business:
        1. Set BusinessAccount.cms_enabled = True
        2. Auto-provision default templates
        """
        from apps.cms.services import CMSTemplateActivationService
        from apps.core.constants import OwnerType
        from apps.organization.business.models import BusinessAccount
        from apps.users.models import User

        business_id = transaction.payload.get("business_id")
        business = BusinessAccount.objects.get(id=business_id)

        # 1. Enable CMS
        business.cms_enabled = True
        business.save(update_fields=["cms_enabled", "updated_at"])

        # 2. Auto-provision default templates
        count = CMSTemplateActivationService.auto_provision_defaults(
            org_type=OwnerType.BUSINESS,
            org_id=business.id,
            user=User.objects.filter(id=transaction.initiator_id).first(),
        )

        approver = User.objects.filter(id=actor_context.user_id).first()
        AuditService.log(
            action=AuditLog.Action.CMS_BUSINESS_ENABLED,
            actor=approver,
            resource=business,
            details={
                "business_id": str(business.id),
                "transaction_id": str(transaction.id),
                "templates_provisioned": count,
            },
        )

        logger.info(
            "outcome.cms.activation_approved",
            business_id=str(business.id),
            transaction_id=str(transaction.id),
            templates_provisioned=count,
        )
