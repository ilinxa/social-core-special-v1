# apps/cms/services.py
"""
CMS Services
==============
All write operations for the CMS app.
Pattern: @staticmethod, @transaction.atomic, keyword-only arguments.
"""

from uuid import UUID

from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from apps.cms.constants import (
    MAX_VERSIONS_PER_PLACEMENT,
    TEMPLATE_ELIGIBILITY,
    VERSION_THROTTLE_SECONDS,
    BlockPlacementStatus,
    ContentLayer,
    ContentVersionAction,
    PageStatus,
)
from apps.cms.models import (
    BlockTemplate,
    BlockTemplateActivation,
    CMSApiKey,
    ContentVersion,
    MediaFile,
    MediaUsage,
    Page,
    PageSectionPlacement,
    SectionBlockPlacement,
    SectionTemplate,
    SectionTemplateActivation,
    Site,
)
from apps.cms.selectors import (
    CMSBlockPlacementSelector,
    CMSContentVersionSelector,
    CMSMediaSelector,
    CMSPageSelector,
    CMSSiteSelector,
    CMSTemplateActivationSelector,
    CMSTemplateSelector,
)
from apps.core.exceptions import (
    BusinessRuleViolation,
    ConflictError,
    NotFound,
    PermissionDenied,
    ValidationError,
)
from apps.core.feature_config import feature_config
from apps.core.observability import AuditLog, AuditService, get_logger
from apps.core.types import ActorContext
from apps.rbac.policies import MembershipPolicy
from apps.users.models import User

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Actor Resolution Helper
# Module-level helper — same pattern as apps/rbac/services.py
# and apps/transaction/services.py
# ---------------------------------------------------------------------------


def _resolve_actor(actor_context: ActorContext):
    """Resolve User from ActorContext.user_id for audit logging."""
    try:
        return User.objects.get(id=actor_context.user_id)
    except User.DoesNotExist:
        return None


# ===========================================================================
# Template Activation Check Helper
# ===========================================================================


def _check_template_activation(*, template, owner_type: str, owner_id):
    """
    Verify template is activated for this org.
    Platform context: skip check (platform can use any template).
    Business context: require active activation.
    """
    from apps.core.constants import OwnerType

    if owner_type == OwnerType.PLATFORM:
        return  # Platform uses templates directly

    if owner_type == OwnerType.BUSINESS:
        template_type = "section" if isinstance(template, SectionTemplate) else "block"
        activated = CMSTemplateActivationSelector.is_template_activated(
            template_id=template.id,
            template_type=template_type,
            org_type=owner_type,
            org_id=owner_id,
        )
        if not activated:
            raise BusinessRuleViolation(
                message="Template not activated for this organization",
                rule="template_not_activated",
            )


# ===========================================================================
# CMSTemplateActivationService
# ===========================================================================


