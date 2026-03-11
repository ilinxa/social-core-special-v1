"use client";

import { useCallback, useState } from "react";

import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FileUploadField } from "./FileUploadField";
import { validateFieldValue } from "@/features/forms/utils/field-validation";
import type { FormField } from "@/types/forms";

// =============================================================================
// TYPES
// =============================================================================

export type FieldRendererProps = {
  field: FormField;
  value: unknown;
  onChange: (fieldKey: string, value: unknown) => void;
  disabled?: boolean;
  errors?: Record<string, string>;
};

// =============================================================================
// OPTION HELPERS
// =============================================================================

type FieldOption = { value: string; label: string };

function getOptions(field: FormField): FieldOption[] {
  if (!Array.isArray(field.options)) return [];
  return field.options.map((opt) => {
    if (typeof opt === "string") return { value: opt, label: opt };
    const o = opt as Record<string, unknown>;
    return {
      value: String(o.value ?? o.label ?? ""),
      label: String(o.label ?? o.value ?? ""),
    };
  });
}

// =============================================================================
// FIELD RENDERER
// =============================================================================

export function FieldRenderer({
  field,
  value,
  onChange,
  disabled = false,
  errors,
}: FieldRendererProps) {
  if (field.is_hidden) return null;

  const externalError = errors?.[field.field_key];
  const [localError, setLocalError] = useState<string | null>(null);
  const isReadonly = disabled || field.is_readonly;

  const handleChange = useCallback(
    (v: unknown) => {
      if (localError) setLocalError(null);
      onChange(field.field_key, v);
    },
    [field.field_key, onChange, localError],
  );

  const handleBlur = useCallback(() => {
    if (isReadonly) return;
    const err = validateFieldValue(field, value);
    setLocalError(err);
  }, [field, value, isReadonly]);

  const error = externalError || localError;

  return (
    <div className="space-y-1.5">
      <Label htmlFor={field.field_key}>
        {field.label}
        {field.is_required && <span className="ml-1 text-red-500">*</span>}
      </Label>

      {field.description && (
        <p className="text-sm text-muted-foreground">{field.description}</p>
      )}

      {renderField(field, value, handleChange, isReadonly, handleBlur)}

      {error && <p className="text-sm text-red-500">{error}</p>}
    </div>
  );
}

