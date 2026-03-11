# apps/cms/tests/test_policies.py
import pytest
from apps.core.exceptions import BusinessRuleViolation
from apps.cms.policies import CMSPolicy
from apps.cms.tests.factories import (
    PageFactory, PageSectionPlacementFactory, SectionBlockPlacementFactory,
    SectionTemplateFactory,
)


@pytest.mark.django_db
class TestCMSPolicyCanDeletePage:
    def test_allows_non_required_page(self, page):
        assert page.is_required is False
        CMSPolicy.can_delete_page(page=page)  # Should not raise

    def test_blocks_required_page(self, page):
        page.is_required = True
        page.save()
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSPolicy.can_delete_page(page=page)
        assert exc.value.details["rule"] == "required_page_delete"


@pytest.mark.django_db
class TestCMSPolicyCanHidePage:
    def test_allows_non_required_page(self, page):
        CMSPolicy.can_hide_page(page=page)  # Should not raise

    def test_blocks_required_page(self, page):
        page.is_required = True
        page.save()
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSPolicy.can_hide_page(page=page)
        assert exc.value.details["rule"] == "required_page_hide"


@pytest.mark.django_db
class TestCMSPolicyCanHideSectionPlacement:
    def test_allows_non_required_placement(self, section_placement):
        CMSPolicy.can_hide_section_placement(placement=section_placement)

    def test_blocks_required_placement(self, section_placement):
        section_placement.is_required = True
        section_placement.save()
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSPolicy.can_hide_section_placement(placement=section_placement)
        assert exc.value.details["rule"] == "required_section_hide"


@pytest.mark.django_db
class TestCMSPolicyCanHideBlockPlacement:
    def test_allows_non_required_placement(self, block_placement):
        CMSPolicy.can_hide_block_placement(placement=block_placement)

    def test_blocks_required_placement(self, block_placement):
        block_placement.is_required = True
        block_placement.save()
        with pytest.raises(BusinessRuleViolation) as exc:
            CMSPolicy.can_hide_block_placement(placement=block_placement)
        assert exc.value.details["rule"] == "required_block_hide"
