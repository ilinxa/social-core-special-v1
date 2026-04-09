# CMS Business Access & Template Activation System — Implementation Plan

**Version:** 1.1 (reviewed 2026-03-29)
**Date:** 2026-03-29
**Scope:** Backend only
**Depends on:** CMS System (complete), Feature Gate System (complete), Transaction System (complete), RBAC System (complete)

---

## 1. Overview & Goals

Extend the CMS system from platform-only to support business organizations:

1. **Template Eligibility** — `org_type` field on templates controls which org types can use them
2. **Template Activation** — Orgs select templates from a catalog into their library before using them
3. **Per-Business CMS Flag** — `cms_enabled` on BusinessAccount, controlled by platform admin or transaction flow
4. **CMS Activation Transaction** — Business requests CMS access, platform approves, outcome handler provisions defaults
5. **Business-Scoped API** — Full CMS CRUD for businesses (sites, pages, placements, media, API keys)
6. **Limits** — VG-enforced caps on sites, pages, templates, media, API keys per business
7. **Platform Management** — Platform admin can enable/disable CMS for businesses, view activation status

### What Does NOT Change
- Template CRUD — superuser-only via Django Admin (unchanged)
- Public API — API key → site → content, already supports any owner_type (unchanged)
- Platform admin views — existing endpoints remain identical
- ContentVersion, schema validation, media tombstoning — all unchanged
- Template `created_by`/`updated_by` — already tracked via AuditModel inheritance

---

## 2. Architecture Decisions

### AD-1: No separate `cms.org_mode` config field
The existing feature gate structure already expresses all three modes:

| Desired Mode | `systems.cms` | `platform.cms` | `business.cms.enabled` |
|---|---|---|---|
| None (CMS off) | `false` | — | — |
| Platform only | `true` | `true` | `false` |
| Platform + Business | `true` | `true` | `true` |

No ambiguity, no conflicting fields. Documentation clarifies which booleans to set.

### AD-2: Templates are NOT owned — `org_type` is an eligibility filter
`org_type` on BlockTemplate/SectionTemplate controls which org types can **activate** (use) the template. Templates have no `owner_id` — they are platform-wide infrastructure managed by superuser.

### AD-3: Activation is a lightweight pointer, not a copy
`TemplateActivation` records are access-control gates + limit counters. No content is copied. Placements still reference canonical templates. Schema always comes from the canonical template.

### AD-4: Activation check only for business context
Platform admin can use any template directly (existing behavior, unchanged). Business context requires an active `TemplateActivation` record before creating placements.

### AD-5: Business CMS URLs under CMS namespace
`/api/v1/cms/business/<slug>/...` — keeps all CMS routes under the same system gate. Business slug in URL for `BusinessContextMixin` resolution.

### AD-6: Public API unchanged
API key maps to site, site has `owner_type`/`owner_id`. When a business creates a site and API key, the public API serves it through the existing middleware. No code change needed.

---

## 3. Feature Gate Design

### 3.1 Deployment Config Changes

```json
{
  "systems": {
    "cms": true
  },
  "platform": {
    "cms": true
  },
  "business": {
    "cms": {
      "enabled": true,
      "activation_request": true,
      "max_sites": 1,
      "max_pages_per_site": 20,
      "max_api_keys_per_site": 3,
      "max_active_block_templates": 20,
      "max_active_section_templates": 10,
      "max_media_files": 100,
      "max_media_file_size_mb": 10,
      "api_key_rate_limit": 60
    }
  },
  "cms": {
    "max_versions_per_placement": 50,
    "max_folder_depth": 5,
    "version_throttle_seconds": 30,
    "api_key_rate_limit": 60,
    "allowed_media_types": ["jpeg", "png", "gif", "webp", "svg", "pdf", "mp4", "webm", "mp3", "ogg"]
  }
}
```

**Key semantics:**
- `systems.cms` — SG gate: CMS URLs mount (existing)
- `platform.cms` — FG gate: platform admin CMS access (existing, stays boolean)
- `business.cms.enabled` — FG gate: business CMS feature available in this deployment
- `business.cms.activation_request` — FG gate: transaction request flow available
- `business.cms.max_*` — VG limits: per-business caps (0 = unlimited)
- `cms.*` — Cross-scope VG values: shared configuration (existing)

### 3.2 Gate Enforcement Points

| Gate | Where Enforced | Effect When Disabled |
|------|---------------|---------------------|
| `systems.cms` | URL coordinator (`urls/__init__.py`) | CMS URLs don't mount (404) |
| `platform.cms` | `FeatureRequired("platform.cms")` on admin views | 403 FeatureDisabled |
| `business.cms.enabled` | `FeatureRequired("business.cms.enabled")` on business views | 403 FeatureDisabled |
| `business.cms.activation_request` | `_REQUEST_FEATURE_GATES` in transaction services | FeatureDisabled on request creation |
| `BusinessAccount.cms_enabled` | Service-level check in business CMS views | 403 "CMS not enabled for this business" |

### 3.3 Three-Layer Access Check (Business CMS Views)

Every business CMS view performs, in order:

```
1. FeatureRequired("business.cms.enabled")    → deployment allows business CMS?
2. BusinessContextMixin.get_actor_context()    → user is active business member?
3. business.cms_enabled == True                → THIS business has CMS?
4. MembershipPolicy.authorize_action(perm)     → user has required permission?
```

---

## 4. Phase 1: Data Layer (Models + Migrations)

### 4.1 Template Org Type Fields

**Files:** `apps/cms/models.py`, `apps/cms/constants.py`

Add to `BlockTemplate` and `SectionTemplate`:

```python
# constants.py — NEW enum
class TemplateOrgType(models.TextChoices):
    SYSTEM = "system", "System"         # Internal only, not activatable
    PLATFORM = "platform", "Platform"   # Platform orgs only
    BUSINESS = "business", "Business"   # Business orgs only
    ALL = "all", "All"                  # Both platform and business

# models.py — ADD to BlockTemplate
org_type = models.CharField(
    max_length=20,
    choices=TemplateOrgType.choices,
    default=TemplateOrgType.ALL,
    db_index=True,
    help_text="Which organization types can activate and use this template.",
)
is_default = models.BooleanField(
    default=False,
    help_text="Auto-activate for new orgs when CMS is enabled.",
)

# models.py — ADD to SectionTemplate (same two fields)
```

