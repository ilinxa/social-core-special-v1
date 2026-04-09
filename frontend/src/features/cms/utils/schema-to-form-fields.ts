/**
 * Schema-to-FormField Mapper
 * ============================
 * Converts CMS block template schema fields to form builder FormField objects.
 * Enables reuse of the existing FieldRenderer for 11 of 18 CMS field types.
 *
 * Backend: apps.cms.validators.SchemaValidator
 */

import type { CmsSchemaField } from "@/features/cms/types";

/**
 * Map CMS field types to form builder FieldType equivalents.
 * Returns null for types that need custom CMS-specific components.
 */
const CMS_TO_FORM_TYPE: Record<string, string | null> = {
  text: "text",
  textarea: "textarea",
  number: "decimal",
  boolean: "boolean",
  url: "url",
  email: "email",
  date: "date",
  datetime: "datetime",
  select: "select",
  multiselect: "checkbox_group",
  // Types needing custom CMS components (return null):
  richtext: null,
  media: null,
  color: null,
  icon: null,
  repeater: null,
  list: null,
  relation: null,
  json: null,
};

/**
 * Check if a CMS field type can be rendered by the form builder's FieldRenderer.
 */
export function isFormBuilderCompatible(cmsFieldType: string): boolean {
  return CMS_TO_FORM_TYPE[cmsFieldType] !== null &&
    CMS_TO_FORM_TYPE[cmsFieldType] !== undefined;
}

/**
 * Get the form builder FieldType for a CMS field type.
 * Returns null if the CMS type needs a custom component.
 */
export function getFormBuilderFieldType(cmsFieldType: string): string | null {
  return CMS_TO_FORM_TYPE[cmsFieldType] ?? null;
}

/**
 * Convert a CMS schema field to a form builder FormField-compatible shape.
 * Only works for form-builder-compatible types. Returns null for custom types.
 */
export function cmsSchemaFieldToFormField(field: CmsSchemaField) {
  const formType = getFormBuilderFieldType(field.type);
  if (!formType) return null;

  return {
    id: field.key,
    field_key: field.key,
    field_type: formType,
    label: field.label ?? field.key,
    description: "",
    placeholder: "",
    order: 0,
    step_tag: "",
    section_tag: "",
    options: field.choices?.map((c) => ({ value: c, label: c })) ?? [],
    validation_rules: {
      ...(field.max_length !== undefined && { max_length: field.max_length }),
      ...(field.min_length !== undefined && { min_length: field.min_length }),
      ...(field.pattern !== undefined && { pattern: field.pattern }),
      ...(field.min !== undefined && { min: field.min }),
      ...(field.max !== undefined && { max: field.max }),
      ...(field.min_selected !== undefined && {
        min_selections: field.min_selected,
      }),
      ...(field.max_selected !== undefined && {
        max_selections: field.max_selected,
      }),
    },
    ui_config: {},
    default_value: null,
    is_required: field.required ?? false,
    is_indexed: false,
    is_hidden: false,
    is_readonly: false,
  };
}