class CMSTemplateActivationService:
    """Template activation — orgs select templates from catalog into their library."""

    @staticmethod
    @transaction.atomic
    def activate_section_template(
        *,
        actor_context: ActorContext,
        template_id: UUID,
        request=None,
    ) -> SectionTemplateActivation:
        """Activate a section template for the actor's org."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_activate_cms_template",
        )
        template = CMSTemplateSelector.get_section_template_by_id(
            template_id=template_id
        )

        # Eligibility check
        eligible = TEMPLATE_ELIGIBILITY.get(actor_context.account_type, set())
        if template.org_type not in eligible:
            raise BusinessRuleViolation(
                message="Template not available for this organization type",
                rule="template_not_eligible",
            )

        # Limit check
        current_count = SectionTemplateActivation.objects.filter(
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
            is_active=True,
        ).count()
        feature_config.check_limit(
            f"{actor_context.account_type}.cms.max_active_section_templates",
            current_count,
            rule="max_active_section_templates_exceeded",
            resource="Section template activation",
        )

        actor = _resolve_actor(actor_context)

        # Create or reactivate
        activation, created = SectionTemplateActivation.objects.get_or_create(
            template=template,
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
            defaults={"activated_by": actor, "is_active": True},
        )
        if not created and not activation.is_active:
            activation.is_active = True
            activation.activated_by = actor
            activation.save(update_fields=["is_active", "activated_by", "updated_at"])

        logger.info(
            "cms.template.activated",
            template_id=str(template.id),
            template_type="section",
            org_type=actor_context.account_type,
            org_id=str(actor_context.account_id),
        )
        AuditService.log(
            action=AuditLog.Action.CMS_TEMPLATE_ACTIVATED,
            actor=actor,
            resource=template,
            request=request,
            details={
                "template_type": "section",
                "org_type": actor_context.account_type,
                "org_id": str(actor_context.account_id),
            },
        )
        return activation

    @staticmethod
    @transaction.atomic
    def activate_block_template(
        *,
        actor_context: ActorContext,
        template_id: UUID,
        request=None,
    ) -> BlockTemplateActivation:
        """Activate a block template for the actor's org."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_activate_cms_template",
        )
        template = CMSTemplateSelector.get_block_template_by_id(template_id=template_id)

        # Eligibility check
        eligible = TEMPLATE_ELIGIBILITY.get(actor_context.account_type, set())
        if template.org_type not in eligible:
            raise BusinessRuleViolation(
                message="Template not available for this organization type",
                rule="template_not_eligible",
            )

        # Limit check
        current_count = BlockTemplateActivation.objects.filter(
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
            is_active=True,
        ).count()
        feature_config.check_limit(
            f"{actor_context.account_type}.cms.max_active_block_templates",
            current_count,
            rule="max_active_block_templates_exceeded",
            resource="Block template activation",
        )

        actor = _resolve_actor(actor_context)

        # Create or reactivate
        activation, created = BlockTemplateActivation.objects.get_or_create(
            template=template,
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
            defaults={"activated_by": actor, "is_active": True},
        )
        if not created and not activation.is_active:
            activation.is_active = True
            activation.activated_by = actor
            activation.save(update_fields=["is_active", "activated_by", "updated_at"])

        logger.info(
            "cms.template.activated",
            template_id=str(template.id),
            template_type="block",
            org_type=actor_context.account_type,
            org_id=str(actor_context.account_id),
        )
        AuditService.log(
            action=AuditLog.Action.CMS_TEMPLATE_ACTIVATED,
            actor=actor,
            resource=template,
            request=request,
            details={
                "template_type": "block",
                "org_type": actor_context.account_type,
                "org_id": str(actor_context.account_id),
            },
        )
        return activation

    @staticmethod
    @transaction.atomic
    def deactivate_section_template(
        *,
        actor_context: ActorContext,
        activation_id: UUID,
        request=None,
    ) -> None:
        """Deactivate a section template — sets is_active=False."""
        from apps.cms.policies import CMSActivationPolicy

        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_deactivate_cms_template",
        )
        activation = CMSTemplateActivationSelector.get_section_activation(
            activation_id=activation_id
        )

        # Verify org ownership
        if activation.org_type != actor_context.account_type or str(
            activation.org_id
        ) != str(actor_context.account_id):
            raise PermissionDenied(
                message="Cannot manage activations for another organization"
            )

        # Check template not in use
        CMSActivationPolicy.can_deactivate_section_template(
            activation=activation,
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
        )

        activation.is_active = False
        activation.save(update_fields=["is_active", "updated_at"])

        actor = _resolve_actor(actor_context)
        logger.info(
            "cms.template.deactivated",
            template_id=str(activation.template_id),
            template_type="section",
            org_type=actor_context.account_type,
            org_id=str(actor_context.account_id),
        )
        AuditService.log(
            action=AuditLog.Action.CMS_TEMPLATE_DEACTIVATED,
            actor=actor,
            resource=activation.template,
            request=request,
            details={
                "template_type": "section",
                "org_type": actor_context.account_type,
                "org_id": str(actor_context.account_id),
            },
        )

    @staticmethod
    @transaction.atomic
    def deactivate_block_template(
        *,
        actor_context: ActorContext,
        activation_id: UUID,
        request=None,
    ) -> None:
        """Deactivate a block template — sets is_active=False."""
        from apps.cms.policies import CMSActivationPolicy

        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_deactivate_cms_template",
        )
        activation = CMSTemplateActivationSelector.get_block_activation(
            activation_id=activation_id
        )

        # Verify org ownership
        if activation.org_type != actor_context.account_type or str(
            activation.org_id
        ) != str(actor_context.account_id):
            raise PermissionDenied(
                message="Cannot manage activations for another organization"
            )

        # Check template not in use
        CMSActivationPolicy.can_deactivate_block_template(
            activation=activation,
            org_type=actor_context.account_type,
            org_id=actor_context.account_id,
        )

        activation.is_active = False
        activation.save(update_fields=["is_active", "updated_at"])

        actor = _resolve_actor(actor_context)
        logger.info(
            "cms.template.deactivated",
            template_id=str(activation.template_id),
            template_type="block",
            org_type=actor_context.account_type,
            org_id=str(actor_context.account_id),
        )
        AuditService.log(
            action=AuditLog.Action.CMS_TEMPLATE_DEACTIVATED,
            actor=actor,
            resource=activation.template,
            request=request,
            details={
                "template_type": "block",
                "org_type": actor_context.account_type,
                "org_id": str(actor_context.account_id),
            },
        )

    @staticmethod
    @transaction.atomic
    def auto_provision_defaults(*, org_type: str, org_id, user=None) -> int:
        """
        Auto-activate all is_default=True templates for a new org.
        Called by CMS activation outcome handler and platform admin toggle.
        Returns count of templates activated.
        """
        eligible = TEMPLATE_ELIGIBILITY.get(org_type, set())
        count = 0

        for st in SectionTemplate.objects.filter(
            is_default=True, org_type__in=eligible
        ):
            _, created = SectionTemplateActivation.objects.get_or_create(
                template=st,
                org_type=org_type,
                org_id=org_id,
                defaults={"activated_by": user, "is_active": True},
            )
            if created:
                count += 1

        for bt in BlockTemplate.objects.filter(is_default=True, org_type__in=eligible):
            _, created = BlockTemplateActivation.objects.get_or_create(
                template=bt,
                org_type=org_type,
                org_id=org_id,
                defaults={"activated_by": user, "is_active": True},
            )
            if created:
                count += 1

        logger.info(
            "cms.defaults.provisioned",
            org_type=org_type,
            org_id=str(org_id),
            count=count,
        )
        if count > 0:
            AuditService.log(
                action=AuditLog.Action.CMS_DEFAULTS_PROVISIONED,
                actor=user,
                details={
                    "org_type": org_type,
                    "org_id": str(org_id),
                    "templates_provisioned": count,
                },
            )
        return count


# ===========================================================================
# CMSSiteService
# ===========================================================================


class CMSSiteService:
    """Site lifecycle — create, update, soft-delete."""

    @staticmethod
    @transaction.atomic
    def create_site(
        *,
        actor_context: ActorContext,
        name: str,
        slug: str,
        domain: str = "",
        description: str = "",
        owner_type: str,
        owner_id=None,
        metadata: dict | None = None,
        request: HttpRequest | None = None,
    ) -> Site:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_site",
        )

        # VG limit — business context only
        if owner_type == "business":
            current = Site.objects.filter(
                owner_type=owner_type, owner_id=owner_id
            ).count()
            feature_config.check_limit(
                "business.cms.max_sites",
                current,
                rule="cms_max_sites_exceeded",
                resource="CMS Site",
            )

        # Check slug uniqueness
        if Site.objects.filter(slug=slug).exists():
            raise ConflictError(resource="Site", conflict_type="duplicate")

        actor = _resolve_actor(actor_context)
        site = Site.objects.create(
            name=name,
            slug=slug,
            domain=domain,
            description=description,
            owner_type=owner_type,
            owner_id=owner_id,
            metadata=metadata,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.site.created", site_id=str(site.id), slug=slug)
        AuditService.log(
            action=AuditLog.Action.CMS_SITE_CREATED,
            actor=actor,
            resource=site,
            request=request,
        )
        return site

    @staticmethod
    @transaction.atomic
    def update_site(
        *,
        actor_context: ActorContext,
        slug: str,
        request: HttpRequest | None = None,
        **fields,
    ) -> Site:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_site",
        )

        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=slug,
        )

        actor = _resolve_actor(actor_context)
        allowed_fields = {"name", "domain", "description", "metadata", "is_active"}
        for field, value in fields.items():
            if field in allowed_fields:
                setattr(site, field, value)
        site.updated_by = actor
        site.save()

        logger.info("cms.site.updated", site_id=str(site.id))
        AuditService.log(
            action=AuditLog.Action.CMS_SITE_UPDATED,
            actor=actor,
            resource=site,
            request=request,
        )
        return site

    @staticmethod
    @transaction.atomic
    def delete_site(
        *,
        actor_context: ActorContext,
        slug: str,
        request: HttpRequest | None = None,
    ) -> None:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_delete_cms_site",
        )

        site = CMSSiteSelector.get_by_slug(
            owner_type=actor_context.account_type,
            owner_id=actor_context.account_id,
            slug=slug,
        )

        actor = _resolve_actor(actor_context)
        site.soft_delete(user=actor)

        logger.info("cms.site.deleted", site_id=str(site.id))
        AuditService.log(
            action=AuditLog.Action.CMS_SITE_DELETED,
            actor=actor,
            resource=site,
            request=request,
        )