**Admin changes** (`apps/cms/admin.py`):
- Add `org_type`, `is_default` to `list_display` and `list_filter` for both template admins

**Migration:** `apps/cms/migrations/0003_template_org_type_fields.py`
- AddField `org_type` with default `"all"` to both templates
- AddField `is_default` with default `False` to both templates
- RunPython: backfill all existing templates to `org_type="all"`, `is_default=True`

### 4.2 Template Activation Models

**File:** `apps/cms/models.py`

```python
class SectionTemplateActivation(UUIDModel, TimeStampedModel):
    """
    Records that an organization has activated a section template for use.

    INVARIANT: Unique(template, org_type, org_id) — one activation per template per org.
    """
    template = models.ForeignKey(
        SectionTemplate,
        on_delete=models.PROTECT,
        related_name="activations",
    )
    org_type = models.CharField(max_length=20, choices=OwnerType.choices, db_index=True)
    org_id = models.UUIDField(db_index=True)
    is_active = models.BooleanField(default=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cms_section_activations",
    )

    class Meta:
        db_table = "cms_section_template_activation"
        constraints = [
            models.UniqueConstraint(
                fields=["template", "org_type", "org_id"],
                name="unique_section_activation_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["org_type", "org_id", "is_active"]),
        ]

class BlockTemplateActivation(UUIDModel, TimeStampedModel):
    """Same structure for block templates."""
    template = models.ForeignKey(
        BlockTemplate,
        on_delete=models.PROTECT,
        related_name="activations",
    )
    org_type = models.CharField(max_length=20, choices=OwnerType.choices, db_index=True)
    org_id = models.UUIDField(db_index=True)
    is_active = models.BooleanField(default=True)
    activated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="cms_block_activations",
    )

    class Meta:
        db_table = "cms_block_template_activation"
        constraints = [
            models.UniqueConstraint(
                fields=["template", "org_type", "org_id"],
                name="unique_block_activation_per_org",
            ),
        ]
        indexes = [
            models.Index(fields=["org_type", "org_id", "is_active"]),
        ]
```

**Managers** (`apps/cms/managers.py`):

```python
class TemplateActivationQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_org(self, org_type, org_id):
        return self.filter(org_type=org_type, org_id=org_id)

class SectionTemplateActivationManager(models.Manager):
    def get_queryset(self):
        return TemplateActivationQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

class BlockTemplateActivationManager(models.Manager):
    # Same pattern
```

**Migration:** `apps/cms/migrations/0004_template_activation_models.py`
- CreateModel SectionTemplateActivation
- CreateModel BlockTemplateActivation
- AddConstraint (unique per org)
- AddIndex (org_type, org_id, is_active)

### 4.3 BusinessAccount.cms_enabled

**File:** `apps/organization/business/models.py`

```python
# ADD after open_member_request field (line ~119)
cms_enabled = models.BooleanField(
    default=False,
    db_index=True,
    help_text="Whether this business has CMS access enabled.",
)
```

**Migration:** `apps/organization/migrations/000X_add_business_cms_enabled.py`
- AddField `cms_enabled` BooleanField default=False

### 4.4 RBAC Permission Seed

**File:** `apps/rbac/migrations/0013_seed_cms_activation_permissions.py`

New permissions:

```python
PERMISSIONS = [
    # CMS Activation Management (platform-only)
    (
        "can_approve_cms_activation",
        "Approve CMS Activation",
        "Approve or deny business CMS activation requests",
        "cms_management",
        ["platform_only"],
    ),
    (
        "can_manage_business_cms",
        "Manage Business CMS",
        "Directly enable or disable CMS for businesses",
        "cms_management",
        ["platform_only"],
    ),
    # Template Activation (business + platform)
    (
        "can_activate_cms_template",
        "Activate CMS Template",
        "Activate templates from the catalog into the organization library",
        "cms_structure",
        ["business", "platform_only"],
    ),
    (
        "can_deactivate_cms_template",
        "Deactivate CMS Template",
        "Remove templates from the organization library",
        "cms_structure",
        ["business", "platform_only"],
    ),
]
```

**Note:** Existing CMS content permissions (`can_view_cms_content`, `can_edit_cms_content`, etc.) already have `business` in their `applicable_scopes`. No change needed.

---

## 5. Phase 2: Template Activation System

### 5.1 Constants

**File:** `apps/cms/constants.py` — additions:

```python
class TemplateOrgType(models.TextChoices):
    SYSTEM = "system", "System"
    PLATFORM = "platform", "Platform"
    BUSINESS = "business", "Business"
    ALL = "all", "All"

# Eligibility mapping: given an org's OwnerType, which TemplateOrgTypes are visible?
TEMPLATE_ELIGIBILITY = {
    OwnerType.PLATFORM: {TemplateOrgType.PLATFORM, TemplateOrgType.ALL},
    OwnerType.BUSINESS: {TemplateOrgType.BUSINESS, TemplateOrgType.ALL},
}
```

### 5.2 Selectors

**File:** `apps/cms/selectors.py` — new class:

```python
class CMSTemplateActivationSelector:

    @staticmethod
    def list_available_section_templates(*, org_type: str, org_id: UUID):
        """Templates eligible for this org type, NOT yet activated."""
        eligible_org_types = TEMPLATE_ELIGIBILITY.get(org_type, set())
        activated_ids = SectionTemplateActivation.objects.filter(
            org_type=org_type, org_id=org_id,
        ).values_list("template_id", flat=True)
        return SectionTemplate.objects.filter(
            org_type__in=eligible_org_types,
        ).exclude(id__in=activated_ids)

    @staticmethod
    def list_available_block_templates(*, org_type: str, org_id: UUID):
        """Same for block templates."""
        # Same pattern

    @staticmethod
    def list_activated_section_templates(*, org_type: str, org_id: UUID):
        """Templates this org has activated (active only)."""
        return SectionTemplate.objects.filter(
            activations__org_type=org_type,
            activations__org_id=org_id,
            activations__is_active=True,
        ).select_related()

    @staticmethod
    def list_activated_block_templates(*, org_type: str, org_id: UUID):
        """Same for block templates."""
        # Same pattern

    @staticmethod
    def get_section_activation(*, activation_id: UUID):
        """Get a specific activation record."""

    @staticmethod
    def get_block_activation(*, activation_id: UUID):
        """Get a specific activation record."""

    @staticmethod
    def is_template_activated(*, template_id: UUID, template_type: str, org_type: str, org_id: UUID) -> bool:
        """Check if a specific template is activated for this org."""
```

