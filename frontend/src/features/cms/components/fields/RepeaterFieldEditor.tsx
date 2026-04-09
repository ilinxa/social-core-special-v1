/**
 * Repeater Field Editor
 * ======================
 * Renders a list of item groups, each containing sub-fields.
 * Uses CmsFieldRenderer recursively (max 1 level — backend enforces no nested repeaters).
 */

"use client";

import { Minus, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import type { CmsApiContext, CmsSchemaField } from "@/features/cms/types";

// Lazy import to avoid circular dependency
import { CmsFieldRenderer } from "./CmsFieldRenderer";

type RepeaterFieldEditorProps = {
  field: CmsSchemaField;
  value: unknown[];
  onChange: (items: unknown[]) => void;
  disabled?: boolean;
  context?: CmsApiContext;
};

export function RepeaterFieldEditor({
  field,
  value,
  onChange,
  disabled = false,
  context,
}: RepeaterFieldEditorProps) {
  const items = Array.isArray(value) ? value : [];
  const subFields = field.item_schema ?? [];
  const minItems = field.min_items ?? 0;
  const maxItems = field.max_items ?? Infinity;

  function addItem() {
    if (items.length >= maxItems) return;
    const emptyItem: Record<string, unknown> = {};
    for (const sf of subFields) {
      emptyItem[sf.key] = null;
    }
    onChange([...items, emptyItem]);
  }

  function removeItem(index: number) {
    if (items.length <= minItems) return;
    onChange(items.filter((_, i) => i !== index));
  }

  function updateItem(index: number, fieldKey: string, fieldValue: unknown) {
    const next = [...items];
    const item = { ...(next[index] as Record<string, unknown>) };
    item[fieldKey] = fieldValue;
    next[index] = item;
    onChange(next);
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div key={index} className="rounded-lg border p-4">
          <div className="mb-3 flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground">
              Item {index + 1}
            </span>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={() => removeItem(index)}
              disabled={disabled || items.length <= minItems}
              title="Remove item"
            >
              <Minus className="h-3.5 w-3.5" />
            </Button>
          </div>
          <div className="space-y-4">
            {subFields.map((sf) => (
              <CmsFieldRenderer
                key={sf.key}
                field={sf}
                value={
                  (item as Record<string, unknown>)?.[sf.key] ?? null
                }
                onChange={(v) => updateItem(index, sf.key, v)}
                disabled={disabled}
                context={context}
              />
            ))}
          </div>
        </div>
      ))}

      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={addItem}
        disabled={disabled || items.length >= maxItems}
      >
        <Plus className="mr-1 h-3.5 w-3.5" />
        Add Item
        {maxItems < Infinity && (
          <span className="ml-1 text-muted-foreground">
            ({items.length}/{maxItems})
          </span>
        )}
      </Button>
    </div>
  );
}
