/**
 * Field-level validation for FormBuilder fields.
 *
 * Validates values based on field_type and validation_rules.
 * Called on blur (per-field) and on submit (all fields).
 */
import type { FormField } from "@/types/forms";

// =============================================================================
// PATTERNS
// =============================================================================

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const URL_REGEX = /^https?:\/\/.+\..+/;
const PHONE_REGEX = /^[+]?[\d\s().-]{7,20}$/;

// =============================================================================
// SINGLE FIELD VALIDATION
// =============================================================================

/**
 * Validate a single field value. Returns an error message or null.
 */
export function validateFieldValue(field: FormField, value: unknown): string | null {
  const strVal = typeof value === "string" ? value.trim() : "";
  const isEmpty =
    value === null ||
    value === undefined ||
    (typeof value === "string" && strVal === "") ||
    (Array.isArray(value) && value.length === 0);

  // Required check
  if (field.is_required && isEmpty) {
    return `${field.label} is required`;
  }

  // Skip type validation if empty and not required
  if (isEmpty) return null;

  const rules = field.validation_rules ?? {};

  switch (field.field_type) {
    // ---- Text-like ----
    case "text":
    case "textarea":
      return validateTextRules(strVal, rules, field.label);

    case "email":
      if (!EMAIL_REGEX.test(strVal)) {
        return "Please enter a valid email address";
      }
      return validateTextRules(strVal, rules, field.label);

    case "url":
      if (!URL_REGEX.test(strVal)) {
        return "Please enter a valid URL (e.g. https://example.com)";
      }
      return validateTextRules(strVal, rules, field.label);

    case "phone":
      if (!PHONE_REGEX.test(strVal)) {
        return "Please enter a valid phone number";
      }
      return null;

    // ---- Numeric ----
    case "integer": {
      const num = Number(value);
      if (isNaN(num) || !Number.isInteger(num)) {
        return "Please enter a whole number";
      }
      return validateNumericRules(num, rules, field.label);
    }

    case "decimal":
    case "currency": {
      const num = Number(value);
      if (isNaN(num)) {
        return "Please enter a valid number";
      }
      return validateNumericRules(num, rules, field.label);
    }

    case "rating": {
      const num = Number(value);
      const max = (rules.max as number) || 5;
      if (isNaN(num) || num < 1 || num > max) {
        return `Please select a rating between 1 and ${max}`;
      }
      return null;
    }

    // ---- Selection ----
    case "select":
    case "radio":
      // Value must be one of the options
      if (field.options && field.options.length > 0) {
        const validValues = getOptionValues(field);
        if (!validValues.includes(String(value))) {
          return "Please select a valid option";
        }
      }
      return null;

    case "multiselect":
    case "checkbox_group": {
      if (!Array.isArray(value) || value.length === 0) {
        if (field.is_required) return "Please select at least one option";
        return null;
      }
      if (field.options && field.options.length > 0) {
        const validValues = getOptionValues(field);
        const invalid = (value as string[]).find((v) => !validValues.includes(v));
        if (invalid) return `Invalid option: ${invalid}`;
      }
      const minSelect = rules.min_selections as number | undefined;
      const maxSelect = rules.max_selections as number | undefined;
      if (minSelect && (value as string[]).length < minSelect) {
        return `Select at least ${minSelect} options`;
      }
      if (maxSelect && (value as string[]).length > maxSelect) {
        return `Select at most ${maxSelect} options`;
      }
      return null;
    }

    // ---- Date/Time ----
    case "date": {
      if (strVal && isNaN(Date.parse(strVal))) {
        return "Please enter a valid date";
      }
      return validateDateRules(strVal, rules);
    }

    case "datetime": {
      if (strVal && isNaN(Date.parse(strVal))) {
        return "Please enter a valid date and time";
      }
      return null;
    }

    case "time":
      if (strVal && !/^\d{2}:\d{2}(:\d{2})?$/.test(strVal)) {
        return "Please enter a valid time";
      }
      return null;

    // ---- File/Image ----
    case "file":
      if (value instanceof File) {
        return validateFileRules(value, rules);
      }
      // If it's a string (URL from previously uploaded), it's valid
      if (typeof value === "string") return null;
      return null;

    case "image":
      if (value instanceof File) {
        if (!value.type.startsWith("image/")) {
          return "Please upload an image file (JPEG, PNG, GIF, or WebP)";
        }
        return validateFileRules(value, rules);
      }
      if (typeof value === "string") return null;
      return null;

    // ---- Boolean ----
    case "boolean":
    case "checkbox":
      return null;

    // ---- Complex ----
    case "location":
      return validateTextRules(strVal, rules, field.label);

    default:
      return null;
  }
}

// =============================================================================
// BULK VALIDATION
// =============================================================================

/**
 * Validate all fields. Returns a Record of field_key → error message.
 * Empty record means all valid.
 */
export function validateAllFields(
  fields: FormField[],
  values: Record<string, unknown>,
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fields) {
    if (field.is_hidden) continue;
    const error = validateFieldValue(field, values[field.field_key]);
    if (error) {
      errors[field.field_key] = error;
    }
  }
  return errors;
}

// =============================================================================
// HELPERS
// =============================================================================

function validateTextRules(
  value: string,
  rules: Record<string, unknown>,
  label: string,
): string | null {
  const minLen = rules.min_length as number | undefined;
  const maxLen = rules.max_length as number | undefined;
  const pattern = rules.pattern as string | undefined;

  if (minLen && value.length < minLen) {
    return `${label} must be at least ${minLen} characters`;
  }
  if (maxLen && value.length > maxLen) {
    return `${label} must be at most ${maxLen} characters`;
  }
  if (pattern) {
    try {
      if (!new RegExp(pattern).test(value)) {
        return (rules.pattern_message as string) || `${label} format is invalid`;
      }
    } catch {
      // Invalid regex pattern — skip
    }
  }
  return null;
}

function validateNumericRules(
  value: number,
  rules: Record<string, unknown>,
  label: string,
): string | null {
  const min = rules.min as number | undefined;
  const max = rules.max as number | undefined;
  if (min !== undefined && value < min) {
    return `${label} must be at least ${min}`;
  }
  if (max !== undefined && value > max) {
    return `${label} must be at most ${max}`;
  }
  return null;
}

function validateDateRules(
  value: string,
  rules: Record<string, unknown>,
): string | null {
  const minDate = rules.min_date as string | undefined;
  const maxDate = rules.max_date as string | undefined;
  if (minDate && value < minDate) {
    return `Date must be on or after ${minDate}`;
  }
  if (maxDate && value > maxDate) {
    return `Date must be on or before ${maxDate}`;
  }
  return null;
}

function validateFileRules(
  file: File,
  rules: Record<string, unknown>,
): string | null {
  const maxSize = (rules.max_file_size as number) || 10 * 1024 * 1024; // 10 MB default
  if (file.size > maxSize) {
    return `File must be smaller than ${Math.round(maxSize / 1024 / 1024)} MB`;
  }
  const allowedTypes = rules.allowed_types as string[] | undefined;
  if (allowedTypes && !allowedTypes.includes(file.type)) {
    return `File type ${file.type} is not allowed`;
  }
  return null;
}

function getOptionValues(field: FormField): string[] {
  if (!Array.isArray(field.options)) return [];
  return field.options.map((opt) => {
    if (typeof opt === "string") return opt;
    const o = opt as Record<string, unknown>;
    return String(o.value ?? o.label ?? "");
  });
}