**Modify existing selectors** — `CMSTemplateSelector`:

```python
# ADD parameter to filter by org_type eligibility:
@staticmethod
def list_section_templates(*, section_type=None, org_type_filter=None):
    qs = SectionTemplate.objects.all()
    if section_type:
        qs = qs.by_type(section_type)
    if org_type_filter:
        eligible = TEMPLATE_ELIGIBILITY.get(org_type_filter, set())
        qs = qs.filter(org_type__in=eligible)
    return qs
```

### 5.3 Services

**File:** `apps/cms/services.py` — new class:

```python
class CMSTemplateActivationService:

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
        template = CMSTemplateSelector.get_section_template_by_id(template_id=template_id)

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

        # Audit + logging
        return activation

    @staticmethod
    @transaction.atomic
    def activate_block_template(...):
        """Same pattern for block templates."""

    @staticmethod
    @transaction.atomic
    def deactivate_section_template(*, actor_context, activation_id, request=None):
        """Deactivate — sets is_active=False (does NOT delete)."""
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_deactivate_cms_template",
        )
        activation = CMSTemplateActivationSelector.get_section_activation(
            activation_id=activation_id,
        )
        # Verify org ownership
        if (activation.org_type != actor_context.account_type
                or activation.org_id != actor_context.account_id):
            raise PermissionDenied("Cannot manage activations for another organization")

        activation.is_active = False
        activation.save(update_fields=["is_active", "updated_at"])

    @staticmethod
    @transaction.atomic
    def deactivate_block_template(...):
        """Same pattern."""

    @staticmethod
    @transaction.atomic
    def auto_provision_defaults(*, org_type: str, org_id: UUID, user):
        """
        Auto-activate all is_default=True templates for a new org.
        Called by CMS activation outcome handler.
        """
        eligible = TEMPLATE_ELIGIBILITY.get(org_type, set())

        for st in SectionTemplate.objects.filter(is_default=True, org_type__in=eligible):
            SectionTemplateActivation.objects.get_or_create(
                template=st, org_type=org_type, org_id=org_id,
                defaults={"activated_by": user, "is_active": True},
            )

        for bt in BlockTemplate.objects.filter(is_default=True, org_type__in=eligible):
            BlockTemplateActivation.objects.get_or_create(
                template=bt, org_type=org_type, org_id=org_id,
                defaults={"activated_by": user, "is_active": True},
            )
```

### 5.4 Activation Check in Placement Creation

**File:** `apps/cms/services.py` — modify existing `CMSTemplateService`

When creating a `PageSectionPlacement` or `SectionBlockPlacement` for a **business** context, add activation check:

```python
# In CMSTemplateService, before creating a placement:
def _check_template_activation(*, template, owner_type, owner_id):
    """
    Verify template is activated for this org.
    Platform context: skip check (platform can use any template).
    Business context: require active activation.
    """
    if owner_type == OwnerType.PLATFORM:
        return  # Platform uses templates directly

    if owner_type == OwnerType.BUSINESS:
        activated = CMSTemplateActivationSelector.is_template_activated(
            template_id=template.id,
            template_type="section" if isinstance(template, SectionTemplate) else "block",
            org_type=owner_type,
            org_id=owner_id,
        )
        if not activated:
            raise BusinessRuleViolation(
                message="Template not activated for this organization",
                rule="template_not_activated",
            )
```

**Impact:** This is a **new check** added to existing service methods. Platform flow is unaffected (early return). Business flow requires activation.

### 5.5 Policies

**File:** `apps/cms/policies.py` — addition:

```python
class CMSActivationPolicy:
    @staticmethod
    def can_deactivate_template(*, activation, org_type, org_id):
        """
        Check if template can be deactivated.
        Cannot deactivate if active placements reference this template.
        """
        # Check for active placements using this template in this org's sites
        if isinstance(activation.template, SectionTemplate):
            has_usage = PageSectionPlacement.objects.filter(
                template=activation.template,
                page__site__owner_type=org_type,
                page__site__owner_id=org_id,
                page__is_deleted=False,
            ).exists()
        else:
            has_usage = SectionBlockPlacement.objects.filter(
                template=activation.template,
                section_placement__page__site__owner_type=org_type,
                section_placement__page__site__owner_id=org_id,
                section_placement__page__is_deleted=False,
            ).exists()

        if has_usage:
            raise BusinessRuleViolation(
                message="Cannot deactivate template that is in use by active pages",
                rule="template_in_use",
            )
```

---

## 6. Phase 3: CMS Activation Transaction

### 6.1 Transaction Type Config

**File:** `apps/transaction/types.py` — add to `TRANSACTION_TYPES`:

```python
# --- CMS ---
"cms_activation_request": TransactionTypeConfig(
    id="cms_activation_request",
    name="CMS Activation Request",
    category="cms",
    conflict_group="cms_activation",
    mode=TransactionMode.REQUEST,
    initiator_types=[PartyType.MEMBERSHIP_ACTOR],
    target_types=[PartyType.ACCOUNT],
    context_type=ContextType.PLATFORM,
    approver_policy=ApproverPolicy.PLATFORM_AUTHORITY,
    approval_permission="can_approve_cms_activation",
    owner_only=True,  # Only business owner can request
    payload_schema={
        "business_id": {"type": "string", "format": "uuid", "required": True},
        "reason": {"type": "string", "max_length": 1000, "required": False},
    },
    expiration_days=30,
    resubmission_cooldown_days=14,
    outcome_handler="apps.cms.outcome_handlers.CMSActivationOutcomeHandler.handle_approved",
),
```

**Design Notes:**
- `context_type=PLATFORM` — request goes to platform for approval
- `initiator_types=[MEMBERSHIP_ACTOR]` — business member creates (must have business membership)
- `owner_only=True` — only business owner can initiate (follows business_verification_request pattern)
- `conflict_group="cms_activation"` — one active request per business
- `payload.business_id` — which business to enable CMS for
- `approval_permission="can_approve_cms_activation"` — platform member with this permission approves

### 6.2 Feature Gate Registration

