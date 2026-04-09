/**
 * CMS Type Definitions
 * =====================
 * Domain types matching backend CMS serializers exactly.
 *
 * Backend: apps.cms.api.serializers
 * Backend: apps.cms.constants
 * Backend: apps.cms.policies (CmsPermissions)
 */

import type { WithPermissions } from "@/types/api";

// =============================================================================
// ENUMS (union literals matching backend TextChoices)
// =============================================================================

export type PageStatus = "draft" | "published" | "archived";
export type BlockPlacementStatus = "draft" | "published";
export type ContentVersionAction = "draft_save" | "publish" | "rollback" | "import";
export type ContentLayer = "draft" | "published";
export type TemplateOrgType = "system" | "platform" | "business" | "all";
export type OwnerType = "platform" | "business";

// =============================================================================
// PERMISSIONS (Tier 1.5 — from CMSPolicy.get_viewer_permissions)
// =============================================================================

export type CmsPermissions = {
  can_view_content: boolean;
  can_edit_content: boolean;
  can_publish_content: boolean;
  can_create_site: boolean;
  can_edit_site: boolean;
  can_delete_site: boolean;
  can_create_page: boolean;
  can_edit_page: boolean;
  can_delete_page: boolean;
  can_upload_media: boolean;
  can_edit_media: boolean;
  can_delete_media: boolean;
  can_create_api_key: boolean;
  can_activate_template: boolean;
};

// =============================================================================
// DOMAIN TYPES — Output serializers
// =============================================================================

