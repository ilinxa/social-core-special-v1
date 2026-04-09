/**
 * Block Content Editor
 * =====================
 * Schema-driven form for editing a block placement's draft_content.
 * Reads fields from block.template.schema, renders via CmsFieldRenderer.
 * Auto-saves draft content with debounce.
 */

"use client";

import { useCallback, useRef, useState } from "react";
import { AlertTriangle, Save } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { useUpdateDraftContent } from "@/features/cms/hooks/use-cms-mutations";
import { CmsFieldRenderer } from "@/features/cms/components/fields/CmsFieldRenderer";
import { DRAFT_AUTO_SAVE_DEBOUNCE_MS } from "@/features/cms/constants/cms-constants";
import type {
  CmsApiContext,
  CmsBlockPlacement,
  CmsPublishError,
  CmsSchemaField,
} from "@/features/cms/types";

type BlockContentEditorProps = {
  context: CmsApiContext;
  block: CmsBlockPlacement;
  publishErrors?: CmsPublishError[];
};

type SaveStatus = "idle" | "saving" | "saved" | "error";

export function BlockContentEditor({
  context,
  block,
  publishErrors,
}: BlockContentEditorProps) {
  const fields = block.template.schema?.fields ?? [];
  // Key-based reset: parent should render <BlockContentEditor key={block.id} />
  const [content, setContent] = useState<Record<string, unknown>>(
    block.draft_content ?? {},
  );
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("idle");
  const updateMutation = useUpdateDraftContent(context, block.id);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Schema version mismatch warning
  const schemaMismatch =
    block.schema_version_validated < block.template.schema_version;

  // Build error map: field_key → message
  const errorMap = new Map<string, string>();
  if (publishErrors) {
    for (const err of publishErrors) {
      errorMap.set(err.field_key, err.message);
    }
  }

  const debouncedSave = useCallback(
    (newContent: Record<string, unknown>) => {
      if (saveTimerRef.current) {
        clearTimeout(saveTimerRef.current);
      }
      saveTimerRef.current = setTimeout(() => {
        setSaveStatus("saving");
        updateMutation.mutate(
          { draft_content: newContent },
          {
            onSuccess: () => setSaveStatus("saved"),
            onError: () => setSaveStatus("error"),
          },
        );
      }, DRAFT_AUTO_SAVE_DEBOUNCE_MS);
    },
    [updateMutation],
  );

  function handleFieldChange(fieldKey: string, value: unknown) {
    const next = { ...content, [fieldKey]: value };
    setContent(next);
    setSaveStatus("idle");
    debouncedSave(next);
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-semibold">
            {block.label || block.template.display_name}
          </h3>
          <p className="text-xs text-muted-foreground">
            Template: {block.template.slug} (v{block.template.schema_version})
          </p>
        </div>
        <div aria-live="polite">
          <SaveStatusIndicator status={saveStatus} />
        </div>
      </div>

      {/* Schema mismatch warning */}
      {schemaMismatch && (
        <div className="flex items-center gap-2 rounded-lg border border-yellow-300 bg-yellow-50 px-4 py-3 text-sm text-yellow-800">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>
            The template schema has been updated (v
            {block.schema_version_validated} &rarr; v
            {block.template.schema_version}). Content may need adjustment.
          </span>
        </div>
      )}

      {/* Field list */}
      {fields.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          This block has no fields defined.
        </p>
      ) : (
        <div className="space-y-5">
          {fields.map((field: CmsSchemaField) => (
            <CmsFieldRenderer
              key={field.key}
              field={field}
              value={content[field.key] ?? null}
              onChange={(value) => handleFieldChange(field.key, value)}
              error={errorMap.get(field.key)}
              context={context}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function SaveStatusIndicator({ status }: { status: SaveStatus }) {
  switch (status) {
    case "saving":
      return (
        <Badge variant="outline" className="gap-1 text-xs">
          <Save className="h-3 w-3 animate-pulse" />
          Saving...
        </Badge>
      );
    case "saved":
      return (
        <Badge variant="secondary" className="gap-1 text-xs">
          <Save className="h-3 w-3" />
          Saved
        </Badge>
      );
    case "error":
      return (
        <Badge variant="destructive" className="gap-1 text-xs">
          Error saving
        </Badge>
      );
    default:
      return null;
  }
}
