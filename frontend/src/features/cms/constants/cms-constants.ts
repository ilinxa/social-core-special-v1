/**
 * CMS Constants & Display Config
 * ================================
 * Business rules, display configs, and enum label mappings.
 *
 * Backend: apps.cms.constants
 */

import type {
  BlockPlacementStatus,
  CmsFieldType,
  ContentVersionAction,
  PageStatus,
  TemplateOrgType,
} from "@/features/cms/types";

// =============================================================================
// STATUS DISPLAY CONFIG
// =============================================================================

type StatusConfig = {
  label: string;
  className: string;
};

export const PAGE_STATUS_CONFIG: Record<PageStatus, StatusConfig> = {
  draft: { label: "Draft", className: "bg-yellow-100 text-yellow-800" },
  published: { label: "Published", className: "bg-green-100 text-green-800" },
  archived: { label: "Archived", className: "bg-gray-100 text-gray-600" },
};

export const BLOCK_STATUS_CONFIG: Record<BlockPlacementStatus, StatusConfig> = {
  draft: { label: "Draft", className: "bg-yellow-100 text-yellow-800" },
  published: { label: "Published", className: "bg-green-100 text-green-800" },
};

// =============================================================================
// VERSION ACTION LABELS
// =============================================================================

export const VERSION_ACTION_CONFIG: Record<ContentVersionAction, string> = {
  draft_save: "Auto-saved",
  publish: "Published",
  rollback: "Rolled back",
  import: "Imported",
};

// =============================================================================
// TEMPLATE ORG TYPE LABELS
// =============================================================================

export const TEMPLATE_ORG_TYPE_LABELS: Record<TemplateOrgType, string> = {
  system: "System",
  platform: "Platform",
  business: "Business",
  all: "All Organizations",
};

// =============================================================================
// CMS FIELD TYPE CONFIG
// =============================================================================

type FieldTypeConfig = {
  label: string;
  category: "text" | "numeric" | "boolean" | "temporal" | "selection" | "media" | "complex";
};

export const CMS_FIELD_TYPE_CONFIG: Record<CmsFieldType, FieldTypeConfig> = {
  text: { label: "Text", category: "text" },
  textarea: { label: "Text Area", category: "text" },
  richtext: { label: "Rich Text", category: "text" },
  number: { label: "Number", category: "numeric" },
  boolean: { label: "Toggle", category: "boolean" },
  url: { label: "URL", category: "text" },
  email: { label: "Email", category: "text" },
  date: { label: "Date", category: "temporal" },
  datetime: { label: "Date & Time", category: "temporal" },
  select: { label: "Dropdown", category: "selection" },
  multiselect: { label: "Multi Select", category: "selection" },
  media: { label: "Media", category: "media" },
  list: { label: "List", category: "complex" },
  repeater: { label: "Repeater", category: "complex" },
  relation: { label: "Relation", category: "complex" },
  json: { label: "JSON", category: "complex" },
  color: { label: "Color", category: "complex" },
  icon: { label: "Icon", category: "complex" },
};

// =============================================================================
// MEDIA SECURITY — mirrors backend ALLOWED_MEDIA_TYPES
// =============================================================================

export const ALLOWED_MEDIA_TYPES = new Set([
  "image/jpeg",
  "image/png",
  "image/gif",
  "image/webp",
  "image/svg+xml",
  "application/pdf",
  "video/mp4",
  "video/webm",
  "audio/mpeg",
  "audio/ogg",
]);

export const ALLOWED_MEDIA_EXTENSIONS = new Set([
  "jpg",
  "jpeg",
  "png",
  "gif",
  "webp",
  "svg",
  "pdf",
  "mp4",
  "webm",
  "mp3",
  "ogg",
]);

export const DEFAULT_MAX_MEDIA_FILE_SIZE_MB = 10;

// =============================================================================
// BUSINESS RULES
// =============================================================================

/** Auto-save debounce delay (ms). Backend throttles versions at 30s. */
export const DRAFT_AUTO_SAVE_DEBOUNCE_MS = 2000;

/** CMS API key prefix (display purposes) */
export const API_KEY_PREFIX = "cmsk_";