function renderField(
  field: FormField,
  value: unknown,
  onChange: (v: unknown) => void,
  disabled: boolean,
  onBlur: () => void,
) {
  const rules = field.validation_rules ?? {};

  switch (field.field_type) {
    // ---- Text-like fields ----
    case "text":
      return (
        <Input
          id={field.field_key}
          type="text"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          placeholder={field.placeholder || undefined}
          disabled={disabled}
          maxLength={rules.max_length as number | undefined}
        />
      );

    case "email":
      return (
        <Input
          id={field.field_key}
          type="email"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          placeholder={field.placeholder || "email@example.com"}
          disabled={disabled}
        />
      );

    case "url":
      return (
        <Input
          id={field.field_key}
          type="url"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          placeholder={field.placeholder || "https://"}
          disabled={disabled}
        />
      );

    case "phone":
      return (
        <Input
          id={field.field_key}
          type="tel"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          placeholder={field.placeholder || "+1 (555) 000-0000"}
          disabled={disabled}
        />
      );

    case "textarea":
      return (
        <Textarea
          id={field.field_key}
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          placeholder={field.placeholder || undefined}
          disabled={disabled}
          rows={4}
          maxLength={rules.max_length as number | undefined}
        />
      );

    // ---- Numeric fields ----
    case "integer":
      return (
        <Input
          id={field.field_key}
          type="number"
          value={value != null ? String(value) : ""}
          onChange={(e) => onChange(e.target.value ? parseInt(e.target.value, 10) : null)}
          onBlur={onBlur}
          placeholder={field.placeholder || undefined}
          disabled={disabled}
          step="1"
          min={rules.min as number | undefined}
          max={rules.max as number | undefined}
        />
      );

    case "decimal":
      return (
        <Input
          id={field.field_key}
          type="number"
          value={value != null ? String(value) : ""}
          onChange={(e) => onChange(e.target.value ? parseFloat(e.target.value) : null)}
          onBlur={onBlur}
          placeholder={field.placeholder || undefined}
          disabled={disabled}
          step="0.01"
          min={rules.min as number | undefined}
          max={rules.max as number | undefined}
        />
      );

    case "currency": {
      const symbol = (rules.currency_symbol as string) || "$";
      return (
        <div className="relative">
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
            {symbol}
          </span>
          <Input
            id={field.field_key}
            type="number"
            className="pl-7"
            value={value != null ? String(value) : ""}
            onChange={(e) => onChange(e.target.value ? parseFloat(e.target.value) : null)}
            onBlur={onBlur}
            placeholder={field.placeholder || "0.00"}
            disabled={disabled}
            step="0.01"
            min={rules.min as number | undefined}
            max={rules.max as number | undefined}
          />
        </div>
      );
    }

    case "rating": {
      const max = (rules.max as number) || 5;
      const current = typeof value === "number" ? value : 0;
      return (
        <div className="flex gap-1" role="radiogroup" aria-label={field.label}>
          {Array.from({ length: max }, (_, i) => (
            <button
              key={i + 1}
              type="button"
              role="radio"
              aria-checked={i + 1 <= current}
              className={`text-2xl ${i + 1 <= current ? "text-yellow-500" : "text-gray-300"}`}
              onClick={() => !disabled && onChange(i + 1)}
              disabled={disabled}
            >
              ★
            </button>
          ))}
        </div>
      );
    }

    // ---- Boolean fields ----
    case "boolean":
      return (
        <div className="flex items-center gap-2">
          <Switch
            id={field.field_key}
            checked={Boolean(value)}
            onCheckedChange={(checked) => onChange(checked)}
            disabled={disabled}
          />
          <Label htmlFor={field.field_key} className="font-normal">
            {field.placeholder || "Yes"}
          </Label>
        </div>
      );

    case "checkbox":
      return (
        <div className="flex items-center gap-2">
          <input
            id={field.field_key}
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => onChange(e.target.checked)}
            disabled={disabled}
            className="h-4 w-4 rounded border-gray-300"
          />
          <Label htmlFor={field.field_key} className="font-normal">
            {field.placeholder || field.label}
          </Label>
        </div>
      );

    // ---- Date/Time fields ----
    case "date":
      return (
        <Input
          id={field.field_key}
          type="date"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          disabled={disabled}
          min={rules.min_date as string | undefined}
          max={rules.max_date as string | undefined}
        />
      );

    case "datetime":
      return (
        <Input
          id={field.field_key}
          type="datetime-local"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          disabled={disabled}
        />
      );

    case "time":
      return (
        <Input
          id={field.field_key}
          type="time"
          value={String(value ?? "")}
          onChange={(e) => onChange(e.target.value)}
          onBlur={onBlur}
          disabled={disabled}
        />
      );

    // ---- Selection fields ----
    case "select":
      return (
        <Select
          value={String(value ?? "")}
          onValueChange={onChange}
          disabled={disabled}
        >
          <SelectTrigger id={field.field_key}>
            <SelectValue placeholder={field.placeholder || "Select..."} />
          </SelectTrigger>
          <SelectContent>
            {getOptions(field).map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );

    case "radio": {
      const options = getOptions(field);
      return (
        <div className="space-y-2" role="radiogroup" aria-label={field.label}>
          {options.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2">
              <input
                type="radio"
                name={field.field_key}
                value={opt.value}
                checked={value === opt.value}
                onChange={() => onChange(opt.value)}
                disabled={disabled}
                className="h-4 w-4"
              />
              <span className="text-sm">{opt.label}</span>
            </label>
          ))}
        </div>
      );
    }

    case "multiselect":
    case "checkbox_group": {
      const options = getOptions(field);
      const selected = Array.isArray(value) ? (value as string[]) : [];
      return (
        <div className="space-y-2">
          {options.map((opt) => (
            <label key={opt.value} className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={selected.includes(opt.value)}
                onChange={(e) => {
                  if (disabled) return;
                  const next = e.target.checked
                    ? [...selected, opt.value]
                    : selected.filter((v) => v !== opt.value);
                  onChange(next);
                }}
                disabled={disabled}
                className="h-4 w-4 rounded border-gray-300"
              />
              <span className="text-sm">{opt.label}</span>
            </label>
          ))}
        </div>
      );
    }

    // ---- File fields ----
    case "file":
      return (
        <FileUploadField
          variant="file"
          value={value instanceof File ? value : typeof value === "string" ? value : null}
          onChange={onChange}
          disabled={disabled}
          maxSize={(rules.max_file_size as number) || undefined}
          allowedTypes={rules.allowed_types as string[] | undefined}
        />
      );

    case "image":
      return (
        <FileUploadField
          variant="image"
          value={value instanceof File ? value : typeof value === "string" ? value : null}
          onChange={onChange}
          disabled={disabled}
          maxSize={(rules.max_file_size as number) || undefined}
        />
      );

    // ---- Complex fields ----
    case "location":
      return (
        <div className="space-y-2">
          <Input
            id={field.field_key}
            placeholder="Enter location"
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            onBlur={onBlur}
            disabled={disabled}
          />
        </div>
      );

    case "repeatable":
      return (
        <p className="text-sm text-muted-foreground italic">
          Repeatable fields are not yet supported in the form builder.
        </p>
      );

    default:
      return (
        <p className="text-sm text-muted-foreground">
          Unknown field type: {field.field_type}
        </p>
      );
  }
}
