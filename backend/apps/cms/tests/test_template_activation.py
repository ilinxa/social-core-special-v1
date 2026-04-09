# apps/cms/tests/test_template_activation.py
"""
Tests for template activation system — selectors, services, policies.
"""

import uuid

import pytest

from apps.cms.constants import TemplateOrgType
from apps.cms.models import BlockTemplateActivation, SectionTemplateActivation
from apps.cms.policies import CMSActivationPolicy
from apps.cms.selectors import CMSTemplateActivationSelector
from apps.cms.services import CMSTemplateActivationService
from apps.cms.tests.factories import (
    BlockTemplateActivationFactory,
    BlockTemplateFactory,
    PageFactory,
    PageSectionPlacementFactory,
    SectionBlockPlacementFactory,
    SectionTemplateActivationFactory,
    SectionTemplateFactory,
    SiteFactory,
)
from apps.core.constants import OwnerType
from apps.core.exceptions import BusinessRuleViolation

# =============================================================================
# Selectors
# =============================================================================


@pytest.mark.django_db
class TestTemplateActivationSelectors:
    def test_list_available_section_templates(self, business_account):
        """Returns eligible templates NOT yet activated."""
        st_all = SectionTemplateFactory(org_type=TemplateOrgType.ALL)
        st_biz = SectionTemplateFactory(org_type=TemplateOrgType.BUSINESS)
        SectionTemplateFactory(org_type=TemplateOrgType.PLATFORM)  # not eligible
        SectionTemplateFactory(org_type=TemplateOrgType.SYSTEM)  # not eligible

        available = CMSTemplateActivationSelector.list_available_section_templates(
            org_type=OwnerType.BUSINESS,
            org_id=business_account.id,
        )
        ids = set(available.values_list("id", flat=True))
        assert st_all.id in ids
        assert st_biz.id in ids
        assert len(ids) == 2

    def test_list_available_excludes_activated(
        self, business_account, activated_section_template
    ):
        """Already-activated templates are excluded from available list."""
        available = CMSTemplateActivationSelector.list_available_section_templates(
            org_type=OwnerType.BUSINESS,
            org_id=business_account.id,
        )
        ids = set(available.values_list("id", flat=True))
        assert activated_section_template.template.id not in ids

    def test_list_activated_section_templates(
        self, business_account, activated_section_template
    ):
        """Returns active activations for the org."""
        activations = CMSTemplateActivationSelector.list_activated_section_templates(
            org_type=OwnerType.BUSINESS,
            org_id=business_account.id,
        )
        assert activations.count() == 1
        assert activations.first().template == activated_section_template.template

    def test_list_available_block_templates(self, business_account):
        """Returns eligible block templates NOT yet activated."""
        bt = BlockTemplateFactory(org_type=TemplateOrgType.ALL)
        BlockTemplateFactory(org_type=TemplateOrgType.SYSTEM)  # not eligible

        available = CMSTemplateActivationSelector.list_available_block_templates(
            org_type=OwnerType.BUSINESS,
            org_id=business_account.id,
        )
        ids = set(available.values_list("id", flat=True))
        assert bt.id in ids

    def test_is_template_activated_true(
        self, business_account, activated_block_template
    ):
        assert CMSTemplateActivationSelector.is_template_activated(
            template_id=activated_block_template.template.id,
            template_type="block",
            org_type=OwnerType.BUSINESS,
            org_id=business_account.id,
        )

    def test_is_template_activated_false(self, business_account):
        bt = BlockTemplateFactory(org_type=TemplateOrgType.ALL)
        assert not CMSTemplateActivationSelector.is_template_activated(
            template_id=bt.id,
            template_type="block",
            org_type=OwnerType.BUSINESS,
            org_id=business_account.id,
        )


# =============================================================================
# Services
# =============================================================================