# ===========================================================================
# CMSTemplateService
# ===========================================================================


class CMSTemplateService:
    """Create/update/delete templates, placement ordering (superuser)."""

    @staticmethod
    @transaction.atomic
    def create_section_template(
        *,
        actor_context: ActorContext,
        name: str,
        display_name: str,
        slug: str,
        section_type: str,
        description: str = "",
        metadata: dict | None = None,
        ui_config: dict | None = None,
        request: HttpRequest | None = None,
    ) -> SectionTemplate:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_template",
        )

        if SectionTemplate.objects.filter(slug=slug).exists():
            raise ConflictError(resource="SectionTemplate", conflict_type="duplicate")

        actor = _resolve_actor(actor_context)
        template = SectionTemplate.objects.create(
            name=name,
            display_name=display_name,
            slug=slug,
            section_type=section_type,
            description=description,
            metadata=metadata,
            ui_config=ui_config,
            created_by=actor,
            updated_by=actor,
        )

        logger.info(
            "cms.section_template.created", template_id=str(template.id), slug=slug
        )
        AuditService.log(
            action=AuditLog.Action.CMS_SECTION_TEMPLATE_CREATED,
            actor=actor,
            resource=template,
            request=request,
        )
        return template

    @staticmethod
    @transaction.atomic
    def create_block_template(
        *,
        actor_context: ActorContext,
        name: str,
        display_name: str,
        slug: str,
        block_type: str,
        schema: dict,
        description: str = "",
        default_content: dict | None = None,
        metadata: dict | None = None,
        ui_config: dict | None = None,
        request: HttpRequest | None = None,
    ) -> BlockTemplate:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_template",
        )

        if BlockTemplate.objects.filter(slug=slug).exists():
            raise ConflictError(resource="BlockTemplate", conflict_type="duplicate")

        from apps.cms.validators import SchemaValidator

        SchemaValidator.validate_schema_structure(schema=schema)

        actor = _resolve_actor(actor_context)
        template = BlockTemplate.objects.create(
            name=name,
            display_name=display_name,
            slug=slug,
            block_type=block_type,
            schema=schema,
            schema_version=1,
            default_content=default_content,
            description=description,
            metadata=metadata,
            ui_config=ui_config,
            created_by=actor,
            updated_by=actor,
        )

        logger.info(
            "cms.block_template.created", template_id=str(template.id), slug=slug
        )
        AuditService.log(
            action=AuditLog.Action.CMS_BLOCK_TEMPLATE_CREATED,
            actor=actor,
            resource=template,
            request=request,
        )
        return template

    @staticmethod
    @transaction.atomic
    def update_block_schema(
        *,
        actor_context: ActorContext,
        template_id: UUID,
        schema: dict,
        request: HttpRequest | None = None,
    ) -> BlockTemplate:
        """Update block template schema. Increments schema_version."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_template",
        )

        template = CMSTemplateSelector.get_block_template_by_id(template_id=template_id)
        old_schema = template.schema

        from apps.cms.validators import SchemaValidator

        SchemaValidator.validate_schema_structure(schema=schema)

        actor = _resolve_actor(actor_context)
        template.schema = schema
        template.schema_version += 1
        template.updated_by = actor
        template.save(
            update_fields=["schema", "schema_version", "updated_by", "updated_at"]
        )

        logger.info(
            "cms.block_template.schema_changed",
            template_id=str(template.id),
            new_version=template.schema_version,
        )
        AuditService.log_change(
            action=AuditLog.Action.CMS_BLOCK_SCHEMA_CHANGED,
            actor=actor,
            resource=template,
            before={"schema": old_schema},
            after={"schema": schema},
            request=request,
        )
        return template

    @staticmethod
    @transaction.atomic
    def reorder_section_placements(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        ordered_placement_ids: list[UUID],
        request: HttpRequest | None = None,
    ) -> None:
        """Atomic bulk reassignment of section placement order within a page."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_page",
        )

        existing_ids = set(
            PageSectionPlacement.objects.filter(page_id=page_id).values_list(
                "id", flat=True
            )
        )
        provided_ids = set(ordered_placement_ids)
        if existing_ids != provided_ids:
            raise ValidationError(
                message="Provided IDs must match exactly the placements on this page",
            )

        # Two-pass update to avoid unique constraint violations on (page, order):
        # Pass 1: Set all orders to high offset (temporary, guaranteed unique)
        offset = 100000
        for index, placement_id in enumerate(ordered_placement_ids):
            PageSectionPlacement.objects.filter(id=placement_id).update(
                order=offset + index
            )
        # Pass 2: Set final order values
        for index, placement_id in enumerate(ordered_placement_ids):
            PageSectionPlacement.objects.filter(id=placement_id).update(order=index)

        logger.info("cms.section_placements.reordered", page_id=str(page_id))

    @staticmethod
    @transaction.atomic
    def reorder_block_placements(
        *,
        actor_context: ActorContext,
        section_placement_id: UUID,
        ordered_placement_ids: list[UUID],
        request: HttpRequest | None = None,
    ) -> None:
        """Atomic bulk reassignment of block placement order within a section."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_page",
        )

        existing_ids = set(
            SectionBlockPlacement.objects.filter(
                section_placement_id=section_placement_id
            ).values_list("id", flat=True)
        )
        provided_ids = set(ordered_placement_ids)
        if existing_ids != provided_ids:
            raise ValidationError(
                message="Provided IDs must match exactly the placements in this section",
            )

        # Two-pass update to avoid unique constraint violations on (section_placement, order):
        # Pass 1: Set all orders to high offset (temporary, guaranteed unique)
        offset = 100000
        for index, placement_id in enumerate(ordered_placement_ids):
            SectionBlockPlacement.objects.filter(id=placement_id).update(
                order=offset + index
            )
        # Pass 2: Set final order values
        for index, placement_id in enumerate(ordered_placement_ids):
            SectionBlockPlacement.objects.filter(id=placement_id).update(order=index)

        logger.info(
            "cms.block_placements.reordered",
            section_placement_id=str(section_placement_id),
        )


# ===========================================================================
# CMSPageService
# ===========================================================================


class CMSPageService:
    """Page lifecycle, ordering, publish/unpublish, export/import."""

    @staticmethod
    @transaction.atomic
    def create_page(
        *,
        actor_context: ActorContext,
        site_id: UUID,
        title: str,
        slug: str,
        path: str,
        page_type: str,
        order: int,
        description: str = "",
        metadata: dict | None = None,
        is_required: bool = False,
        request: HttpRequest | None = None,
    ) -> Page:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_page",
        )

        site = CMSSiteSelector.get_by_id(site_id=site_id)

        # VG limit — business context only
        if site.owner_type == "business":
            current = Page.objects.filter(site=site).count()
            feature_config.check_limit(
                "business.cms.max_pages_per_site",
                current,
                rule="cms_max_pages_per_site_exceeded",
                resource="CMS Page",
            )

        if Page.objects.filter(site=site, slug=slug).exists():
            raise ConflictError(resource="Page", conflict_type="duplicate")

        actor = _resolve_actor(actor_context)
        page = Page.objects.create(
            site=site,
            title=title,
            slug=slug,
            path=path,
            page_type=page_type,
            order=order,
            description=description,
            metadata=metadata,
            is_required=is_required,
            status=PageStatus.DRAFT,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.page.created", page_id=str(page.id), slug=slug)
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_CREATED,
            actor=actor,
            resource=page,
            request=request,
        )
        return page

    @staticmethod
    @transaction.atomic
    def reorder_pages(
        *,
        actor_context: ActorContext,
        site_id: UUID,
        ordered_page_ids: list[UUID],
        request: HttpRequest | None = None,
    ) -> None:
        """Atomic bulk reassignment of page order within a site."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_page",
        )

        existing_ids = set(
            Page.objects.filter(site_id=site_id).values_list("id", flat=True)
        )
        provided_ids = set(ordered_page_ids)
        if existing_ids != provided_ids:
            raise ValidationError(
                message="Provided IDs must match exactly the pages in this site",
            )

        # Two-pass update to avoid unique constraint violations on (site, order):
        offset = 100000
        for index, page_id in enumerate(ordered_page_ids):
            Page.objects.filter(id=page_id).update(order=offset + index)
        for index, page_id in enumerate(ordered_page_ids):
            Page.objects.filter(id=page_id).update(order=index)

        logger.info("cms.pages.reordered", site_id=str(site_id))

    @staticmethod
    @transaction.atomic
    def update_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        request: HttpRequest | None = None,
        **fields,
    ) -> Page:
        """Update page metadata (title, description, path, metadata, is_visible)."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_page",
        )
        page = CMSPageSelector.get_by_id(page_id=page_id)
        actor = _resolve_actor(actor_context)

        allowed = {"title", "description", "path", "metadata", "is_visible"}
        for key, value in fields.items():
            if key in allowed:
                setattr(page, key, value)

        page.updated_by = actor
        page.save()

        logger.info("cms.page.updated", page_id=str(page.id))
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_UPDATED,
            actor=actor,
            resource=page,
            request=request,
        )
        return page

    @staticmethod
    @transaction.atomic
    def delete_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        request: HttpRequest | None = None,
    ) -> None:
        """Soft-delete a page. Respects is_required invariant."""
        from apps.cms.policies import CMSPolicy

        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_delete_cms_page",
        )
        page = CMSPageSelector.get_by_id(page_id=page_id)
        CMSPolicy.can_delete_page(page=page)

        actor = _resolve_actor(actor_context)
        page.soft_delete(user=actor)

        logger.info("cms.page.deleted", page_id=str(page.id))
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_DELETED,
            actor=actor,
            resource=page,
            request=request,
        )

    @staticmethod
    @transaction.atomic
    def publish_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        request: HttpRequest | None = None,
    ) -> Page:
        """
        Atomic publish: validate all blocks, copy draft->published.
        Uses select_for_update() for concurrency safety.
        """
        from apps.cms.validators import SchemaValidator

        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_publish_cms_content",
        )

        # STEP 1: Acquire locks
        page = Page.objects.select_for_update().filter(id=page_id).first()
        if not page:
            raise NotFound(resource="Page", resource_id=page_id)

        list(
            PageSectionPlacement.objects.select_for_update()
            .filter(page=page)
            .order_by("order")
        )
        block_placements = list(
            SectionBlockPlacement.objects.select_for_update()
            .filter(section_placement__page=page)
            .select_related("template")
        )

        # STEP 2: Validate ALL (before any writes)
        publish_errors = []
        for bp in block_placements:
            # Skip hidden, non-required blocks
            if not bp.is_visible and not bp.is_required:
                continue

            errors = SchemaValidator.validate_content(
                schema=bp.template.schema,
                content=bp.draft_content or {},
                strict=True,
            )
            for error in errors:
                publish_errors.append(
                    {
                        "section_placement_id": str(bp.section_placement_id),
                        "block_placement_id": str(bp.id),
                        "block_template": bp.template.slug,
                        **error,
                    }
                )

        if publish_errors:
            # ValidationError only accepts message/field/value, so set details manually
            err = ValidationError(message="Publish validation failed")
            err.details = {"publish_errors": publish_errors}
            raise err

        # STEP 3: Write ALL
        actor = _resolve_actor(actor_context)
        for bp in block_placements:
            bp.published_content = bp.draft_content
            bp.status = BlockPlacementStatus.PUBLISHED
            bp.schema_version_validated = bp.template.schema_version
            bp.save(
                update_fields=[
                    "published_content",
                    "status",
                    "schema_version_validated",
                    "updated_at",
                ]
            )

            _create_content_version(
                block_placement=bp,
                content=bp.draft_content,
                action=ContentVersionAction.PUBLISH,
                actor=actor,
            )

            _sync_media_usage(
                block_placement=bp,
                content=bp.published_content,
                layer=ContentLayer.PUBLISHED,
            )

        page.status = PageStatus.PUBLISHED
        page.published_at = timezone.now()
        page.updated_by = actor
        page.save(update_fields=["status", "published_at", "updated_by", "updated_at"])

        logger.info(
            "cms.page.publish.success",
            page_id=str(page.id),
            block_count=len(block_placements),
        )

        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_PUBLISHED,
            actor=actor,
            resource=page,
            request=request,
            details={
                "block_count": len(block_placements),
                "site_slug": page.site.slug,
            },
        )
        return page

    @staticmethod
    @transaction.atomic
    def unpublish_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        request: HttpRequest | None = None,
    ) -> Page:
        """Revert page to draft. published_content is NOT cleared."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_publish_cms_content",
        )

        page = CMSPageSelector.get_by_id(page_id=page_id)
        if page.status != PageStatus.PUBLISHED:
            raise BusinessRuleViolation(
                message="Only published pages can be unpublished",
                rule="unpublish_from_published",
            )

        actor = _resolve_actor(actor_context)

        SectionBlockPlacement.objects.filter(section_placement__page=page).update(
            status=BlockPlacementStatus.DRAFT
        )

        page.status = PageStatus.DRAFT
        page.updated_by = actor
        page.save(update_fields=["status", "updated_by", "updated_at"])

        logger.info("cms.page.unpublished", page_id=str(page.id))
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_UNPUBLISHED,
            actor=actor,
            resource=page,
            request=request,
        )
        return page

    @staticmethod
    def export_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        request: HttpRequest | None = None,
    ) -> dict:
        """Export page tree as JSON (see spec Section 10.1)."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_export_cms_content",
        )

        page = CMSPageSelector.get_with_full_tree(page_id=page_id)
        actor = _resolve_actor(actor_context)

        export_data = {
            "export_version": "3.1",
            "exported_at": timezone.now().isoformat(),
            "exported_by": str(actor_context.user_id),
            "source_site": page.site.slug,
            "source_owner_type": page.site.owner_type,
            "source_owner_id": str(page.site.owner_id),
            "page": _serialize_page_for_export(page),
        }

        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_EXPORTED,
            actor=actor,
            resource=page,
            request=request,
        )
        return export_data

    @staticmethod
    @transaction.atomic
    def import_page(
        *,
        actor_context: ActorContext,
        page_id: UUID,
        import_data: dict,
        request: HttpRequest | None = None,
    ) -> Page:
        """Content-only import: match block placements by UUID, update draft_content."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_import_cms_content",
        )

        page = CMSPageSelector.get_by_id(page_id=page_id)
        actor = _resolve_actor(actor_context)

        imported_blocks = _extract_block_placements_from_import(import_data)
        for bp_data in imported_blocks:
            bp = (
                SectionBlockPlacement.objects.filter(
                    id=bp_data["id"],
                    section_placement__page=page,
                )
                .select_related("template")
                .first()
            )
            if not bp:
                continue  # Skip non-matching UUIDs

            from apps.cms.validators import SchemaValidator

            SchemaValidator.validate_content(
                schema=bp.template.schema,
                content=bp_data.get("draft_content", {}),
                strict=False,
            )
            # Store regardless (permissive import)
            bp.draft_content = bp_data.get("draft_content", bp.draft_content)
            bp.updated_by = actor
            bp.save(update_fields=["draft_content", "updated_by", "updated_at"])

            _create_content_version(
                block_placement=bp,
                content=bp.draft_content,
                action=ContentVersionAction.IMPORT,
                actor=actor,
            )

        logger.info("cms.page.imported", page_id=str(page.id))
        AuditService.log(
            action=AuditLog.Action.CMS_PAGE_IMPORTED,
            actor=actor,
            resource=page,
            request=request,
        )
        return page


