/**
 * CMS Field Renderer
 * ===================
 * Renders a single field from a CMS block template schema.
 * Delegates to form builder FieldRenderer for 11 common types.
 * Uses CMS-specific components for 7 custom types.
 *
 * Backend: apps.cms.constants.CMS_FIELD_TYPES (18 types)
 */

"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import type { CmsApiContext, CmsSchemaField } from "@/features/cms/types";
import { TipTapEditor } from "./TipTapEditor";
import { MediaPickerDialog } from "./MediaPickerDialog";
import { RepeaterFieldEditor } from "./RepeaterFieldEditor";

type CmsFieldRendererProps = {
  field: CmsSchemaField;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled?: boolean;
  error?: string;
  context?: CmsApiContext;
};

export function CmsFieldRenderer({
  field,
  value,
  onChange,
  disabled = false,
  error,
  context,
}: CmsFieldRendererProps) {
  const label = field.label ?? field.key;
  const fieldId = `cms-field-${field.key}`;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Label htmlFor={fieldId}>
          {label}
          {field.required && <span className="ml-0.5 text-destructive">*</span>}
        </Label>
      </div>
      {renderFieldControl(field, value, onChange, disabled, fieldId, context)}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  );
}

function renderFieldControl(
  field: CmsSchemaField,
  value: unknown,
  onChange: (value: unknown) => void,
  disabled: boolean,
  fieldId: string,
  context?: CmsApiContext,
) {
  const strValue = typeof value === "string" ? value : "";
  const numValue = typeof value === "number" ? value : undefined;

  switch (field.type) {
    // ---- Form builder compatible types ----
    case "text":
      return (
        <Input
          id={fieldId}
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          maxLength={field.max_length}
          placeholder={`Enter ${field.label ?? field.key}`}
        />
      );

    case "textarea":
      return (
        <Textarea
          id={fieldId}
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          maxLength={field.max_length}
          rows={4}
          placeholder={`Enter ${field.label ?? field.key}`}
        />
      );

    case "richtext":
      return (
        <TipTapEditor
          content={strValue}
          onChange={(html: string) => onChange(html)}
          disabled={disabled}
          placeholder={`Enter ${field.label ?? field.key}`}
        />
      );

    case "number":
      return (
        <Input
          id={fieldId}
          type="number"
          value={numValue ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            onChange(v === "" ? null : parseFloat(v));
          }}
          disabled={disabled}
          min={field.min}
          max={field.max}
        />
      );

    case "boolean":
      return (
        <div className="flex items-center gap-2">
          <Switch
            id={fieldId}
            checked={value === true}
            onCheckedChange={(checked) => onChange(checked)}
            disabled={disabled}
          />
          <Label htmlFor={fieldId} className="text-sm text-muted-foreground">
            {value === true ? "Yes" : "No"}
          </Label>
        </div>
      );

    case "url":
      return (
        <Input
          id={fieldId}
          type="url"
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="https://example.com"
        />
      );

    case "email":
      return (
        <Input
          id={fieldId}
          type="email"
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="email@example.com"
        />
      );

    case "date":
      return (
        <Input
          id={fieldId}
          type="date"
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
      );

    case "datetime":
      return (
        <Input
          id={fieldId}
          type="datetime-local"
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
        />
      );

    case "select":
      return (
        <Select
          value={strValue}
          onValueChange={(v) => onChange(v)}
          disabled={disabled}
        >
          <SelectTrigger id={fieldId}>
            <SelectValue placeholder="Select..." />
          </SelectTrigger>
          <SelectContent>
            {(field.choices ?? []).map((choice) => (
              <SelectItem key={choice} value={choice}>
                {choice}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      );

    case "multiselect": {
      const selectedValues = Array.isArray(value) ? (value as string[]) : [];
      return (
        <div className="space-y-2">
          {(field.choices ?? []).map((choice) => (
            <div key={choice} className="flex items-center gap-2">
              <Checkbox
                id={`${fieldId}-${choice}`}
                checked={selectedValues.includes(choice)}
                onCheckedChange={(checked) => {
                  const next = checked
                    ? [...selectedValues, choice]
                    : selectedValues.filter((v) => v !== choice);
                  onChange(next);
                }}
                disabled={disabled}
              />
              <Label
                htmlFor={`${fieldId}-${choice}`}
                className="text-sm font-normal"
              >
                {choice}
              </Label>
            </div>
          ))}
        </div>
      );
    }

    // ---- CMS-specific types (Phase 3 full implementations) ----

    case "media":
      return (
        <MediaFieldControl
          value={value}
          onChange={onChange}
          disabled={disabled}
          context={context}
        />
      );

    case "color":
      return (
        <Input
          id={fieldId}
          type="color"
          value={strValue || "#000000"}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          className="h-10 w-20"
        />
      );

    case "icon":
      return (
        <Input
          id={fieldId}
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Icon name (e.g., lucide:star)"
        />
      );

    case "list": {
      const items = Array.isArray(value) ? (value as string[]) : [];
      return (
        <div className="space-y-2">
          {items.map((item, i) => (
            <div key={i} className="flex gap-2">
              <Input
                value={item}
                onChange={(e) => {
                  const next = [...items];
                  next[i] = e.target.value;
                  onChange(next);
                }}
                disabled={disabled}
              />
              <button
                type="button"
                className="text-sm text-destructive hover:underline"
                onClick={() => onChange(items.filter((_, idx) => idx !== i))}
                disabled={disabled}
              >
                Remove
              </button>
            </div>
          ))}
          <button
            type="button"
            className="text-sm text-primary hover:underline"
            onClick={() => onChange([...items, ""])}
            disabled={disabled}
          >
            + Add item
          </button>
        </div>
      );
    }

    case "repeater":
      return (
        <RepeaterFieldEditor
          field={field}
          value={Array.isArray(value) ? value : []}
          onChange={(items) => onChange(items)}
          disabled={disabled}
          context={context}
        />
      );

    case "relation":
      return (
        <Input
          id={fieldId}
          value={strValue}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          placeholder="Entity UUID"
        />
      );

    case "json":
      return (
        <Textarea
          id={fieldId}
          value={typeof value === "string" ? value : JSON.stringify(value, null, 2)}
          onChange={(e) => {
            try {
              onChange(JSON.parse(e.target.value));
            } catch {
              onChange(e.target.value);
            }
          }}
          disabled={disabled}
          rows={6}
          className="font-mono text-sm"
          placeholder="{}"
        />
      );

    default:
      return (
        <p className="text-sm text-muted-foreground">
          Unsupported field type: {field.type}
        </p>
      );
  }
}

/** Media field with picker dialog (needs own state for dialog open). */
function MediaFieldControl({
  value,
  onChange,
  disabled,
  context,
}: {
  value: unknown;
  onChange: (value: unknown) => void;
  disabled: boolean;
  context?: CmsApiContext;
}) {
  const [pickerOpen, setPickerOpen] = useState(false);
  const mediaVal = value as Record<string, unknown> | null;
  const mediaId = mediaVal?.media_id ? String(mediaVal.media_id) : "";
  const mediaName = mediaVal?.filename ? String(mediaVal.filename) : mediaId;

  return (
    <>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setPickerOpen(true)}
          disabled={disabled || !context}
        >
          {mediaId ? "Change Media" : "Select Media"}
        </Button>
        {mediaId && (
          <span className="truncate text-sm text-muted-foreground">
            {mediaName}
          </span>
        )}
      </div>
      {context && (
        <MediaPickerDialog
          open={pickerOpen}
          onOpenChange={setPickerOpen}
          context={context}
          onSelect={(id, filename) => onChange({ media_id: id, filename })}
        />
      )}
    </>
  );
}