@pytest.mark.django_db
class TestTemplateActivationService:
    def test_activate_section_template(
        self, business_actor_context, business_section_template
    ):
        activation = CMSTemplateActivationService.activate_section_template(
            actor_context=business_actor_context,
            template_id=business_section_template.id,
        )
        assert activation.is_active
        assert activation.template == business_section_template
        assert activation.org_type == business_actor_context.account_type
        assert str(activation.org_id) == str(business_actor_context.account_id)

    def test_activate_block_template(
        self, business_actor_context, business_block_template
    ):
        activation = CMSTemplateActivationService.activate_block_template(
            actor_context=business_actor_context,
            template_id=business_block_template.id,
        )
        assert activation.is_active
        assert activation.template == business_block_template

    def test_activate_ineligible_template_rejected(self, business_actor_context):
        """Business can't activate a platform-only template."""
        platform_template = SectionTemplateFactory(org_type=TemplateOrgType.PLATFORM)
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSTemplateActivationService.activate_section_template(
                actor_context=business_actor_context,
                template_id=platform_template.id,
            )
        assert exc.value.details["rule"] == "template_not_eligible"

    def test_activate_system_template_rejected(self, business_actor_context):
        """Nobody can activate system templates."""
        system_template = BlockTemplateFactory(org_type=TemplateOrgType.SYSTEM)
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSTemplateActivationService.activate_block_template(
                actor_context=business_actor_context,
                template_id=system_template.id,
            )
        assert exc.value.details["rule"] == "template_not_eligible"

    def test_duplicate_activation_reactivates(
        self, business_actor_context, business_section_template, business_account
    ):
        """Second activate on same template reactivates if deactivated."""
        # First activation
        activation = CMSTemplateActivationService.activate_section_template(
            actor_context=business_actor_context,
            template_id=business_section_template.id,
        )
        # Deactivate
        activation.is_active = False
        activation.save(update_fields=["is_active"])

        # Re-activate
        reactivated = CMSTemplateActivationService.activate_section_template(
            actor_context=business_actor_context,
            template_id=business_section_template.id,
        )
        assert reactivated.id == activation.id
        assert reactivated.is_active

    def test_deactivate_section_template(
        self, business_actor_context, activated_section_template
    ):
        CMSTemplateActivationService.deactivate_section_template(
            actor_context=business_actor_context,
            activation_id=activated_section_template.id,
        )
        activated_section_template.refresh_from_db()
        assert not activated_section_template.is_active

    def test_deactivate_block_template(
        self, business_actor_context, activated_block_template
    ):
        CMSTemplateActivationService.deactivate_block_template(
            actor_context=business_actor_context,
            activation_id=activated_block_template.id,
        )
        activated_block_template.refresh_from_db()
        assert not activated_block_template.is_active

    def test_auto_provision_defaults(self, business_account, business_user):
        """Auto-provision creates activations for all default templates."""
        st1 = SectionTemplateFactory(org_type=TemplateOrgType.ALL, is_default=True)
        st2 = SectionTemplateFactory(org_type=TemplateOrgType.BUSINESS, is_default=True)
        SectionTemplateFactory(
            org_type=TemplateOrgType.PLATFORM, is_default=True
        )  # should be skipped
        bt1 = BlockTemplateFactory(org_type=TemplateOrgType.ALL, is_default=True)

        count = CMSTemplateActivationService.auto_provision_defaults(
            org_type=OwnerType.BUSINESS,
            org_id=business_account.id,
            user=business_user,
        )
        assert count == 3  # st1, st2, bt1

        assert (
            SectionTemplateActivation.objects.filter(
                org_type=OwnerType.BUSINESS,
                org_id=business_account.id,
            ).count()
            == 2
        )  # st1 + st2

        assert (
            BlockTemplateActivation.objects.filter(
                org_type=OwnerType.BUSINESS,
                org_id=business_account.id,
            ).count()
            == 1
        )  # bt1

    def test_max_active_section_templates_limit(
        self, business_actor_context, feature_config_override
    ):
        """Limit check prevents over-activation."""
        feature_config_override(
            {"business": {"cms": {"enabled": True, "max_active_section_templates": 1}}}
        )
        st1 = SectionTemplateFactory(org_type=TemplateOrgType.ALL)
        st2 = SectionTemplateFactory(org_type=TemplateOrgType.ALL)

        CMSTemplateActivationService.activate_section_template(
            actor_context=business_actor_context,
            template_id=st1.id,
        )
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSTemplateActivationService.activate_section_template(
                actor_context=business_actor_context,
                template_id=st2.id,
            )
        assert exc.value.details["rule"] == "max_active_section_templates_exceeded"


# =============================================================================
# Policies
# =============================================================================


@pytest.mark.django_db
class TestActivationPolicy:
    def test_can_deactivate_unused_section_template(
        self, activated_section_template, business_account
    ):
        """No error when template has no active placements."""
        CMSActivationPolicy.can_deactivate_section_template(
            activation=activated_section_template,
            org_type=OwnerType.BUSINESS,
            org_id=business_account.id,
        )

    def test_cannot_deactivate_section_template_in_use(
        self,
        activated_section_template,
        business_section_template,
        business_account,
        business_user,
    ):
        """Error when template is referenced by active placements."""
        site = SiteFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        page = PageFactory(
            site=site, created_by=business_user, updated_by=business_user
        )
        PageSectionPlacementFactory(page=page, template=business_section_template)

        with pytest.raises(BusinessRuleViolation) as exc:
            CMSActivationPolicy.can_deactivate_section_template(
                activation=activated_section_template,
                org_type=OwnerType.BUSINESS,
                org_id=business_account.id,
            )
        assert exc.value.details["rule"] == "template_in_use"

    def test_cannot_deactivate_block_template_in_use(
        self,
        activated_block_template,
        business_block_template,
        business_account,
        business_user,
    ):
        """Error when block template is referenced by active placements."""
        site = SiteFactory(
            owner_type=OwnerType.BUSINESS,
            owner_id=business_account.id,
            created_by=business_user,
            updated_by=business_user,
        )
        page = PageFactory(
            site=site, created_by=business_user, updated_by=business_user
        )
        sp = PageSectionPlacementFactory(page=page, template=SectionTemplateFactory())
        SectionBlockPlacementFactory(
            section_placement=sp,
            template=business_block_template,
            created_by=business_user,
            updated_by=business_user,
        )

        with pytest.raises(BusinessRuleViolation) as exc:
            CMSActivationPolicy.can_deactivate_block_template(
                activation=activated_block_template,
                org_type=OwnerType.BUSINESS,
                org_id=business_account.id,
            )
        assert exc.value.details["rule"] == "template_in_use"
