/**
 * Form Builder types matching backend API contracts.
 *
 * Backend source: apps.forms.api.serializers, apps.forms.policies,
 *                 apps.core.constants (FormStatus, ResponseStatus, FieldType)
 */

import type { WithPermissions } from "@/types/api";

// =============================================================================
// ENUMS
// =============================================================================

export type FormStatus = "draft" | "active" | "archived" | "deleted";
export type ResponseStatus = "draft" | "submitted" | "processed" | "void" | "expired";
export type OwnerType = "system" | "platform" | "business";
export type FormScope = "platform" | "business";

export type FieldType =
  // Text
  | "text"
  | "textarea"
  | "email"
  | "url"
  | "phone"
  // Numeric
  | "integer"
  | "decimal"
  | "currency"
  | "rating"
  // Boolean
  | "boolean"
  | "checkbox"
  // Date/Time
  | "date"
  | "datetime"
  | "time"
  // Selection
  | "select"
  | "radio"
  | "multiselect"
  | "checkbox_group"
  // File
  | "file"
  | "image"
  // Complex
  | "location"
  | "repeatable";

// =============================================================================
// FORM FIELD
// =============================================================================

export type FormField = {
  id: string;
  field_key: string;
  field_type: FieldType;
  label: string;
  description: string;
  placeholder: string;
  order: number;
  step_tag: string;
  section_tag: string;
  options: unknown[];
  validation_rules: Record<string, unknown>;
  ui_config: Record<string, unknown>;
  default_value: unknown;
  is_required: boolean;
  is_indexed: boolean;
  is_hidden: boolean;
  is_readonly: boolean;
};

// =============================================================================
// FORM TEMPLATE
// =============================================================================

/** List view (FormTemplateListOutputSerializer). */
export type FormTemplateList = {
  id: string;
  name: string;
  slug: string;
  description: string;
  owner_type: OwnerType;
  scope: FormScope;
  status: FormStatus;
  version: number;
  is_current: boolean;
  is_template_public: boolean;
  created_at: string;
  updated_at: string;
};

/** Detail view (FormTemplateDetailOutputSerializer). */
export type FormTemplateDetail = {
  id: string;
  name: string;
  slug: string;
  description: string;
  owner_type: OwnerType;
  owner_id: string | null;
  scope: FormScope;
  status: FormStatus;
  version: number;
  is_current: boolean;
  parent_version: number | null;
  is_template_public: boolean;
  forked_from: string | null;
  forked_from_name: string | null;
  settings: Record<string, unknown>;
  fields: FormField[];
  created_at: string;
  updated_at: string;
};

// =============================================================================
// FORM RESPONSE
// =============================================================================

/** List view (FormResponseListOutputSerializer). */
export type FormResponseList = {
  id: string;
  form_template: string;
  form_name: string;
  form_version: number;
  submitted_by: string;
  submitter_email: string;
  submitter_username: string;
  submitter_display_name: string;
  data: Record<string, unknown>;
  status: ResponseStatus;
  submitted_at: string | null;
  processed_at: string | null;
  created_at: string;
};

/** Detail view (FormResponseDetailOutputSerializer). */
export type FormResponseDetail = {
  id: string;
  form_template: string;
  form_name: string;
  form_version: number;
  submitted_by: string;
  submitter_email: string;
  submitter_username: string;
  submitter_display_name: string;
  submitter_context: Record<string, unknown>;
  data: Record<string, unknown>;
  status: ResponseStatus;
  submitted_at: string | null;
  processed_at: string | null;
  processed_by: string | null;
  processor_email: string | null;
  processor_notes: string;
  created_at: string;
  updated_at: string;
};

// =============================================================================
// PERMISSION TYPES (from FormTemplatePolicy.get_viewer_permissions)
// =============================================================================

export type FormTemplatePermissions = {
  can_edit: boolean;
  can_delete: boolean;
  can_publish: boolean;
  can_archive: boolean;
};

export type FormTemplateDetailWithPerms = FormTemplateDetail &
  WithPermissions<FormTemplatePermissions>;

// =============================================================================
// INPUT TYPES
// =============================================================================

export type CreateTemplateInput = {
  name: string;
  slug?: string;
  description?: string;
  owner_type: OwnerType;
  owner_id?: string;
  scope: FormScope;
  settings?: Record<string, unknown>;
};

export type UpdateTemplateInput = {
  name?: string;
  description?: string;
  settings?: Record<string, unknown>;
};

export type CreateFieldInput = {
  field_key: string;
  field_type: FieldType;
  label: string;
  description?: string;
  placeholder?: string;
  order: number;
  step_tag?: string;
  section_tag?: string;
  options?: unknown[];
  validation_rules?: Record<string, unknown>;
  ui_config?: Record<string, unknown>;
  default_value?: unknown;
  is_required?: boolean;
  is_indexed?: boolean;
  is_hidden?: boolean;
  is_readonly?: boolean;
};

export type UpdateFieldInput = {
  label?: string;
  help_text?: string;
  placeholder?: string;
  options?: unknown[];
  validation_rules?: Record<string, unknown>;
  is_required?: boolean;
  is_indexable?: boolean;
  section_tag?: string;
  step_tag?: string;
  conditional_logic?: Record<string, unknown>;
};

export type ReorderFieldItem = {
  field_id: string;
  order: number;
};

export type ForkTemplateInput = {
  new_owner_type: OwnerType;
  new_owner_id: string;
  new_name?: string;
  new_slug?: string;
};

export type CreateResponseInput = {
  data: Record<string, unknown>;
};

export type UpdateResponseInput = {
  data: Record<string, unknown>;
};

export type ProcessResponseInput = {
  notes?: string;
};

export type VoidResponseInput = {
  reason?: string;
};

// =============================================================================
// QUERY PARAMS
// =============================================================================

export type FormResponseListParams = {
  status?: ResponseStatus;
  page?: number;
  page_size?: number;
};