# ===========================================================================
# CMSContentService
# ===========================================================================


class CMSContentService:
    """Draft content editing, rollback, visibility toggling."""

    @staticmethod
    @transaction.atomic
    def update_draft_content(
        *,
        actor_context: ActorContext,
        block_placement_id: UUID,
        content: dict,
        request: HttpRequest | None = None,
    ) -> SectionBlockPlacement:
        """
        Update draft_content on a block placement.
        Validates permissively (warnings, not errors).
        Creates ContentVersion with throttling.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_content",
        )

        placement = CMSBlockPlacementSelector.get_by_id(
            block_placement_id=block_placement_id
        )

        from apps.cms.validators import SchemaValidator

        content = SchemaValidator.sanitize_content(
            schema=placement.template.schema,
            content=content,
        )
        SchemaValidator.validate_content(
            schema=placement.template.schema,
            content=content,
            strict=False,
        )

        old_content = placement.draft_content
        actor = _resolve_actor(actor_context)

        placement.draft_content = content
        placement.updated_by = actor
        placement.save(update_fields=["draft_content", "updated_by", "updated_at"])

        _create_content_version_throttled(
            block_placement=placement,
            content=content,
            action=ContentVersionAction.DRAFT_SAVE,
            actor=actor,
        )

        _sync_media_usage(
            block_placement=placement,
            content=content,
            layer=ContentLayer.DRAFT,
        )

        logger.info(
            "cms.content.draft_saved",
            placement_id=str(placement.id),
        )
        AuditService.log_change(
            action=AuditLog.Action.CMS_CONTENT_DRAFT_SAVED,
            actor=actor,
            resource=placement,
            before={"draft_content": old_content},
            after={"draft_content": content},
            request=request,
        )

        return placement

    @staticmethod
    @transaction.atomic
    def rollback_content(
        *,
        actor_context: ActorContext,
        block_placement_id: UUID,
        version_number: int,
        request: HttpRequest | None = None,
    ) -> SectionBlockPlacement:
        """
        Rollback draft_content to a previous version.
        Does NOT update published_content — admin must re-publish.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_rollback_cms_content",
        )

        placement = CMSBlockPlacementSelector.get_by_id(
            block_placement_id=block_placement_id
        )
        version = CMSContentVersionSelector.get_version(
            block_placement_id=block_placement_id,
            version_number=version_number,
        )

        actor = _resolve_actor(actor_context)
        placement.draft_content = version.content_snapshot
        placement.updated_by = actor
        placement.save(update_fields=["draft_content", "updated_by", "updated_at"])

        _create_content_version(
            block_placement=placement,
            content=version.content_snapshot,
            action=ContentVersionAction.ROLLBACK,
            actor=actor,
            notes=f"Rolled back to version {version_number}",
        )

        logger.info(
            "cms.content.rollback",
            placement_id=str(placement.id),
            to_version=version_number,
        )
        AuditService.log(
            action=AuditLog.Action.CMS_CONTENT_ROLLBACK,
            actor=actor,
            resource=placement,
            request=request,
            details={"rolled_back_to_version": version_number},
        )
        return placement

    @staticmethod
    @transaction.atomic
    def toggle_visibility(
        *,
        actor_context: ActorContext,
        block_placement_id: UUID,
        is_visible: bool,
        request: HttpRequest | None = None,
    ) -> SectionBlockPlacement:
        """Toggle visibility on a non-required block placement."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_toggle_cms_visibility",
        )

        placement = CMSBlockPlacementSelector.get_by_id(
            block_placement_id=block_placement_id
        )

        if placement.is_required and not is_visible:
            raise BusinessRuleViolation(
                message="Cannot hide a required block placement",
                rule="required_placement_visibility",
            )

        actor = _resolve_actor(actor_context)
        placement.is_visible = is_visible
        placement.updated_by = actor
        placement.save(update_fields=["is_visible", "updated_by", "updated_at"])

        logger.info(
            "cms.visibility.toggled",
            placement_id=str(placement.id),
            is_visible=is_visible,
        )
        AuditService.log(
            action=AuditLog.Action.CMS_VISIBILITY_TOGGLED,
            actor=actor,
            resource=placement,
            request=request,
            details={"is_visible": is_visible},
        )
        return placement


# ===========================================================================
# CMSMediaService
# ===========================================================================


class CMSMediaService:
    """File upload, delete, tombstone cleanup."""

    @staticmethod
    @transaction.atomic
    def upload_file(
        *,
        actor_context: ActorContext,
        owner_type: str,
        owner_id: UUID,
        file,  # Django UploadedFile
        folder_id: UUID | None = None,
        alt_text: str = "",
        title: str = "",
        request: HttpRequest | None = None,
    ) -> MediaFile:
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_upload_cms_media",
        )

        # VG limits — business context only
        if owner_type == "business":
            current = MediaFile.objects.filter(
                owner_type=owner_type, owner_id=owner_id
            ).count()
            feature_config.check_limit(
                "business.cms.max_media_files",
                current,
                rule="cms_max_media_files_exceeded",
                resource="CMS Media File",
            )
            max_mb = feature_config.get_value("business.cms.max_media_file_size_mb", 10)
            if max_mb and file.size > max_mb * 1024 * 1024:
                raise ValidationError(
                    message=f"File size exceeds {max_mb}MB limit",
                    field="file",
                )

        import uuid as uuid_mod

        from django.core.files.storage import default_storage

        from apps.cms.constants import ALLOWED_MEDIA_EXTENSIONS, ALLOWED_MEDIA_TYPES

        actor = _resolve_actor(actor_context)

        # Validate file type (extension + MIME type whitelist)
        ext = file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        mime = (file.content_type or "").lower()
        if ext not in ALLOWED_MEDIA_EXTENSIONS:
            raise ValidationError(
                message=f"File extension '.{ext}' is not allowed",
                field="file",
            )
        if mime not in ALLOWED_MEDIA_TYPES:
            raise ValidationError(
                message=f"File type '{mime}' is not allowed",
                field="file",
            )

        storage_key = f"{owner_type}/{str(owner_id)}/media/{uuid_mod.uuid4().hex}.{ext}"

        saved_path = default_storage.save(storage_key, file)

        media = MediaFile.objects.create(
            owner_type=owner_type,
            owner_id=owner_id,
            folder_id=folder_id,
            storage_key=saved_path,
            original_filename=file.name,
            mime_type=file.content_type or "application/octet-stream",
            file_size=file.size,
            alt_text=alt_text,
            title=title,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.media.uploaded", file_id=str(media.id), filename=file.name)
        AuditService.log(
            action=AuditLog.Action.CMS_MEDIA_UPLOADED,
            actor=actor,
            resource=media,
            request=request,
        )
        return media

    @staticmethod
    @transaction.atomic
    def update_file(
        *,
        actor_context: ActorContext,
        file_id: UUID,
        request: HttpRequest | None = None,
        **fields,
    ) -> MediaFile:
        """Update media file metadata (alt_text, title, folder)."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_edit_cms_media",
        )

        media = CMSMediaSelector.get_file_by_id(file_id=file_id)
        actor = _resolve_actor(actor_context)

        allowed_fields = {"alt_text", "title"}
        for field, value in fields.items():
            if field in allowed_fields:
                setattr(media, field, value)

        if "folder_id" in fields:
            media.folder_id = fields["folder_id"]

        media.updated_by = actor
        media.save()

        logger.info("cms.media.updated", file_id=str(media.id))
        AuditService.log(
            action=AuditLog.Action.CMS_MEDIA_UPDATED,
            actor=actor,
            resource=media,
            request=request,
        )
        return media

    @staticmethod
    @transaction.atomic
    def delete_file(
        *,
        actor_context: ActorContext,
        file_id: UUID,
        request: HttpRequest | None = None,
    ) -> MediaFile:
        """
        Delete a media file. If published content references it,
        tombstone instead of deleting.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_delete_cms_media",
        )

        media = CMSMediaSelector.get_file_by_id(file_id=file_id)
        actor = _resolve_actor(actor_context)

        published_usage_count = MediaUsage.objects.filter(
            media_file=media,
            content_layer=ContentLayer.PUBLISHED,
        ).count()

        if published_usage_count > 0:
            media.is_tombstoned = True
            media.updated_by = actor
            media.save(update_fields=["is_tombstoned", "updated_by", "updated_at"])

            _null_draft_media_references(media_file=media)

            logger.info("cms.media.tombstoned", file_id=str(media.id))
            AuditService.log(
                action=AuditLog.Action.CMS_MEDIA_TOMBSTONED,
                actor=actor,
                resource=media,
                request=request,
                details={"published_refs": published_usage_count},
            )
        else:
            media.soft_delete(user=actor)

            logger.info("cms.media.deleted", file_id=str(media.id))
            AuditService.log(
                action=AuditLog.Action.CMS_MEDIA_DELETED,
                actor=actor,
                resource=media,
                request=request,
            )

        return media

    @staticmethod
    @transaction.atomic
    def delete_folder(
        *,
        actor_context: ActorContext,
        folder_id: UUID,
        request: HttpRequest | None = None,
    ) -> None:
        """
        Soft-delete a folder and recursively soft-delete all children.

        Defense-in-depth: models.CASCADE only fires on hard delete.
        Soft delete requires explicit recursion to avoid orphaned children.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_delete_cms_media",
        )

        folder = CMSMediaSelector.get_folder_by_id(folder_id=folder_id)
        actor = _resolve_actor(actor_context)

        def _soft_delete_recursive(parent_folder):
            for child in parent_folder.children.filter(is_deleted=False):
                _soft_delete_recursive(child)
                child.soft_delete(user=actor)

        _soft_delete_recursive(folder)
        folder.soft_delete(user=actor)

        logger.info("cms.media_folder.deleted", folder_id=str(folder.id))

    @staticmethod
    def cleanup_tombstoned() -> int:
        """
        Celery task: Remove tombstoned files with zero published references.
        Returns count of files cleaned up.

        NOTE: No @transaction.atomic — each file is cleaned independently.
        A storage error on one file must not roll back successful deletions.
        """
        from django.core.files.storage import default_storage

        tombstoned = MediaFile.objects.filter(is_tombstoned=True)
        cleaned = 0

        for media in tombstoned:
            published_count = MediaUsage.objects.filter(
                media_file=media,
                content_layer=ContentLayer.PUBLISHED,
            ).count()

            if published_count == 0:
                try:
                    default_storage.delete(media.storage_key)
                except Exception:
                    logger.warning(
                        "cms.media.cleanup.storage_error",
                        file_id=str(media.id),
                        storage_key=media.storage_key,
                    )
                    continue
                media.delete()
                cleaned += 1

        logger.info("cms.media.cleanup.complete", cleaned_count=cleaned)
        return cleaned


