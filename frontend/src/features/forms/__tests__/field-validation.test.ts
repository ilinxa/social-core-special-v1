import { describe, it, expect } from "vitest";

import type { FormField } from "@/types/forms";
import { validateFieldValue, validateAllFields } from "../utils/field-validation";

// =============================================================================
// HELPERS
// =============================================================================

/** Build a mock FormField with sensible defaults, overridable via Partial. */
function makeField(overrides: Partial<FormField> = {}): FormField {
  return {
    id: "field-1",
    field_key: "test_field",
    field_type: "text",
    label: "Test Field",
    description: "",
    placeholder: "",
    is_required: false,
    is_hidden: false,
    is_readonly: false,
    is_indexed: false,
    order: 0,
    section_tag: "",
    step_tag: "",
    options: [],
    validation_rules: {},
    ui_config: {},
    default_value: null,
    ...overrides,
  };
}

// =============================================================================
// validateFieldValue
// =============================================================================

describe("validateFieldValue", () => {
  // ---------------------------------------------------------------------------
  // Required / Optional
  // ---------------------------------------------------------------------------
  describe("required / optional checks", () => {
    it("returns error when required field value is null", () => {
      const field = makeField({ is_required: true, label: "Name" });
      expect(validateFieldValue(field, null)).toBe("Name is required");
    });

    it("returns error when required field value is undefined", () => {
      const field = makeField({ is_required: true, label: "Name" });
      expect(validateFieldValue(field, undefined)).toBe("Name is required");
    });

    it("returns error when required field value is empty string", () => {
      const field = makeField({ is_required: true, label: "Name" });
      expect(validateFieldValue(field, "")).toBe("Name is required");
    });

    it("returns error when required field value is whitespace-only string", () => {
      const field = makeField({ is_required: true, label: "Name" });
      expect(validateFieldValue(field, "   ")).toBe("Name is required");
    });

    it("returns null for optional field with null value", () => {
      const field = makeField({ is_required: false });
      expect(validateFieldValue(field, null)).toBeNull();
    });

    it("returns null for optional field with undefined value", () => {
      const field = makeField({ is_required: false });
      expect(validateFieldValue(field, undefined)).toBeNull();
    });

    it("returns null for optional field with empty string", () => {
      const field = makeField({ is_required: false });
      expect(validateFieldValue(field, "")).toBeNull();
    });

    it("validates value when present even if field is not required", () => {
      const field = makeField({ is_required: false, field_type: "email" });
      expect(validateFieldValue(field, "not-email")).toBe(
        "Please enter a valid email address",
      );
    });

    it("still validates value for hidden fields (hidden check is in validateAllFields)", () => {
      const field = makeField({
        is_hidden: true,
        is_required: false,
        field_type: "email",
      });
      expect(validateFieldValue(field, "bad-email")).toBe(
        "Please enter a valid email address",
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Email
  // ---------------------------------------------------------------------------
  describe("email field", () => {
    const field = makeField({ field_type: "email" });

    it("accepts a valid email", () => {
      expect(validateFieldValue(field, "user@example.com")).toBeNull();
    });

    it("accepts an email with subdomain", () => {
      expect(validateFieldValue(field, "admin@mail.example.co.uk")).toBeNull();
    });

    it("rejects email without @", () => {
      expect(validateFieldValue(field, "userexample.com")).toBe(
        "Please enter a valid email address",
      );
    });

    it("rejects email without domain", () => {
      expect(validateFieldValue(field, "user@")).toBe(
        "Please enter a valid email address",
      );
    });

    it("rejects email with spaces", () => {
      expect(validateFieldValue(field, "user @example.com")).toBe(
        "Please enter a valid email address",
      );
    });

    it("applies text validation rules after format check", () => {
      const emailWithMax = makeField({
        field_type: "email",
        label: "Email",
        validation_rules: { max_length: 20 },
      });
      expect(
        validateFieldValue(emailWithMax, "very.long.email.address@example.com"),
      ).toBe("Email must be at most 20 characters");
    });
  });

  // ---------------------------------------------------------------------------
  // URL
  // ---------------------------------------------------------------------------
  describe("url field", () => {
    const field = makeField({ field_type: "url" });

    it("accepts a valid http URL", () => {
      expect(validateFieldValue(field, "http://example.com")).toBeNull();
    });

    it("accepts a valid https URL", () => {
      expect(validateFieldValue(field, "https://example.com/path")).toBeNull();
    });

    it("rejects a URL without protocol", () => {
      expect(validateFieldValue(field, "example.com")).toBe(
        "Please enter a valid URL (e.g. https://example.com)",
      );
    });

    it("rejects ftp URL", () => {
      expect(validateFieldValue(field, "ftp://example.com")).toBe(
        "Please enter a valid URL (e.g. https://example.com)",
      );
    });

    it("rejects random text", () => {
      expect(validateFieldValue(field, "not a url")).toBe(
        "Please enter a valid URL (e.g. https://example.com)",
      );
    });

    it("applies text validation rules after format check", () => {
      const urlWithMax = makeField({
        field_type: "url",
        label: "Website",
        validation_rules: { max_length: 25 },
      });
      expect(
        validateFieldValue(urlWithMax, "https://very-long-domain-name.example.com"),
      ).toBe("Website must be at most 25 characters");
    });
  });

  // ---------------------------------------------------------------------------
  // Phone
  // ---------------------------------------------------------------------------
  describe("phone field", () => {
    const field = makeField({ field_type: "phone" });

    it("accepts a simple phone number", () => {
      expect(validateFieldValue(field, "1234567890")).toBeNull();
    });

    it("accepts a phone number with country code", () => {
      expect(validateFieldValue(field, "+1 (555) 123-4567")).toBeNull();
    });

    it("accepts a phone number with dots", () => {
      expect(validateFieldValue(field, "+44.20.7946.0958")).toBeNull();
    });

    it("rejects a number that is too short", () => {
      expect(validateFieldValue(field, "12345")).toBe(
        "Please enter a valid phone number",
      );
    });

    it("rejects alphabetic input", () => {
      expect(validateFieldValue(field, "not a phone")).toBe(
        "Please enter a valid phone number",
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Text / Textarea
  // ---------------------------------------------------------------------------
  describe("text field", () => {
    it("returns null for valid text without rules", () => {
      const field = makeField({ field_type: "text" });
      expect(validateFieldValue(field, "hello world")).toBeNull();
    });

    it("enforces min_length", () => {
      const field = makeField({
        field_type: "text",
        label: "Bio",
        validation_rules: { min_length: 10 },
      });
      expect(validateFieldValue(field, "short")).toBe(
        "Bio must be at least 10 characters",
      );
    });

    it("passes when text meets min_length", () => {
      const field = makeField({
        field_type: "text",
        validation_rules: { min_length: 3 },
      });
      expect(validateFieldValue(field, "hello")).toBeNull();
    });

    it("enforces max_length", () => {
      const field = makeField({
        field_type: "text",
        label: "Title",
        validation_rules: { max_length: 5 },
      });
      expect(validateFieldValue(field, "too long text")).toBe(
        "Title must be at most 5 characters",
      );
    });

    it("passes when text meets max_length", () => {
      const field = makeField({
        field_type: "text",
        validation_rules: { max_length: 20 },
      });
      expect(validateFieldValue(field, "within limit")).toBeNull();
    });

    it("enforces pattern rule", () => {
      const field = makeField({
        field_type: "text",
        label: "Code",
        validation_rules: { pattern: "^[A-Z]{3}$" },
      });
      expect(validateFieldValue(field, "abc")).toBe("Code format is invalid");
    });

    it("passes when text matches pattern", () => {
      const field = makeField({
        field_type: "text",
        validation_rules: { pattern: "^[A-Z]{3}$" },
      });
      expect(validateFieldValue(field, "ABC")).toBeNull();
    });

    it("uses pattern_message when provided", () => {
      const field = makeField({
        field_type: "text",
        validation_rules: {
          pattern: "^[A-Z]+$",
          pattern_message: "Only uppercase letters allowed",
        },
      });
      expect(validateFieldValue(field, "abc")).toBe(
        "Only uppercase letters allowed",
      );
    });

    it("skips invalid regex pattern gracefully", () => {
      const field = makeField({
        field_type: "text",
        validation_rules: { pattern: "[invalid(" },
      });
      expect(validateFieldValue(field, "anything")).toBeNull();
    });
  });

  describe("textarea field", () => {
    it("applies text validation rules to textarea", () => {
      const field = makeField({
        field_type: "textarea",
        label: "Description",
        validation_rules: { min_length: 5 },
      });
      expect(validateFieldValue(field, "hi")).toBe(
        "Description must be at least 5 characters",
      );
    });

    it("passes valid textarea content", () => {
      const field = makeField({ field_type: "textarea" });
      expect(validateFieldValue(field, "A long description here.")).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Integer
  // ---------------------------------------------------------------------------
  describe("integer field", () => {
    const field = makeField({ field_type: "integer", label: "Quantity" });

    it("accepts a valid string-encoded integer", () => {
      expect(validateFieldValue(field, "42")).toBeNull();
    });

    it("accepts string-encoded zero", () => {
      expect(validateFieldValue(field, "0")).toBeNull();
    });

    it("accepts string-encoded negative integer", () => {
      expect(validateFieldValue(field, "-10")).toBeNull();
    });

    it("rejects a string-encoded decimal number", () => {
      expect(validateFieldValue(field, "3.14")).toBe(
        "Please enter a whole number",
      );
    });

    it("rejects non-numeric string", () => {
      expect(validateFieldValue(field, "abc")).toBe(
        "Please enter a whole number",
      );
    });

    it("enforces min bound", () => {
      const withMin = makeField({
        field_type: "integer",
        label: "Score",
        validation_rules: { min: 0 },
      });
      expect(validateFieldValue(withMin, "-5")).toBe(
        "Score must be at least 0",
      );
    });

    it("enforces max bound", () => {
      const withMax = makeField({
        field_type: "integer",
        label: "Score",
        validation_rules: { max: 100 },
      });
      expect(validateFieldValue(withMax, "150")).toBe(
        "Score must be at most 100",
      );
    });

    it("passes when within min/max bounds", () => {
      const withBounds = makeField({
        field_type: "integer",
        validation_rules: { min: 1, max: 10 },
      });
      expect(validateFieldValue(withBounds, "5")).toBeNull();
    });

    it("passes when value equals min bound", () => {
      const withMin = makeField({
        field_type: "integer",
        validation_rules: { min: 0 },
      });
      expect(validateFieldValue(withMin, "0")).toBeNull();
    });

    it("passes when value equals max bound", () => {
      const withMax = makeField({
        field_type: "integer",
        validation_rules: { max: 100 },
      });
      expect(validateFieldValue(withMax, "100")).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Decimal / Currency
  // ---------------------------------------------------------------------------
  describe("decimal field", () => {
    const field = makeField({ field_type: "decimal", label: "Amount" });

    it("accepts a valid string-encoded decimal", () => {
      expect(validateFieldValue(field, "3.14")).toBeNull();
    });

    it("accepts a string-encoded integer value", () => {
      expect(validateFieldValue(field, "10")).toBeNull();
    });

    it("accepts a string-encoded number with trailing zeros", () => {
      expect(validateFieldValue(field, "99.99")).toBeNull();
    });

    it("rejects non-numeric string", () => {
      expect(validateFieldValue(field, "abc")).toBe(
        "Please enter a valid number",
      );
    });

    it("enforces min bound", () => {
      const withMin = makeField({
        field_type: "decimal",
        label: "Price",
        validation_rules: { min: 0 },
      });
      expect(validateFieldValue(withMin, "-1.5")).toBe(
        "Price must be at least 0",
      );
    });

    it("enforces max bound", () => {
      const withMax = makeField({
        field_type: "decimal",
        label: "Price",
        validation_rules: { max: 1000 },
      });
      expect(validateFieldValue(withMax, "1500")).toBe(
        "Price must be at most 1000",
      );
    });

    it("passes when value equals min bound", () => {
      const withMin = makeField({
        field_type: "decimal",
        validation_rules: { min: 0 },
      });
      expect(validateFieldValue(withMin, "0")).toBeNull();
    });

    it("passes when value equals max bound", () => {
      const withMax = makeField({
        field_type: "decimal",
        validation_rules: { max: 1000 },
      });
      expect(validateFieldValue(withMax, "1000")).toBeNull();
    });
  });

  describe("currency field", () => {
    it("accepts a valid currency value", () => {
      const field = makeField({ field_type: "currency" });
      expect(validateFieldValue(field, "49.99")).toBeNull();
    });

    it("rejects non-numeric input", () => {
      const field = makeField({ field_type: "currency" });
      expect(validateFieldValue(field, "free")).toBe(
        "Please enter a valid number",
      );
    });

    it("enforces min rule", () => {
      const field = makeField({
        field_type: "currency",
        label: "Total",
        validation_rules: { min: 1, max: 500 },
      });
      expect(validateFieldValue(field, "0.5")).toBe(
        "Total must be at least 1",
      );
    });

    it("enforces max rule", () => {
      const field = makeField({
        field_type: "currency",
        label: "Total",
        validation_rules: { min: 1, max: 500 },
      });
      expect(validateFieldValue(field, "600")).toBe(
        "Total must be at most 500",
      );
    });

    it("passes when value is within bounds", () => {
      const field = makeField({
        field_type: "currency",
        validation_rules: { min: 1, max: 500 },
      });
      expect(validateFieldValue(field, "250")).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Rating
  // ---------------------------------------------------------------------------
  describe("rating field", () => {
    it("accepts a value within default 1-5 range", () => {
      const field = makeField({ field_type: "rating" });
      expect(validateFieldValue(field, "3")).toBeNull();
    });

    it("accepts value of 1 (lower bound)", () => {
      const field = makeField({ field_type: "rating" });
      expect(validateFieldValue(field, "1")).toBeNull();
    });

    it("accepts value of 5 (upper bound)", () => {
      const field = makeField({ field_type: "rating" });
      expect(validateFieldValue(field, "5")).toBeNull();
    });

    it("rejects value of 0", () => {
      const field = makeField({ field_type: "rating" });
      expect(validateFieldValue(field, "0")).toBe(
        "Please select a rating between 1 and 5",
      );
    });

    it("rejects value above default max", () => {
      const field = makeField({ field_type: "rating" });
      expect(validateFieldValue(field, "6")).toBe(
        "Please select a rating between 1 and 5",
      );
    });

    it("rejects negative value", () => {
      const field = makeField({ field_type: "rating" });
      expect(validateFieldValue(field, "-1")).toBe(
        "Please select a rating between 1 and 5",
      );
    });

    it("uses custom max from validation_rules", () => {
      const field = makeField({
        field_type: "rating",
        validation_rules: { max: 10 },
      });
      expect(validateFieldValue(field, "8")).toBeNull();
      expect(validateFieldValue(field, "11")).toBe(
        "Please select a rating between 1 and 10",
      );
    });

    it("rejects non-numeric value", () => {
      const field = makeField({ field_type: "rating" });
      expect(validateFieldValue(field, "great")).toBe(
        "Please select a rating between 1 and 5",
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Boolean / Checkbox
  // ---------------------------------------------------------------------------
  describe("boolean / checkbox fields", () => {
    it("returns null for boolean with string true", () => {
      const field = makeField({ field_type: "boolean" });
      expect(validateFieldValue(field, "true")).toBeNull();
    });

    it("returns null for boolean with string false", () => {
      const field = makeField({ field_type: "boolean" });
      expect(validateFieldValue(field, "false")).toBeNull();
    });

    it("returns null for checkbox with string value", () => {
      const field = makeField({ field_type: "checkbox" });
      expect(validateFieldValue(field, "yes")).toBeNull();
    });

    it("returns null for boolean with null value (optional)", () => {
      const field = makeField({ field_type: "boolean", is_required: false });
      expect(validateFieldValue(field, null)).toBeNull();
    });

    it("returns required error for boolean with empty value when required", () => {
      const field = makeField({
        field_type: "boolean",
        is_required: true,
        label: "Agreement",
      });
      expect(validateFieldValue(field, "")).toBe("Agreement is required");
    });
  });

  // ---------------------------------------------------------------------------
  // Date
  // ---------------------------------------------------------------------------
  describe("date field", () => {
    const field = makeField({ field_type: "date" });

    it("accepts a valid YYYY-MM-DD date", () => {
      expect(validateFieldValue(field, "2025-06-15")).toBeNull();
    });

    it("accepts a date with timezone info (Date.parse compatible)", () => {
      expect(validateFieldValue(field, "2025-06-15T00:00:00Z")).toBeNull();
    });

    it("rejects a clearly invalid date string", () => {
      expect(validateFieldValue(field, "not-a-date")).toBe(
        "Please enter a valid date",
      );
    });

    it("enforces min_date rule", () => {
      const withMinDate = makeField({
        field_type: "date",
        validation_rules: { min_date: "2025-01-01" },
      });
      expect(validateFieldValue(withMinDate, "2024-12-31")).toBe(
        "Date must be on or after 2025-01-01",
      );
    });

    it("passes when date equals min_date", () => {
      const withMinDate = makeField({
        field_type: "date",
        validation_rules: { min_date: "2025-01-01" },
      });
      expect(validateFieldValue(withMinDate, "2025-01-01")).toBeNull();
    });

    it("enforces max_date rule", () => {
      const withMaxDate = makeField({
        field_type: "date",
        validation_rules: { max_date: "2025-12-31" },
      });
      expect(validateFieldValue(withMaxDate, "2026-01-01")).toBe(
        "Date must be on or before 2025-12-31",
      );
    });

    it("passes when date equals max_date", () => {
      const withMaxDate = makeField({
        field_type: "date",
        validation_rules: { max_date: "2025-12-31" },
      });
      expect(validateFieldValue(withMaxDate, "2025-12-31")).toBeNull();
    });

    it("passes when date is within min/max range", () => {
      const withRange = makeField({
        field_type: "date",
        validation_rules: { min_date: "2025-01-01", max_date: "2025-12-31" },
      });
      expect(validateFieldValue(withRange, "2025-06-15")).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // DateTime
  // ---------------------------------------------------------------------------
  describe("datetime field", () => {
    it("accepts a valid ISO datetime", () => {
      const field = makeField({ field_type: "datetime" });
      expect(validateFieldValue(field, "2025-06-15T10:30:00")).toBeNull();
    });

    it("rejects an invalid datetime string", () => {
      const field = makeField({ field_type: "datetime" });
      expect(validateFieldValue(field, "not-a-datetime")).toBe(
        "Please enter a valid date and time",
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Time
  // ---------------------------------------------------------------------------
  describe("time field", () => {
    const field = makeField({ field_type: "time" });

    it("accepts HH:MM format", () => {
      expect(validateFieldValue(field, "14:30")).toBeNull();
    });

    it("accepts HH:MM:SS format", () => {
      expect(validateFieldValue(field, "14:30:45")).toBeNull();
    });

    it("rejects single-digit hours/minutes", () => {
      expect(validateFieldValue(field, "1:5")).toBe(
        "Please enter a valid time",
      );
    });

    it("rejects random text", () => {
      expect(validateFieldValue(field, "noon")).toBe(
        "Please enter a valid time",
      );
    });

    it("rejects time with extra characters", () => {
      expect(validateFieldValue(field, "14:30:45:00")).toBe(
        "Please enter a valid time",
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Select / Radio
  // ---------------------------------------------------------------------------
  describe("select / radio fields", () => {
    it("accepts value matching a string option", () => {
      const field = makeField({
        field_type: "select",
        options: ["red", "green", "blue"],
      });
      expect(validateFieldValue(field, "green")).toBeNull();
    });

    it("rejects value not in string options", () => {
      const field = makeField({
        field_type: "select",
        options: ["red", "green", "blue"],
      });
      expect(validateFieldValue(field, "yellow")).toBe(
        "Please select a valid option",
      );
    });

    it("accepts value matching an object option by value key", () => {
      const field = makeField({
        field_type: "radio",
        options: [
          { value: "opt1", label: "Option 1" },
          { value: "opt2", label: "Option 2" },
        ],
      });
      expect(validateFieldValue(field, "opt1")).toBeNull();
    });

    it("rejects value not matching any object option value", () => {
      const field = makeField({
        field_type: "radio",
        options: [
          { value: "opt1", label: "Option 1" },
          { value: "opt2", label: "Option 2" },
        ],
      });
      expect(validateFieldValue(field, "opt3")).toBe(
        "Please select a valid option",
      );
    });

    it("falls back to label when option has no value key", () => {
      const field = makeField({
        field_type: "select",
        options: [{ label: "Alpha" }, { label: "Beta" }],
      });
      expect(validateFieldValue(field, "Alpha")).toBeNull();
    });

    it("passes any value when options array is empty", () => {
      const field = makeField({ field_type: "select", options: [] });
      expect(validateFieldValue(field, "anything")).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Multiselect / Checkbox_group
  // ---------------------------------------------------------------------------
  describe("multiselect / checkbox_group fields", () => {
    it("accepts valid array of selected options", () => {
      const field = makeField({
        field_type: "multiselect",
        is_required: false,
        options: ["a", "b", "c"],
      });
      expect(validateFieldValue(field, ["a", "c"])).toBeNull();
    });

    it("accepts valid array when required", () => {
      const field = makeField({
        field_type: "multiselect",
        is_required: true,
        options: ["a", "b"],
      });
      expect(validateFieldValue(field, ["a"])).toBeNull();
    });

    it("rejects invalid option in array", () => {
      const field = makeField({
        field_type: "multiselect",
        options: ["a", "b", "c"],
      });
      expect(validateFieldValue(field, ["a", "z"])).toBe("Invalid option: z");
    });

    it("rejects non-array string value when required", () => {
      const field = makeField({
        field_type: "multiselect",
        is_required: true,
        options: ["a", "b"],
      });
      expect(validateFieldValue(field, "a")).toBe(
        "Please select at least one option",
      );
    });

    it("returns null for non-array string value when not required", () => {
      const field = makeField({
        field_type: "multiselect",
        is_required: false,
        options: ["a", "b"],
      });
      expect(validateFieldValue(field, "a")).toBeNull();
    });

    it("returns required error for empty array when required", () => {
      const field = makeField({
        field_type: "checkbox_group",
        is_required: true,
        label: "Choices",
        options: ["x", "y"],
      });
      expect(validateFieldValue(field, [])).toBe("Choices is required");
    });

    it("returns null for empty array when not required", () => {
      const field = makeField({
        field_type: "checkbox_group",
        is_required: false,
        options: ["x", "y"],
      });
      expect(validateFieldValue(field, [])).toBeNull();
    });

    it("enforces min_selections rule", () => {
      const field = makeField({
        field_type: "multiselect",
        options: ["a", "b", "c"],
        validation_rules: { min_selections: 2 },
      });
      expect(validateFieldValue(field, ["a"])).toBe(
        "Select at least 2 options",
      );
    });

    it("enforces max_selections rule", () => {
      const field = makeField({
        field_type: "multiselect",
        options: ["a", "b", "c", "d"],
        validation_rules: { max_selections: 2 },
      });
      expect(validateFieldValue(field, ["a", "b", "c"])).toBe(
        "Select at most 2 options",
      );
    });

    it("passes when selections within min/max bounds", () => {
      const field = makeField({
        field_type: "multiselect",
        options: ["a", "b", "c"],
        validation_rules: { min_selections: 1, max_selections: 3 },
      });
      expect(validateFieldValue(field, ["a", "b"])).toBeNull();
    });

    it("validates against object options", () => {
      const field = makeField({
        field_type: "multiselect",
        options: [
          { value: "x1", label: "X1" },
          { value: "x2", label: "X2" },
        ],
      });
      expect(validateFieldValue(field, ["x1"])).toBeNull();
      expect(validateFieldValue(field, ["x3"])).toBe("Invalid option: x3");
    });
  });

  // ---------------------------------------------------------------------------
  // File
  // ---------------------------------------------------------------------------
  describe("file field", () => {
    it("accepts a File instance within default size limit", () => {
      const field = makeField({ field_type: "file" });
      const file = new File(["content"], "test.pdf", {
        type: "application/pdf",
      });
      expect(validateFieldValue(field, file)).toBeNull();
    });

    it("validates file size against max_file_size rule", () => {
      const field = makeField({
        field_type: "file",
        validation_rules: { max_file_size: 10 },
      });
      const file = new File(["a".repeat(100)], "big.pdf", {
        type: "application/pdf",
      });
      expect(validateFieldValue(field, file)).toBe(
        "File must be smaller than 0 MB",
      );
    });

    it("validates file type against allowed_types rule", () => {
      const field = makeField({
        field_type: "file",
        validation_rules: { allowed_types: ["application/pdf"] },
      });
      const file = new File(["data"], "test.zip", {
        type: "application/zip",
      });
      expect(validateFieldValue(field, file)).toBe(
        "File type application/zip is not allowed",
      );
    });

    it("accepts a string value (previously uploaded URL)", () => {
      const field = makeField({ field_type: "file" });
      expect(
        validateFieldValue(field, "https://cdn.example.com/file.pdf"),
      ).toBeNull();
    });

    it("returns null for string URL even with validation rules", () => {
      const field = makeField({
        field_type: "file",
        validation_rules: {
          allowed_types: ["application/pdf"],
          max_file_size: 1024,
        },
      });
      expect(
        validateFieldValue(field, "https://cdn.example.com/file.zip"),
      ).toBeNull();
    });

    it("returns required error when required and value is null", () => {
      const field = makeField({
        field_type: "file",
        is_required: true,
        label: "Document",
      });
      expect(validateFieldValue(field, null)).toBe("Document is required");
    });
  });

  // ---------------------------------------------------------------------------
  // Image
  // ---------------------------------------------------------------------------
  describe("image field", () => {
    it("accepts image File", () => {
      const field = makeField({ field_type: "image" });
      const file = new File(["pixels"], "photo.png", { type: "image/png" });
      expect(validateFieldValue(field, file)).toBeNull();
    });

    it("rejects non-image File", () => {
      const field = makeField({ field_type: "image" });
      const file = new File(["data"], "doc.pdf", { type: "application/pdf" });
      expect(validateFieldValue(field, file)).toBe(
        "Please upload an image file (JPEG, PNG, GIF, or WebP)",
      );
    });

    it("validates image file size", () => {
      const field = makeField({
        field_type: "image",
        validation_rules: { max_file_size: 10 },
      });
      const file = new File(["a".repeat(100)], "big.png", { type: "image/png" });
      expect(validateFieldValue(field, file)).toBe(
        "File must be smaller than 0 MB",
      );
    });

    it("accepts a string value (previously uploaded URL)", () => {
      const field = makeField({ field_type: "image" });
      expect(
        validateFieldValue(field, "https://cdn.example.com/photo.jpg"),
      ).toBeNull();
    });

    it("returns required error when required and value is null", () => {
      const field = makeField({
        field_type: "image",
        is_required: true,
        label: "Avatar",
      });
      expect(validateFieldValue(field, null)).toBe("Avatar is required");
    });
  });

  // ---------------------------------------------------------------------------
  // Location
  // ---------------------------------------------------------------------------
  describe("location field", () => {
    it("accepts a valid location string", () => {
      const field = makeField({ field_type: "location" });
      expect(validateFieldValue(field, "New York, NY")).toBeNull();
    });

    it("enforces text validation rules", () => {
      const field = makeField({
        field_type: "location",
        label: "Address",
        validation_rules: { min_length: 10 },
      });
      expect(validateFieldValue(field, "Short")).toBe(
        "Address must be at least 10 characters",
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Unknown / Default field type
  // ---------------------------------------------------------------------------
  describe("unknown field type", () => {
    it("returns null for unrecognized field types", () => {
      const field = makeField({
        field_type: "repeatable" as FormField["field_type"],
      });
      expect(validateFieldValue(field, "anything")).toBeNull();
    });
  });

  // ---------------------------------------------------------------------------
  // Non-string value handling
  // ---------------------------------------------------------------------------
  describe("non-string value handling", () => {
    it("validates raw JS number through integer branch", () => {
      const field = makeField({
        field_type: "integer",
        label: "Count",
        validation_rules: { min: 0 },
      });
      expect(validateFieldValue(field, 42)).toBeNull();
      expect(validateFieldValue(field, -1)).toBe("Count must be at least 0");
    });

    it("validates raw JS number through decimal branch", () => {
      const field = makeField({
        field_type: "decimal",
        label: "Amount",
        validation_rules: { max: 100 },
      });
      expect(validateFieldValue(field, 3.14)).toBeNull();
      expect(validateFieldValue(field, 150)).toBe("Amount must be at most 100");
    });

    it("validates raw JS boolean through boolean branch", () => {
      const field = makeField({ field_type: "boolean" });
      expect(validateFieldValue(field, true)).toBeNull();
      expect(validateFieldValue(field, false)).toBeNull();
    });

    it("validates raw JS array through multiselect branch", () => {
      const field = makeField({
        field_type: "multiselect",
        options: ["a", "b", "c"],
      });
      expect(validateFieldValue(field, ["a", "b"])).toBeNull();
      expect(validateFieldValue(field, ["z"])).toBe("Invalid option: z");
    });

    it("validates File through file branch", () => {
      const field = makeField({ field_type: "file" });
      const file = new File(["content"], "test.pdf", { type: "application/pdf" });
      expect(validateFieldValue(field, file)).toBeNull();
    });

    it("validates string-encoded numbers through numeric branch", () => {
      const field = makeField({
        field_type: "integer",
        label: "Count",
        validation_rules: { min: 0 },
      });
      expect(validateFieldValue(field, "42")).toBeNull();
      expect(validateFieldValue(field, "-1")).toBe("Count must be at least 0");
    });
  });
});

// =============================================================================
// validateAllFields
// =============================================================================

describe("validateAllFields", () => {
  it("returns empty object when all fields are valid", () => {
    const fields = [
      makeField({ field_key: "name", field_type: "text" }),
      makeField({ field_key: "email", field_type: "email" }),
    ];
    const values = { name: "Alice", email: "alice@example.com" };
    expect(validateAllFields(fields, values)).toEqual({});
  });

  it("returns errors keyed by field_key", () => {
    const fields = [
      makeField({
        field_key: "email",
        field_type: "email",
        is_required: true,
        label: "Email",
      }),
      makeField({
        field_key: "score",
        field_type: "integer",
        label: "Score",
      }),
    ];
    const values = { email: "", score: "abc" };
    const errors = validateAllFields(fields, values);
    expect(errors).toEqual({
      email: "Email is required",
      score: "Please enter a whole number",
    });
  });

  it("skips hidden fields entirely", () => {
    const fields = [
      makeField({
        field_key: "visible",
        field_type: "email",
        is_required: true,
        label: "Visible",
      }),
      makeField({
        field_key: "hidden_field",
        field_type: "email",
        is_required: true,
        is_hidden: true,
        label: "Hidden",
      }),
    ];
    const values = { visible: "", hidden_field: "" };
    const errors = validateAllFields(fields, values);
    expect(errors).toEqual({ visible: "Visible is required" });
    expect(errors).not.toHaveProperty("hidden_field");
  });

  it("treats missing values as undefined (triggers required check)", () => {
    const fields = [
      makeField({
        field_key: "name",
        field_type: "text",
        is_required: true,
        label: "Name",
      }),
    ];
    const values = {}; // name not present
    const errors = validateAllFields(fields, values);
    expect(errors).toEqual({ name: "Name is required" });
  });

  it("includes only fields with errors", () => {
    const fields = [
      makeField({ field_key: "good", field_type: "text" }),
      makeField({
        field_key: "bad_email",
        field_type: "email",
        label: "Email",
      }),
      makeField({ field_key: "ok_text", field_type: "text" }),
    ];
    const values = { good: "valid", bad_email: "invalid", ok_text: "fine" };
    const errors = validateAllFields(fields, values);
    expect(Object.keys(errors)).toEqual(["bad_email"]);
    expect(errors.bad_email).toBe("Please enter a valid email address");
  });

  it("handles empty fields array", () => {
    expect(validateAllFields([], {})).toEqual({});
  });

  it("validates multiple field types in one call", () => {
    const fields = [
      makeField({
        field_key: "name",
        field_type: "text",
        is_required: true,
        label: "Name",
      }),
      makeField({
        field_key: "email",
        field_type: "email",
        label: "Email",
      }),
      makeField({
        field_key: "rating",
        field_type: "rating",
        label: "Rating",
      }),
      makeField({
        field_key: "color",
        field_type: "select",
        options: ["red", "blue"],
      }),
    ];
    const values = {
      name: "Alice",
      email: "alice@example.com",
      rating: "4",
      color: "red",
    };
    expect(validateAllFields(fields, values)).toEqual({});
  });

  it("reports errors from multiple fields simultaneously", () => {
    const fields = [
      makeField({
        field_key: "name",
        field_type: "text",
        is_required: true,
        label: "Name",
      }),
      makeField({
        field_key: "email",
        field_type: "email",
        is_required: true,
        label: "Email",
      }),
      makeField({
        field_key: "score",
        field_type: "integer",
        label: "Score",
        validation_rules: { min: 0 },
      }),
    ];
    const values = { name: "", email: "bad", score: "-5" };
    const errors = validateAllFields(fields, values);
    expect(Object.keys(errors)).toHaveLength(3);
    expect(errors.name).toBe("Name is required");
    expect(errors.email).toBe("Please enter a valid email address");
    expect(errors.score).toBe("Score must be at least 0");
  });

  it("does not include non-hidden optional empty fields in errors", () => {
    const fields = [
      makeField({
        field_key: "bio",
        field_type: "textarea",
        is_required: false,
      }),
      makeField({
        field_key: "website",
        field_type: "url",
        is_required: false,
      }),
    ];
    const values = { bio: "", website: "" };
    expect(validateAllFields(fields, values)).toEqual({});
  });

  it("validates all visible required fields even when some pass", () => {
    const fields = [
      makeField({
        field_key: "first_name",
        field_type: "text",
        is_required: true,
        label: "First Name",
      }),
      makeField({
        field_key: "last_name",
        field_type: "text",
        is_required: true,
        label: "Last Name",
      }),
      makeField({
        field_key: "email",
        field_type: "email",
        is_required: true,
        label: "Email",
      }),
    ];
    const values = { first_name: "Alice", last_name: "", email: "" };
    const errors = validateAllFields(fields, values);
    expect(errors).toEqual({
      last_name: "Last Name is required",
      email: "Email is required",
    });
    expect(errors).not.toHaveProperty("first_name");
  });
});