**File:** `apps/transaction/services.py` — add to `_REQUEST_FEATURE_GATES`:

```python
_REQUEST_FEATURE_GATES: dict[str, list[str]] = {
    # ... existing entries ...
    "cms_activation_request": ["business.cms.activation_request"],
}
```

### 6.3 Outcome Handler

**File:** `apps/cms/outcome_handlers.py` (NEW FILE)

```python
"""
CMS Outcome Handlers
====================
Handle transaction outcomes for CMS-related transactions.
"""

import logging

from django.db import transaction as db_transaction

from apps.core.types import ActorContext

logger = logging.getLogger(__name__)


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

        business_id = transaction.payload.get("business_id")
        business = BusinessAccount.objects.get(id=business_id)

        # 1. Enable CMS
        business.cms_enabled = True
        business.save(update_fields=["cms_enabled", "updated_at"])

        # 2. Auto-provision default templates
        CMSTemplateActivationService.auto_provision_defaults(
            org_type=OwnerType.BUSINESS,
            org_id=business.id,
            user=business.created_by,  # Or transaction initiator
        )

        logger.info(
            "outcome.cms.activation_approved",
            extra={
                "business_id": str(business.id),
                "transaction_id": str(transaction.id),
            },
        )
```

### 6.4 Handler Registration

**File:** `apps/transaction/outcome_handlers.py` — add to `register_all_handlers()`:

```python
def register_all_handlers():
    # ... existing registrations ...

    # CMS handlers (conditional on CMS system being enabled)
    if feature_config.is_system_enabled("cms"):
        from apps.cms.outcome_handlers import CMSActivationOutcomeHandler
        r("cms_activation_request", CMSActivationOutcomeHandler.handle_approved)
```

---

## 7. Phase 4: Business-Scoped CMS API

### 7.1 URL Structure

**File:** `apps/cms/api/urls_business.py` (NEW FILE)

**IMPORTANT:** `BusinessContextMixin.get_business()` resolves the business from URL kwarg `business_slug`
(via `self.kwargs.get("business_slug")`). All URL patterns MUST use `<slug:business_slug>`.

```
# Template Catalog (browse available templates)
GET  /api/v1/cms/business/<business_slug>/catalog/sections/
GET  /api/v1/cms/business/<business_slug>/catalog/blocks/

# Template Library (manage activations)
GET  /api/v1/cms/business/<business_slug>/library/sections/
POST /api/v1/cms/business/<business_slug>/library/sections/                   → activate
DELETE /api/v1/cms/business/<business_slug>/library/sections/<uuid>/           → deactivate
GET  /api/v1/cms/business/<business_slug>/library/blocks/
POST /api/v1/cms/business/<business_slug>/library/blocks/                     → activate
DELETE /api/v1/cms/business/<business_slug>/library/blocks/<uuid>/             → deactivate

# Content Management (mirrors platform admin, scoped to business)
GET/POST /api/v1/cms/business/<business_slug>/sites/
GET/PATCH/DELETE /api/v1/cms/business/<business_slug>/sites/<slug:slug>/
GET/POST /api/v1/cms/business/<business_slug>/pages/
GET /api/v1/cms/business/<business_slug>/pages/<slug:slug>/
POST /api/v1/cms/business/<business_slug>/pages/<slug:slug>/publish/
POST /api/v1/cms/business/<business_slug>/pages/<slug:slug>/unpublish/
POST /api/v1/cms/business/<business_slug>/pages/<slug:slug>/export/
POST /api/v1/cms/business/<business_slug>/pages/<slug:slug>/import/
GET/PATCH /api/v1/cms/business/<business_slug>/block-placements/<uuid:uuid>/
GET /api/v1/cms/business/<business_slug>/block-placements/<uuid:uuid>/history/
POST /api/v1/cms/business/<business_slug>/block-placements/<uuid:uuid>/rollback/<int:version_number>/
GET/POST /api/v1/cms/business/<business_slug>/media/files/
GET/PATCH/DELETE /api/v1/cms/business/<business_slug>/media/files/<uuid:uuid>/
GET/POST /api/v1/cms/business/<business_slug>/api-keys/
DELETE /api/v1/cms/business/<business_slug>/api-keys/<uuid:uuid>/
```

### 7.2 URL Mounting

**File:** `backend_core/urls/cms.py` — add:

```python
# Existing
path("api/v1/cms/admin/", include("apps.cms.api.urls", namespace="cms")),
path("api/v1/cms/public/", include("apps.cms.api.urls_public", namespace="cms-public")),

# NEW — business-scoped
path("api/v1/cms/business/", include("apps.cms.api.urls_business", namespace="cms-business")),
```

No change to `urls/__init__.py` — all three are under the same `systems.cms` gate.

### 7.3 Views

**File:** `apps/cms/api/views.py` — new view classes:

All business views follow this pattern:

```python
from apps.rbac.views import BusinessContextMixin

_BusinessCmsGate = FeatureRequired("business.cms.enabled")


class BusinessCMSMixin(BusinessContextMixin):
    """
    Base mixin for all business CMS views.
    Checks: feature gate → business membership → cms_enabled flag.
    """
    permission_classes = [IsAuthenticated, _BusinessCmsGate]

    def get_actor_context(self):
        ctx = super().get_actor_context()
        # Additional check: is CMS enabled for THIS business?
        business = self.get_business()
        if not business.cms_enabled:
            raise FeatureDisabled(feature="business.cms")
        return ctx
```

**View classes to create** (each mirrors the platform admin counterpart but uses `BusinessCMSMixin`):