# ===========================================================================
# CMSApiKeyService
# ===========================================================================


class CMSApiKeyService:
    """API key lifecycle for public API access."""

    @staticmethod
    @transaction.atomic
    def create_api_key(
        *,
        actor_context: ActorContext,
        site_id: UUID,
        name: str,
        allowed_origins: list[str] | None = None,
        rate_limit: int = 60,
        expires_at=None,
        request: HttpRequest | None = None,
    ) -> tuple[CMSApiKey, str]:
        """
        Create a new API key. Returns (api_key_record, plaintext_key).
        Plaintext is returned ONCE and never stored.
        """
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_create_cms_api_key",
        )

        site = CMSSiteSelector.get_by_id(site_id=site_id)

        # VG limits — business context only
        if site.owner_type == "business":
            current = CMSApiKey.objects.filter(site=site).count()
            feature_config.check_limit(
                "business.cms.max_api_keys_per_site",
                current,
                rule="cms_max_api_keys_per_site_exceeded",
                resource="CMS API Key",
            )
            # Use business-specific rate limit if no override provided
            if rate_limit == 60:
                biz_rate = feature_config.get_value(
                    "business.cms.api_key_rate_limit", 60
                )
                rate_limit = biz_rate

        actor = _resolve_actor(actor_context)

        plaintext, prefix, key_hash = CMSApiKey.generate_key()

        api_key = CMSApiKey.objects.create(
            site=site,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            allowed_origins=allowed_origins or [],
            rate_limit=rate_limit,
            expires_at=expires_at,
            is_active=True,
            created_by=actor,
            updated_by=actor,
        )

        logger.info("cms.api_key.created", key_id=str(api_key.id), site_id=str(site_id))
        AuditService.log(
            action=AuditLog.Action.CMS_API_KEY_CREATED,
            actor=actor,
            resource=api_key,
            request=request,
        )
        return api_key, plaintext

    @staticmethod
    @transaction.atomic
    def revoke_api_key(
        *,
        actor_context: ActorContext,
        api_key_id: UUID,
        request: HttpRequest | None = None,
    ) -> CMSApiKey:
        """Revoke (soft-delete) an API key."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_revoke_cms_api_key",
        )

        api_key = CMSApiKey.objects.filter(id=api_key_id, is_deleted=False).first()
        if not api_key:
            raise NotFound(resource="CMSApiKey", resource_id=api_key_id)

        actor = _resolve_actor(actor_context)
        api_key.is_active = False
        api_key.save(update_fields=["is_active", "updated_at"])
        api_key.soft_delete(user=actor)

        logger.info("cms.api_key.revoked", key_id=str(api_key.id))
        AuditService.log(
            action=AuditLog.Action.CMS_API_KEY_REVOKED,
            actor=actor,
            resource=api_key,
            request=request,
        )
        return api_key

    @staticmethod
    def validate_api_key(*, plaintext_key: str) -> CMSApiKey:
        """
        Validate an API key from request header.
        Checks: exists, active, not expired.
        """
        key_hash = CMSApiKey.hash_key(plaintext_key)
        api_key = (
            CMSApiKey.objects.filter(key_hash=key_hash, is_deleted=False)
            .select_related("site")
            .first()
        )

        if not api_key:
            raise PermissionDenied(message="Invalid API key")

        if not api_key.is_active:
            raise PermissionDenied(message="API key is inactive")

        if api_key.expires_at and api_key.expires_at < timezone.now():
            raise PermissionDenied(message="API key has expired")

        # Update last_used_at
        CMSApiKey.objects.filter(id=api_key.id).update(last_used_at=timezone.now())

        return api_key


# ---------------------------------------------------------------------------
# Internal helpers (module-level, not exposed)
# ---------------------------------------------------------------------------


def _create_content_version(
    *,
    block_placement: SectionBlockPlacement,
    content: dict,
    action: str,
    actor,
    notes: str = "",
) -> ContentVersion:
    """Create a content version snapshot."""
    latest = CMSContentVersionSelector.get_latest_version(
        block_placement_id=block_placement.id
    )
    next_number = (latest.version_number + 1) if latest else 1

    version = ContentVersion.objects.create(
        block_placement=block_placement,
        content_snapshot=content or {},
        version_number=next_number,
        action=action,
        created_by=actor,
        notes=notes,
    )

    _prune_old_versions(block_placement_id=block_placement.id)

    return version


def _create_content_version_throttled(
    *,
    block_placement: SectionBlockPlacement,
    content: dict,
    action: str,
    actor,
) -> ContentVersion | None:
    """
    Create version with throttling: max 1 per 30 seconds.
    Within the window, updates the latest version in-place
    (only if same user, same action=draft_save).
    """
    latest = CMSContentVersionSelector.get_latest_version(
        block_placement_id=block_placement.id
    )

    if (
        latest
        and latest.action == ContentVersionAction.DRAFT_SAVE
        and latest.created_by == actor
        and (timezone.now() - latest.created_at).total_seconds()
        < feature_config.get_value(
            "cms.version_throttle_seconds", VERSION_THROTTLE_SECONDS
        )
    ):
        # Update in-place
        latest.content_snapshot = content or {}
        latest.save(update_fields=["content_snapshot"])
        return latest

    return _create_content_version(
        block_placement=block_placement,
        content=content,
        action=action,
        actor=actor,
    )


def _prune_old_versions(*, block_placement_id: UUID) -> None:
    """Remove versions beyond MAX_VERSIONS_PER_PLACEMENT (oldest first)."""
    version_ids = list(
        ContentVersion.objects.filter(block_placement_id=block_placement_id)
        .order_by("-version_number")
        .values_list("id", flat=True)[
            feature_config.get_value(
                "cms.max_versions_per_placement", MAX_VERSIONS_PER_PLACEMENT
            ) :
        ]
    )
    if version_ids:
        ContentVersion.objects.filter(id__in=version_ids).delete()


def _sync_media_usage(
    *,
    block_placement: SectionBlockPlacement,
    content: dict | None,
    layer: str,
) -> None:
    """
    Scan content JSONB for media references and sync MediaUsage records.
    Deletes old usages for this layer, creates new ones.
    """
    MediaUsage.objects.filter(
        block_placement=block_placement,
        content_layer=layer,
    ).delete()

    if not content:
        return

    media_refs = _extract_media_references(content=content)

    for field_key, media_id in media_refs:
        MediaUsage.objects.create(
            media_file_id=media_id,
            block_placement=block_placement,
            field_key=field_key,
            content_layer=layer,
        )


def _extract_media_references(
    *, content: dict, prefix: str = ""
) -> list[tuple[str, UUID]]:
    """
    Recursively extract (field_key, media_id) pairs from content JSONB.
    Handles media fields {"media_id": "uuid", "alt": "..."} and repeaters.
    """
    refs = []
    for key, value in content.items():
        full_key = f"{prefix}.{key}" if prefix else key

        if isinstance(value, dict) and "media_id" in value:
            try:
                refs.append((full_key, UUID(value["media_id"])))
            except (ValueError, TypeError):
                pass
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    refs.extend(
                        _extract_media_references(
                            content=item,
                            prefix=f"{full_key}[{i}]",
                        )
                    )
    return refs


def _null_draft_media_references(*, media_file: MediaFile) -> None:
    """Null out all draft_content references to a deleted media file."""
    draft_usages = MediaUsage.objects.filter(
        media_file=media_file,
        content_layer=ContentLayer.DRAFT,
    ).select_related("block_placement")

    for usage in draft_usages:
        bp = usage.block_placement
        if bp.draft_content:
            _null_media_id_in_content(
                content=bp.draft_content,
                target_media_id=str(media_file.id),
            )
            bp.save(update_fields=["draft_content", "updated_at"])

    MediaUsage.objects.filter(
        media_file=media_file,
        content_layer=ContentLayer.DRAFT,
    ).delete()


def _null_media_id_in_content(*, content: dict, target_media_id: str) -> None:
    """Recursively null out media references matching target_media_id."""
    for key, value in content.items():
        if isinstance(value, dict) and value.get("media_id") == target_media_id:
            content[key] = None
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _null_media_id_in_content(
                        content=item, target_media_id=target_media_id
                    )


def _serialize_page_for_export(page: Page) -> dict:
    """Serialize a page with full tree for export."""
    return {
        "slug": page.slug,
        "title": page.title,
        "path": page.path,
        "page_type": page.page_type,
        "status": page.status,
        "metadata": page.metadata,
        "section_placements": [
            {
                "id": str(sp.id),
                "template_slug": sp.template.slug,
                "order": sp.order,
                "is_required": sp.is_required,
                "is_visible": sp.is_visible,
                "block_placements": [
                    {
                        "id": str(bp.id),
                        "template_slug": bp.template.slug,
                        "order": bp.order,
                        "is_required": bp.is_required,
                        "is_visible": bp.is_visible,
                        "schema": bp.template.schema,
                        "draft_content": bp.draft_content,
                        "published_content": bp.published_content,
                        "default_content": bp.template.default_content,
                    }
                    for bp in sp.block_placements.order_by("order")
                ],
            }
            for sp in page.section_placements.order_by("order")
        ],
    }


def _extract_block_placements_from_import(import_data: dict) -> list[dict]:
    """Extract block placement data from import JSON."""
    blocks = []
    page_data = import_data.get("page", {})
    for sp in page_data.get("section_placements", []):
        for bp in sp.get("block_placements", []):
            blocks.append(bp)
    return blocks
