import type { FieldType } from "@/types/forms";

export type FieldCategory =
  | "text"
  | "choice"
  | "numeric"
  | "boolean"
  | "temporal"
  | "file"
  | "complex";

export type FieldTypeConfig = {
  label: string;
  category: FieldCategory;
  description: string;
  indexable: boolean;
};

export const FIELD_TYPE_CONFIG: Record<FieldType, FieldTypeConfig> = {
  // Text
  text: { label: "Text", category: "text", description: "Single-line text input", indexable: true },
  textarea: { label: "Textarea", category: "text", description: "Multi-line text input", indexable: true },
  email: { label: "Email", category: "text", description: "Email address input", indexable: true },
  url: { label: "URL", category: "text", description: "URL input", indexable: true },
  phone: { label: "Phone", category: "text", description: "Phone number input", indexable: true },

  // Numeric
  integer: { label: "Integer", category: "numeric", description: "Whole number input", indexable: true },
  decimal: { label: "Decimal", category: "numeric", description: "Decimal number input", indexable: true },
  currency: { label: "Currency", category: "numeric", description: "Currency amount input", indexable: true },
  rating: { label: "Rating", category: "numeric", description: "Star rating selector", indexable: true },

  // Boolean
  boolean: { label: "Boolean", category: "boolean", description: "Yes/No toggle", indexable: true },
  checkbox: { label: "Checkbox", category: "boolean", description: "Single checkbox", indexable: true },

  // Date/Time
  date: { label: "Date", category: "temporal", description: "Date picker", indexable: true },
  datetime: { label: "Date & Time", category: "temporal", description: "Date and time picker", indexable: true },
  time: { label: "Time", category: "temporal", description: "Time picker", indexable: true },

  // Selection
  select: { label: "Select", category: "choice", description: "Dropdown single select", indexable: true },
  radio: { label: "Radio", category: "choice", description: "Radio button group", indexable: true },
  multiselect: { label: "Multi-select", category: "choice", description: "Dropdown multi-select", indexable: false },
  checkbox_group: { label: "Checkbox Group", category: "choice", description: "Multiple checkboxes", indexable: false },

  // File
  file: { label: "File", category: "file", description: "File upload", indexable: false },
  image: { label: "Image", category: "file", description: "Image upload", indexable: false },

  // Complex
  location: { label: "Location", category: "complex", description: "Location picker", indexable: false },
  repeatable: { label: "Repeatable", category: "complex", description: "Repeatable field group", indexable: false },
};

export const FIELD_CATEGORIES: { value: FieldCategory; label: string }[] = [
  { value: "text", label: "Text" },
  { value: "choice", label: "Choice" },
  { value: "numeric", label: "Numeric" },
  { value: "boolean", label: "Boolean" },
  { value: "temporal", label: "Date & Time" },
  { value: "file", label: "File" },
  { value: "complex", label: "Complex" },
];