| View | Platform Counterpart | Notes |
|------|---------------------|-------|
| `BusinessCatalogSectionView` | — (new) | Browse available section templates |
| `BusinessCatalogBlockView` | — (new) | Browse available block templates |
| `BusinessLibrarySectionListCreateView` | — (new) | List/activate section templates |
| `BusinessLibrarySectionDetailView` | — (new) | Deactivate |
| `BusinessLibraryBlockListCreateView` | — (new) | List/activate block templates |
| `BusinessLibraryBlockDetailView` | — (new) | Deactivate |
| `BusinessSiteListCreateView` | `AdminSiteListCreateView` | Scoped to business |
| `BusinessSiteDetailView` | `AdminSiteDetailView` | Scoped to business |
| `BusinessPageListCreateView` | `AdminPageListCreateView` | + limit check |
| `BusinessPageDetailView` | `AdminPageDetailView` | Scoped |
| `BusinessPagePublishView` | `AdminPagePublishView` | Scoped |
| `BusinessPageUnpublishView` | `AdminPageUnpublishView` | Scoped |
| `BusinessPageExportView` | `AdminPageExportView` | Scoped |
| `BusinessPageImportView` | `AdminPageImportView` | Scoped |
| `BusinessBlockPlacementDetailView` | `AdminBlockPlacementDetailView` | + activation check on template |
| `BusinessBlockPlacementHistoryView` | `AdminBlockPlacementHistoryView` | Scoped |
| `BusinessBlockPlacementRollbackView` | `AdminBlockPlacementRollbackView` | Scoped |
| `BusinessMediaFileListCreateView` | `AdminMediaFileListCreateView` | + limit check |
| `BusinessMediaFileDetailView` | `AdminMediaFileDetailView` | Scoped |
| `BusinessApiKeyListCreateView` | `AdminApiKeyListCreateView` | + limit check |
| `BusinessApiKeyDetailView` | `AdminApiKeyDetailView` | Scoped |

**Key difference from platform views:** Business views call `self.get_business()` for scoping, pass `owner_type="business"` and `owner_id=business.id` to services/selectors.

### 7.4 Serializers

**File:** `apps/cms/api/serializers.py` — additions:

```python
# Template catalog output (read-only, for browsing)
class TemplateCatalogSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SectionTemplate
        fields = ["id", "name", "display_name", "slug", "section_type",
                  "description", "ui_config", "org_type"]

class TemplateCatalogBlockSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockTemplate
        fields = ["id", "name", "display_name", "slug", "block_type",
                  "description", "schema", "schema_version", "default_content",
                  "ui_config", "org_type"]

# Template activation input
class TemplateActivationSerializer(serializers.Serializer):
    template_id = serializers.UUIDField()

# Template activation output
class SectionActivationOutputSerializer(serializers.ModelSerializer):
    template = TemplateCatalogSectionSerializer(read_only=True)

    class Meta:
        model = SectionTemplateActivation
        fields = ["id", "template", "is_active", "activated_at", "created_at"]

class BlockActivationOutputSerializer(serializers.ModelSerializer):
    template = TemplateCatalogBlockSerializer(read_only=True)

    class Meta:
        model = BlockTemplateActivation
        fields = ["id", "template", "is_active", "activated_at", "created_at"]
```

---

## 8. Phase 5: Limit Enforcement

### 8.1 Enforcement Points

| Limit Path | Enforced In | When |
|------------|-------------|------|
| `business.cms.max_sites` | `CMSSiteService.create_site()` | Before creating site for business owner |
| `business.cms.max_pages_per_site` | `CMSPageService.create_page()` | Before creating page |
| `business.cms.max_api_keys_per_site` | `CMSApiKeyService.create_api_key()` | Before creating API key |
| `business.cms.max_active_block_templates` | `CMSTemplateActivationService.activate_block_template()` | Before activation |
| `business.cms.max_active_section_templates` | `CMSTemplateActivationService.activate_section_template()` | Before activation |
| `business.cms.max_media_files` | `CMSMediaService.upload_file()` | Before upload |
| `business.cms.max_media_file_size_mb` | `CMSMediaService.upload_file()` | Before upload |
| `business.cms.api_key_rate_limit` | `CMSApiKeyService.create_api_key()` | Default rate_limit for business keys |

### 8.2 Service Modifications

Each service method that creates a resource needs a limit check **when the owner is a business**:

```python
# Pattern: in CMSSiteService.create_site()
if owner_type == OwnerType.BUSINESS:
    current = Site.objects.filter(
        owner_type=owner_type, owner_id=owner_id
    ).count()
    feature_config.check_limit(
        "business.cms.max_sites",
        current,
        rule="cms_max_sites_exceeded",
        resource="CMS Site",
    )
```

Platform context: no per-org limits (platform uses cross-scope `cms.*` values).

### 8.3 Media File Size Limit

```python
# In CMSMediaService.upload_file(), for business context:
if owner_type == OwnerType.BUSINESS:
    max_mb = feature_config.get_value("business.cms.max_media_file_size_mb", 10)
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(f"File size exceeds {max_mb}MB limit")
```

---

## 9. Phase 6: Platform Management Endpoints

### 9.1 New Platform Admin Endpoints

Add to `apps/cms/api/urls.py` (platform admin namespace):

```
# Business CMS management (platform admin)
GET  /api/v1/cms/admin/businesses/                    → list businesses with CMS status
PATCH /api/v1/cms/admin/businesses/<uuid>/             → toggle cms_enabled directly
GET  /api/v1/cms/admin/businesses/<uuid>/activations/  → view business template activations
```

### 9.2 Views

```python
class AdminBusinessCMSListView(PlatformContextMixin, APIView):
    """List businesses with their CMS status."""
    permission_classes = [IsAuthenticated, _CmsGate]

    def get(self, request):
        actor_context = self.get_actor_context()
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_manage_business_cms",
        )
        businesses = BusinessAccount.objects.active().values(
            "id", "slug", "legal_name", "cms_enabled",
        )
        # Paginate and return

class AdminBusinessCMSToggleView(PlatformContextMixin, APIView):
    """Enable/disable CMS for a specific business."""
    permission_classes = [IsAuthenticated, _CmsGate]

    def patch(self, request, uuid):
        actor_context = self.get_actor_context()
        MembershipPolicy.authorize_action(
            actor_context=actor_context,
            required_permission="can_manage_business_cms",
        )
        business = BusinessAccount.objects.get(id=uuid)
        cms_enabled = request.data.get("cms_enabled")

        business.cms_enabled = cms_enabled
        business.save(update_fields=["cms_enabled", "updated_at"])

        if cms_enabled:
            # Auto-provision default templates (same as transaction handler)
            CMSTemplateActivationService.auto_provision_defaults(
                org_type=OwnerType.BUSINESS,
                org_id=business.id,
                user=request.user,
            )

        return Response({"id": str(business.id), "cms_enabled": business.cms_enabled})
```

### 9.3 Serializers

```python
class BusinessCMSStatusSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    legal_name = serializers.CharField()
    cms_enabled = serializers.BooleanField()

class BusinessCMSToggleSerializer(serializers.Serializer):
    cms_enabled = serializers.BooleanField(required=True)
```