/** SiteOutputSerializer */
export type CmsSite = {
  id: string;
  owner_type: OwnerType;
  owner_id: string;
  name: string;
  slug: string;
  domain: string;
  description: string;
  default_locale: string;
  metadata: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

/** PageOutputSerializer */
export type CmsPage = {
  id: string;
  site: string;
  site_slug: string;
  title: string;
  slug: string;
  description: string;
  path: string;
  page_type: string;
  metadata: Record<string, unknown> | null;
  status: PageStatus;
  published_at: string | null;
  order: number;
  is_required: boolean;
  is_visible: boolean;
  created_at: string;
  updated_at: string;
};

/** SectionTemplateOutputSerializer */
export type CmsSectionTemplate = {
  id: string;
  name: string;
  display_name: string;
  slug: string;
  description: string;
  section_type: string;
  org_type?: TemplateOrgType;
  is_default?: boolean;
  metadata: Record<string, unknown> | null;
  ui_config: Record<string, unknown> | null;
  created_at: string;
};

/** BlockTemplateOutputSerializer */
export type CmsBlockTemplate = {
  id: string;
  name: string;
  display_name: string;
  slug: string;
  description: string;
  block_type: string;
  org_type?: TemplateOrgType;
  is_default?: boolean;
  schema: CmsBlockSchema;
  schema_version: number;
  default_content: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  ui_config: Record<string, unknown> | null;
  created_at: string;
};

/** Block template schema structure */
export type CmsBlockSchema = {
  fields: CmsSchemaField[];
};

/** Individual field in a block template schema */
export type CmsSchemaField = {
  key: string;
  type: CmsFieldType;
  label?: string;
  required?: boolean;
  validation?: Record<string, unknown>;
  choices?: string[];
  allowed_tags?: string[];
  item_schema?: CmsSchemaField[];
  max_length?: number;
  min_length?: number;
  pattern?: string;
  min?: number;
  max?: number;
  min_selected?: number;
  max_selected?: number;
  min_items?: number;
  max_items?: number;
};

/** All 18 CMS field types */
export type CmsFieldType =
  | "text"
  | "textarea"
  | "richtext"
  | "number"
  | "boolean"
  | "url"
  | "email"
  | "date"
  | "datetime"
  | "select"
  | "multiselect"
  | "media"
  | "list"
  | "repeater"
  | "relation"
  | "json"
  | "color"
  | "icon";

/** SectionPlacementOutputSerializer (nested in PageDetail) */
export type CmsSectionPlacement = {
  id: string;
  page: string;
  template: CmsSectionTemplate;
  label: string;
  order: number;
  is_required: boolean;
  is_visible: boolean;
  config_overrides: Record<string, unknown> | null;
  created_at: string;
  block_placements: CmsBlockPlacement[];
};

/** BlockPlacementOutputSerializer */
export type CmsBlockPlacement = {
  id: string;
  section_placement: string;
  template: CmsBlockTemplate;
  label: string;
  order: number;
  is_required: boolean;
  is_visible: boolean;
  config_overrides: Record<string, unknown> | null;
  schema_version_validated: number;
  draft_content: Record<string, unknown> | null;
  published_content: Record<string, unknown> | null;
  status: BlockPlacementStatus;
  created_at: string;
  updated_at: string;
};

/** PageDetailOutputSerializer — page with full tree */
export type CmsPageDetail = CmsPage & {
  section_placements: CmsSectionPlacement[];
};

/** ContentVersionOutputSerializer */
export type CmsContentVersion = {
  id: string;
  block_placement: string;
  content_snapshot: Record<string, unknown>;
  version_number: number;
  action: ContentVersionAction;
  created_by: string;
  created_by_username: string;
  created_at: string;
  notes: string;
};

/** MediaFileOutputSerializer */
export type CmsMediaFile = {
  id: string;
  owner_type: OwnerType;
  owner_id: string;
  folder: string | null;
  storage_key: string;
  original_filename: string;
  mime_type: string;
  file_size: number;
  width: number | null;
  height: number | null;
  alt_text: string;
  title: string;
  metadata: Record<string, unknown> | null;
  is_tombstoned: boolean;
  usage_count: number;
  created_at: string;
  updated_at: string;
};

/** ApiKeyOutputSerializer */
export type CmsApiKey = {
  id: string;
  site: string;
  name: string;
  key_prefix: string;
  allowed_origins: string[];
  is_active: boolean;
  expires_at: string | null;
  last_used_at: string | null;
  rate_limit: number;
  created_at: string;
};

/** ApiKeyCreatedOutputSerializer — one-time key return */
export type CmsApiKeyCreated = {
  id: string;
  site: string;
  name: string;
  key_prefix: string;
  allowed_origins: string[];
  is_active: boolean;
  expires_at: string | null;
  rate_limit: number;
  created_at: string;
  key: string;
};

/** TemplateCatalogSectionSerializer */
export type CmsTemplateCatalogSection = {
  id: string;
  name: string;
  display_name: string;
  slug: string;
  section_type: string;
  description: string;
  ui_config: Record<string, unknown> | null;
  org_type: TemplateOrgType;
  is_default: boolean;
};

/** TemplateCatalogBlockSerializer */
export type CmsTemplateCatalogBlock = {
  id: string;
  name: string;
  display_name: string;
  slug: string;
  block_type: string;
  description: string;
  schema: CmsBlockSchema;
  schema_version: number;
  default_content: Record<string, unknown> | null;
  ui_config: Record<string, unknown> | null;
  org_type: TemplateOrgType;
  is_default: boolean;
};

/** SectionActivationOutputSerializer */
export type CmsSectionActivation = {
  id: string;
  template: CmsTemplateCatalogSection;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

/** BlockActivationOutputSerializer */
export type CmsBlockActivation = {
  id: string;
  template: CmsTemplateCatalogBlock;
  is_active: boolean;
  created_at: string;
  updated_at: string;
};

/** PageExportOutputSerializer */
export type CmsPageExport = {
  export_version: string;
  exported_at: string;
  exported_by: string;
  source_site: string;
  source_owner_type: OwnerType;
  source_owner_id: string;
  page: Record<string, unknown>;
};

/** BusinessCMSStatusSerializer */
export type BusinessCmsStatus = {
  id: string;
  slug: string;
  legal_name: string;
  cms_enabled: boolean;
};

/** Publish error item (from 400 validation_error on publish) */
export type CmsPublishError = {
  section_placement_id: string;
  block_placement_id: string;
  block_template: string;
  field_key: string;
  error_type: string;
  message: string;
};

// =============================================================================
// COMPOSED PERMISSION-AWARE TYPES
// =============================================================================

export type CmsSiteWithPerms = CmsSite & WithPermissions<CmsPermissions>;
export type CmsPageDetailWithPerms = CmsPageDetail & WithPermissions<CmsPermissions>;
export type CmsBlockPlacementWithPerms = CmsBlockPlacement &
  WithPermissions<CmsPermissions>;
export type CmsMediaFileWithPerms = CmsMediaFile & WithPermissions<CmsPermissions>;

// =============================================================================
// INPUT TYPES — matching backend input serializers
// =============================================================================

export type CreateSiteInput = {
  name: string;
  slug: string;
  domain?: string;
  description?: string;
  metadata?: Record<string, unknown>;
};

export type UpdateSiteInput = {
  name?: string;
  domain?: string;
  description?: string;
  metadata?: Record<string, unknown>;
  is_active?: boolean;
};

export type CreatePageInput = {
  site_id: string;
  title: string;
  slug: string;
  path: string;
  page_type: string;
  order: number;
  description?: string;
  metadata?: Record<string, unknown>;
  is_required?: boolean;
};

export type UpdatePageInput = {
  title?: string;
  description?: string;
  path?: string;
  metadata?: Record<string, unknown>;
  is_visible?: boolean;
};

export type UpdateDraftContentInput = {
  draft_content: Record<string, unknown>;
};

export type ImportPageInput = {
  export_version: string;
  page: Record<string, unknown>;
};

export type CreateApiKeyInput = {
  site_id: string;
  name: string;
  allowed_origins?: string[];
  rate_limit?: number;
  expires_at?: string;
};

export type ActivateTemplateInput = {
  template_id: string;
};

export type UpdateMediaInput = {
  alt_text?: string;
  title?: string;
  folder_id?: string;
};

export type ToggleBusinessCmsInput = {
  cms_enabled: boolean;
};

// =============================================================================
// API CONTEXT
// =============================================================================

export type CmsApiContext =
  | { type: "platform" }
  | { type: "business"; businessSlug: string };

// =============================================================================
// PAGINATED RESPONSE (DRF standard)
// =============================================================================

export type PaginatedCmsResponse<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