---

## 10. Observability & Notifications

### 10.1 New Audit Actions

**File:** `apps/core/observability/audit/models.py` — add to `AuditLog.Action`:

```python
# CMS — Template Activation (add after CMS - Templates section)
CMS_TEMPLATE_ACTIVATED = "cms.template.activated"
CMS_TEMPLATE_DEACTIVATED = "cms.template.deactivated"

# CMS — Business Management
CMS_BUSINESS_ENABLED = "cms.business.enabled"
CMS_BUSINESS_DISABLED = "cms.business.disabled"
CMS_DEFAULTS_PROVISIONED = "cms.defaults.provisioned"
```

### 10.2 Structlog + AuditService in Every New Service Method

Every new service method MUST follow the existing CMS pattern:

```python
# Pattern: every write operation
logger.info("cms.template.activated", template_id=str(template.id), org_id=str(org_id))
AuditService.log(
    action=AuditLog.Action.CMS_TEMPLATE_ACTIVATED,
    actor=actor,
    resource=template,
    request=request,
    details={"org_type": org_type, "org_id": str(org_id)},
)
```

Methods requiring audit:
- `CMSTemplateActivationService.activate_section_template()` → `CMS_TEMPLATE_ACTIVATED`
- `CMSTemplateActivationService.activate_block_template()` → `CMS_TEMPLATE_ACTIVATED`
- `CMSTemplateActivationService.deactivate_section_template()` → `CMS_TEMPLATE_DEACTIVATED`
- `CMSTemplateActivationService.deactivate_block_template()` → `CMS_TEMPLATE_DEACTIVATED`
- `CMSTemplateActivationService.auto_provision_defaults()` → `CMS_DEFAULTS_PROVISIONED`
- `AdminBusinessCMSToggleView.patch()` → `CMS_BUSINESS_ENABLED` or `CMS_BUSINESS_DISABLED`
- `CMSActivationOutcomeHandler.handle_approved()` → `CMS_BUSINESS_ENABLED` + `CMS_DEFAULTS_PROVISIONED`

### 10.3 Notification Integration

**Transaction flow (auto-handled):**
The transaction system auto-sends generic notifications on state changes:
- Request created → `transaction_pending_approval` to platform approvers
- Approved → `transaction_accepted` to initiator
- Denied → `transaction_denied` to initiator

These generic notifications are sufficient for the transaction-based activation flow.

**Direct toggle (P2 — not blocking):**
When platform admin directly enables/disables CMS via `AdminBusinessCMSToggleView`, no transaction exists, so no auto-notification. Consider adding a `cms_enabled_for_business` notification type in a follow-up phase to notify the business owner.

---

## 11. Side Effects & Dependency Matrix

### 11.1 Files Modified (Existing)

| File | Change | Risk |
|------|--------|------|
| `apps/cms/models.py` | Add `org_type`, `is_default` to templates + 2 new activation models | LOW — additive fields with defaults, no existing field changes |
| `apps/cms/managers.py` | Add 2 activation manager classes | NONE — purely additive |
| `apps/cms/constants.py` | Add `TemplateOrgType` enum, `TEMPLATE_ELIGIBILITY` | NONE — new constants |
| `apps/cms/services.py` | Add `CMSTemplateActivationService`, add activation check in placement creation, add limit checks for business context | MEDIUM — placement creation gets a new check (platform path has early return, no impact) |
| `apps/cms/selectors.py` | Add `CMSTemplateActivationSelector`, modify `CMSTemplateSelector.list_*` to accept `org_type_filter` | LOW — existing callers don't pass new param (default=None, no filter) |
| `apps/cms/policies.py` | Add `CMSActivationPolicy` | NONE — new class |
| `apps/cms/api/views.py` | Add ~21 business views + 3 platform management views | LOW — new views in same file, existing views unchanged |
| `apps/cms/api/serializers.py` | Add catalog, activation, management serializers | NONE — purely additive |
| `apps/cms/api/urls.py` | Add 3 platform management URL patterns | LOW — additive |
| `apps/cms/admin.py` | Add `org_type`, `is_default` to template admins, register activation models | LOW — display changes only |
| `apps/cms/apps.py` | No change needed (outcome handler registered in transaction app) | NONE |
| `apps/organization/business/models.py` | Add `cms_enabled` field | LOW — new boolean with default=False |
| `apps/transaction/types.py` | Add `cms_activation_request` to TRANSACTION_TYPES | LOW — additive entry |
| `apps/transaction/outcome_handlers.py` | Add handler registration in `register_all_handlers()` | LOW — conditional import |
| `apps/transaction/services.py` | Add entry to `_REQUEST_FEATURE_GATES` | LOW — dict addition |
| `backend/deployment_config.json` | Upgrade `business.cms` from boolean to object | MEDIUM — see 10.2 |
| `backend/conftest.py` | Update `_FULL_FEATURE_CONFIG` to match | MEDIUM — see 10.2 |
| `backend_core/urls/cms.py` | Add business URL include | LOW — additive path |
| `apps/core/observability/audit/models.py` | Add 5 new CMS audit actions | NONE — additive enum values |
| `apps/core/tests/test_feature_config.py` | Update 14 `business.cms` boolean refs to dict | MEDIUM — must update to match new config shape |

### 11.2 Breaking Change: `business.cms` Config Upgrade

**Current:** `"business": { "cms": true }`
**New:** `"business": { "cms": { "enabled": true, ... } }`

**Impact analysis:**
- `is_feature_enabled("business.cms")` — returns `True` for non-empty dict (safe)
- `FeatureRequired("business.cms")` — not currently used anywhere (CMS views use `"platform.cms"`)
- Business CMS views will use `FeatureRequired("business.cms.enabled")` (new)
- `_FULL_FEATURE_CONFIG` in `conftest.py` — must update from `True` to dict

**Existing test impact:** CMS feature gate tests in `test_fg_module_gates.py` test `"platform.cms"`, not `"business.cms"`. The config upgrade is safe for existing tests.

**Action required:** 14 references in `apps/core/tests/test_feature_config.py` set `business.cms` as a boolean in test configs. These tests still PASS (non-empty dict is truthy), but tests that construct `{"business": {"cms": True}}` and then check `is_feature_enabled("business.cms.enabled")` would fail because you can't traverse into a boolean.

**Fix:** Update all 14 test references in `test_feature_config.py`:
```python
# Before
feature_config_override({"business": {"cms": True}})
# After
feature_config_override({"business": {"cms": {"enabled": True}}})
```

Tests that assert `is_feature_enabled("business.cms") is True` still pass (dict is truthy). Add new test for `"business.cms.enabled"` path.

### 11.3 Files Created (New)

| File | Purpose |
|------|---------|
| `apps/cms/outcome_handlers.py` | CMS activation outcome handler |
| `apps/cms/api/urls_business.py` | Business CMS URL patterns |
| `apps/cms/migrations/0003_template_org_type_fields.py` | Template org_type + is_default |
| `apps/cms/migrations/0004_template_activation_models.py` | Activation models |
| `apps/organization/migrations/000X_add_business_cms_enabled.py` | Business cms_enabled |
| `apps/rbac/migrations/0013_seed_cms_activation_permissions.py` | New permissions |
| `apps/cms/tests/test_template_activation.py` | Activation service/selector tests |
| `apps/cms/tests/test_business_views.py` | Business API tests |
| `apps/cms/tests/test_outcome_handlers.py` | Transaction outcome tests |
| `apps/cms/tests/test_limits.py` | VG limit enforcement tests |

### 11.4 Systems NOT Affected

| System | Why Unaffected |
|--------|---------------|
| Public API | API key → site → content path unchanged. Business sites served identically to platform sites |
| Platform admin views | All existing endpoints unchanged. New management endpoints are additive |
| Schema validation | Validates against canonical template schema — no change |
| Content versioning | Operates on placements, independent of who owns the site |
| Media tombstoning | Works on MediaFile level, independent of owner_type |
| Chat, Network, Forms | Separate systems, no CMS dependency |
| Explore | May eventually index business CMS content, but not in this phase |

---

## 12. Test Plan

### 12.1 Unit Tests — Template Activation

**File:** `apps/cms/tests/test_template_activation.py`

| Test | What It Verifies |
|------|-----------------|
| `test_activate_section_template` | Creates activation record, links template to org |
| `test_activate_block_template` | Same for block templates |
| `test_activate_ineligible_template_rejected` | Business can't activate platform-only template |
| `test_activate_system_template_rejected` | Nobody can activate system templates |
| `test_duplicate_activation_reactivates` | Second activate on same template sets is_active=True |
| `test_deactivate_template` | Sets is_active=False |
| `test_deactivate_template_in_use_rejected` | Can't deactivate if active placements exist |
| `test_max_active_section_templates_limit` | BusinessRuleViolation when at limit |
| `test_max_active_block_templates_limit` | Same for blocks |
| `test_auto_provision_defaults` | Creates activations for all is_default=True eligible templates |
| `test_auto_provision_skips_ineligible` | System/platform-only templates not provisioned for business |
| `test_list_available_templates` | Returns eligible, not-yet-activated templates |
| `test_list_activated_templates` | Returns active activations for org |
| `test_is_template_activated` | Boolean check |

### 12.2 Unit Tests — Business CMS Views

**File:** `apps/cms/tests/test_business_views.py`

| Test | What It Verifies |
|------|-----------------|
| `test_business_cms_requires_feature_gate` | 403 when business.cms.enabled=False |
| `test_business_cms_requires_cms_enabled` | 403 when business.cms_enabled=False |
| `test_business_site_list_scoped` | Only returns business's own sites |
| `test_business_create_site` | Creates site with owner_type=business |
| `test_business_create_site_limit` | BusinessRuleViolation at max_sites |
| `test_business_create_page` | Creates page in business site |
| `test_business_create_page_limit` | BusinessRuleViolation at max_pages_per_site |
| `test_business_publish_page` | Publishes business page |
| `test_business_upload_media_limit` | BusinessRuleViolation at max_media_files |
| `test_business_upload_media_size_limit` | Rejected when file too large |
| `test_business_create_api_key` | Creates key for business site |
| `test_business_create_api_key_limit` | BusinessRuleViolation at max_api_keys_per_site |
| `test_business_catalog_lists_eligible` | Shows only business+all org_type templates |
| `test_business_library_activate` | Activates template, appears in library |
| `test_business_library_deactivate` | Deactivates, disappears from library |
| `test_placement_requires_activation` | Can't create placement with non-activated template |
| `test_platform_admin_toggle_business_cms` | Platform admin enables CMS for business |
| `test_platform_admin_list_business_cms_status` | Lists all businesses with CMS status |

### 12.3 Unit Tests — Outcome Handler

**File:** `apps/cms/tests/test_outcome_handlers.py`

| Test | What It Verifies |
|------|-----------------|
| `test_activation_approved_enables_cms` | Sets business.cms_enabled=True |
| `test_activation_approved_provisions_defaults` | Creates activations for default templates |
| `test_activation_approved_only_eligible_templates` | Skips system/platform-only templates |

### 12.4 Unit Tests — Limits

**File:** `apps/cms/tests/test_limits.py`

| Test | What It Verifies |
|------|-----------------|
| `test_site_limit_enforced` | Can't create more sites than max_sites |
| `test_site_limit_zero_unlimited` | 0 = no limit |
| `test_page_limit_enforced` | Per-site page cap |
| `test_api_key_limit_enforced` | Per-site API key cap |
| `test_media_file_limit_enforced` | Per-business media cap |
| `test_media_file_size_limit_enforced` | Per-file size cap |
| `test_template_activation_limit_enforced` | Per-business template cap |
| `test_platform_no_business_limits` | Platform context skips all business.cms limits |

### 12.5 Integration Tests

Add to `tests/api_integration/` — CMS business flow (requires live Docker):

| Test | Flow |
|------|------|
| `test_full_business_cms_activation_flow` | Create business → request CMS → approve → verify enabled + defaults |
| `test_business_cms_content_flow` | Enable CMS → activate template → create site → create page → edit content → publish → public API |

### 12.6 Test Fixtures

**File:** `apps/cms/tests/conftest.py` — additions:

```python
@pytest.fixture
def business_with_cms(business, user):
    """Business with CMS enabled and RBAC initialized."""
    business.cms_enabled = True
    business.save(update_fields=["cms_enabled"])
    # Initialize RBAC, create owner membership
    return business

@pytest.fixture
def business_actor_context(business_with_cms, user):
    """ActorContext for business owner with CMS permissions."""
    # Build from membership

@pytest.fixture
def activated_block_template(block_template, business_with_cms):
    """Block template activated for business."""
    return BlockTemplateActivation.objects.create(
        template=block_template,
        org_type=OwnerType.BUSINESS,
        org_id=business_with_cms.id,
        is_active=True,
    )
```

**File:** `apps/cms/tests/factories.py` — additions:

```python
class SectionTemplateActivationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SectionTemplateActivation
    template = factory.SubFactory(SectionTemplateFactory)
    org_type = OwnerType.BUSINESS
    org_id = factory.LazyFunction(uuid.uuid4)
    is_active = True

class BlockTemplateActivationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BlockTemplateActivation
    template = factory.SubFactory(BlockTemplateFactory)
    org_type = OwnerType.BUSINESS
    org_id = factory.LazyFunction(uuid.uuid4)
    is_active = True
```

---

## 13. Implementation Order

### Step 1: Foundation (no dependencies)
1. `constants.py` — TemplateOrgType enum, TEMPLATE_ELIGIBILITY
2. Migration 0003 — template org_type + is_default fields
3. Migration for BusinessAccount.cms_enabled
4. Migration for RBAC permissions
5. `admin.py` — template admin updates

### Step 2: Activation Models (depends on Step 1)
6. `models.py` — SectionTemplateActivation, BlockTemplateActivation
7. `managers.py` — activation managers
8. Migration 0004 — activation models

### Step 3: Activation Logic (depends on Step 2)
9. `selectors.py` — CMSTemplateActivationSelector + modify CMSTemplateSelector
10. `services.py` — CMSTemplateActivationService
11. `policies.py` — CMSActivationPolicy
12. `services.py` — add activation check to placement creation
13. `services.py` — add limit checks for business context

### Step 4: Transaction Integration (depends on Step 3)
14. `outcome_handlers.py` (new) — CMSActivationOutcomeHandler
15. `transaction/types.py` — add cms_activation_request
16. `transaction/outcome_handlers.py` — register CMS handler
17. `transaction/services.py` — add feature gate

### Step 5: Config + Observability (parallel with Step 3-4)
18. `deployment_config.json` — upgrade business.cms to object
19. `conftest.py` — update _FULL_FEATURE_CONFIG
20. `core/observability/audit/models.py` — add 5 new audit actions
21. `core/tests/test_feature_config.py` — update 14 `business.cms` boolean refs to dict

### Step 6: Business API (depends on Step 3)
22. `serializers.py` — catalog + activation serializers
23. `views.py` — BusinessCMSMixin + all business views
24. `urls_business.py` (new) — business URL patterns (use `<slug:business_slug>`)
25. `urls/cms.py` — mount business URLs

### Step 7: Platform Management (depends on Step 3)
26. `views.py` — platform management views
27. `serializers.py` — management serializers
28. `urls.py` — management URL patterns

### Step 8: Tests (depends on all above)
29. `tests/factories.py` — activation factories
30. `tests/conftest.py` — business CMS fixtures
31. `tests/test_template_activation.py`
32. `tests/test_business_views.py`
33. `tests/test_outcome_handlers.py`
34. `tests/test_limits.py`
35. Update `tests/test_views.py` — ensure existing platform tests still pass
36. Run full test suite — verify 14 updated `test_feature_config.py` refs pass

### Step 9: Documentation
37. Update `docs/implementations/backend/cms-system.md`
38. Update `deployment_config.json` reference docs
39. Update CLAUDE.md CMS section if needed
40. Progress entry

---

## 14. Risks & Mitigations

### R-1: `business.cms` config upgrade breaks existing tests
**Risk:** MEDIUM
**Mitigation:** Verify with `grep -r "business.cms" --include="*.py" backend/` before migration. The `is_feature_enabled()` method returns truthy for non-empty dicts. Existing feature gate tests check `platform.cms` not `business.cms`.

### R-2: Activation check on placement creation affects platform flow
**Risk:** LOW
**Mitigation:** Activation check has early return for `owner_type == PLATFORM`. Platform tests run unchanged.

### R-3: Template PROTECT on_delete blocks template deletion
**Risk:** LOW — working as designed
**Mitigation:** Activations use `on_delete=PROTECT`, preventing deletion of templates with active activations. Superuser must deactivate across all orgs before deleting a template. Future: add `is_deprecated` field to templates.

### R-4: Auto-provision creates many activations on bulk CMS enable
**Risk:** LOW
**Mitigation:** `get_or_create()` in loop is safe but slow for large template catalogs. If catalog exceeds ~100 templates, optimize with `bulk_create(ignore_conflicts=True)`. Current scale is small.

### R-5: test_feature_config.py tests break after config restructure
**Risk:** MEDIUM
**Mitigation:** 14 tests in `test_feature_config.py` use `{"business": {"cms": True}}`. After upgrading to `{"business": {"cms": {"enabled": True}}}`, the `is_feature_enabled("business.cms")` call returns `True` (dict is truthy), so assertion-level tests still pass. BUT tests that construct partial configs then check `"business.cms.enabled"` would fail. Fix: update all 14 references to use new dict structure. Run full test suite after config change.

### R-6: Race condition on activation count for limit check
**Risk:** LOW
**Mitigation:** `check_limit()` + `get_or_create()` within `@transaction.atomic` — standard pattern used throughout the codebase. The unique constraint prevents double-activation.

---

## 15. Estimated Scope

| Category | Count |
|----------|-------|
| New models | 2 (SectionTemplateActivation, BlockTemplateActivation) |
| Model field additions | 5 (org_type + is_default on 2 templates, cms_enabled on BusinessAccount) |
| New migrations | 4 |
| New RBAC permissions | 4 |
| New transaction type | 1 (cms_activation_request) |
| New API endpoints | ~27 (21 business + 3 platform management + 3 catalog/library) |
| New serializers | ~8 |
| New service methods | ~10 |
| Modified service methods | ~6 (add limit/activation checks) |
| New test files | 4 |
| Expected new tests | ~60-80 |
| New files total | ~10 |
| New audit actions | 5 |
| Modified test files | 1 (test_feature_config.py — 14 refs updated) |
| Modified files total | ~20 |
