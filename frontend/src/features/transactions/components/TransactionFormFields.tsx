"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { FileUp, ImagePlus, Trash2, FileIcon } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";
import { uploadFormFileApi } from "@/features/forms/api/forms-api";
import type { FormTemplateForTransaction } from "@/features/transactions/api/transactions-api";

// =============================================================================
// TYPES
// =============================================================================

type FieldData = FormTemplateForTransaction["fields"][number];

// =============================================================================
// MAIN FIELD RENDERER (used by both Accept and Request dialogs)
// =============================================================================

export function TransactionFormFieldInput({
  field,
  value,
  onChange,
  disabled,
}: {
  field: FieldData;
  value: unknown;
  onChange: (val: unknown) => void;
  disabled?: boolean;
}) {
  const id = `field-${field.field_key}`;

  switch (field.field_type) {
    case "textarea":
      return (
        <div className="space-y-1.5">
          <FieldLabel id={id} label={field.label} required={field.is_required} />
          <FieldDescription text={field.description} />
          <Textarea
            id={id}
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || undefined}
            disabled={disabled}
          />
        </div>
      );

    case "boolean":
    case "checkbox":
      return (
        <div className="flex items-center gap-2">
          <Checkbox
            id={id}
            checked={(value as boolean) ?? false}
            onCheckedChange={(checked) => onChange(checked === true)}
            disabled={disabled}
          />
          <Label htmlFor={id}>
            {field.label}
            {field.is_required && <span className="text-destructive"> *</span>}
          </Label>
        </div>
      );

    case "select":
      return (
        <div className="space-y-1.5">
          <FieldLabel id={id} label={field.label} required={field.is_required} />
          <FieldDescription text={field.description} />
          <select
            id={id}
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          >
            <option value="">{field.placeholder || "Select..."}</option>
            {(field.options as Array<{ value: string; label: string }>).map(
              (opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ),
            )}
          </select>
        </div>
      );

    case "integer":
    case "decimal":
    case "currency":
    case "rating":
      return (
        <div className="space-y-1.5">
          <FieldLabel id={id} label={field.label} required={field.is_required} />
          <FieldDescription text={field.description} />
          <Input
            id={id}
            type="number"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || undefined}
            disabled={disabled}
          />
        </div>
      );

    case "date":
      return (
        <div className="space-y-1.5">
          <FieldLabel id={id} label={field.label} required={field.is_required} />
          <FieldDescription text={field.description} />
          <Input
            id={id}
            type="date"
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled}
          />
        </div>
      );

    case "image":
      return (
        <div className="space-y-1.5">
          <FieldLabel id={id} label={field.label} required={field.is_required} />
          <FieldDescription text={field.description} />
          <InlineFileUpload
            variant="image"
            value={value as File | string | null}
            onChange={onChange}
            disabled={disabled}
            maxSize={(field.validation_rules?.max_file_size as number) || undefined}
          />
        </div>
      );

    case "file":
      return (
        <div className="space-y-1.5">
          <FieldLabel id={id} label={field.label} required={field.is_required} />
          <FieldDescription text={field.description} />
          <InlineFileUpload
            variant="file"
            value={value as File | string | null}
            onChange={onChange}
            disabled={disabled}
            maxSize={(field.validation_rules?.max_file_size as number) || undefined}
            allowedTypes={field.validation_rules?.allowed_types as string[] | undefined}
          />
        </div>
      );

    default:
      return (
        <div className="space-y-1.5">
          <FieldLabel id={id} label={field.label} required={field.is_required} />
          <FieldDescription text={field.description} />
          <Input
            id={id}
            type={
              field.field_type === "email"
                ? "email"
                : field.field_type === "url"
                  ? "url"
                  : field.field_type === "phone"
                    ? "tel"
                    : "text"
            }
            value={(value as string) ?? ""}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder || undefined}
            disabled={disabled}
          />
        </div>
      );
  }
}

// =============================================================================
// HELPER: Upload all File values in form data before submission
// =============================================================================

/**
 * Takes the form data and uploads any File values, replacing them with URLs.
 * Returns a new object safe to send as JSON.
 */
export async function uploadFilesInFormData(
  formData: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const result = { ...formData };

  for (const [key, value] of Object.entries(result)) {
    if (value instanceof File) {
      const url = await uploadFormFileApi(value);
      result[key] = url;
    }
  }

  return result;
}

// =============================================================================
// INTERNAL COMPONENTS
// =============================================================================

function FieldLabel({ id, label, required }: { id: string; label: string; required: boolean }) {
  return (
    <Label htmlFor={id}>
      {label}
      {required && <span className="text-destructive"> *</span>}
    </Label>
  );
}

function FieldDescription({ text }: { text: string }) {
  if (!text) return null;
  return <p className="text-xs text-muted-foreground">{text}</p>;
}

// =============================================================================
// INLINE FILE UPLOAD (compact version for transaction dialogs)
// =============================================================================

const IMAGE_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"];
const DEFAULT_MAX_SIZE = 10 * 1024 * 1024; // 10 MB

function InlineFileUpload({
  variant,
  value,
  onChange,
  disabled,
  maxSize = DEFAULT_MAX_SIZE,
  allowedTypes,
}: {
  variant: "file" | "image";
  value: File | string | null;
  onChange: (val: unknown) => void;
  disabled?: boolean;
  maxSize?: number;
  allowedTypes?: string[];
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const isImage = variant === "image";
  const acceptTypes = isImage
    ? IMAGE_TYPES.join(",")
    : allowedTypes?.join(",") ?? undefined;

  useEffect(() => {
    if (!(value instanceof File)) {
      setPreviewUrl(null);
      return;
    }
    if (isImage || value.type.startsWith("image/")) {
      const url = URL.createObjectURL(value);
      setPreviewUrl(url);
      return () => URL.revokeObjectURL(url);
    }
    setPreviewUrl(null);
  }, [value, isImage]);

  const displayUrl = previewUrl ?? (typeof value === "string" ? value : null);
  const hasFile = !!value;
  const fileName =
    value instanceof File
      ? value.name
      : typeof value === "string"
        ? value.split("/").pop()
        : null;

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      if (file.size > maxSize) {
        toast.error(
          `File must be smaller than ${Math.round(maxSize / 1024 / 1024)} MB`,
        );
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      if (isImage && !file.type.startsWith("image/")) {
        toast.error("Please select an image file (JPEG, PNG, GIF, or WebP)");
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      if (allowedTypes && !allowedTypes.includes(file.type)) {
        toast.error(`File type ${file.type} is not allowed`);
        if (inputRef.current) inputRef.current.value = "";
        return;
      }

      onChange(file);
      if (inputRef.current) inputRef.current.value = "";
    },
    [onChange, maxSize, isImage, allowedTypes],
  );

  const handleRemove = useCallback(() => {
    onChange(null);
  }, [onChange]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (disabled) return;

      const file = e.dataTransfer.files[0];
      if (!file) return;

      if (file.size > maxSize) {
        toast.error(
          `File must be smaller than ${Math.round(maxSize / 1024 / 1024)} MB`,
        );
        return;
      }

      if (isImage && !file.type.startsWith("image/")) {
        toast.error("Please select an image file");
        return;
      }

      onChange(file);
    },
    [disabled, maxSize, isImage, onChange],
  );

  if (isImage) {
    return (
      <div>
        <div
          className={cn(
            "group relative flex items-center justify-center overflow-hidden rounded-lg border-2 border-dashed transition-colors",
            hasFile
              ? "border-transparent"
              : "border-muted-foreground/25 hover:border-primary/50",
            "aspect-[16/9] w-full max-w-xs",
            disabled && "pointer-events-none opacity-50",
          )}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          {displayUrl ? (
            <>
              <img
                src={displayUrl}
                alt="Uploaded"
                className="h-full w-full object-cover"
              />
              {!disabled && (
                <div className="absolute inset-0 flex items-center justify-center gap-2 bg-black/50 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => inputRef.current?.click()}
                  >
                    Change
                  </Button>
                  <Button
                    type="button"
                    variant="destructive"
                    size="sm"
                    onClick={handleRemove}
                  >
                    <Trash2 className="mr-1 h-3.5 w-3.5" />
                    Remove
                  </Button>
                </div>
              )}
            </>
          ) : (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              disabled={disabled}
              className="flex h-full w-full flex-col items-center justify-center gap-2 p-4 text-muted-foreground transition-colors hover:text-foreground"
            >
              <ImagePlus className="h-6 w-6" />
              <span className="text-xs font-medium">
                Click or drag to upload
              </span>
              <span className="text-[10px] opacity-60">
                JPEG, PNG, GIF or WebP
              </span>
            </button>
          )}
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={acceptTypes}
          onChange={handleFileSelect}
          disabled={disabled}
          className="hidden"
          aria-label="Upload image"
        />
      </div>
    );
  }

  return (
    <div>
      <div
        className={cn(
          "group relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-4 transition-colors",
          hasFile
            ? "border-primary/30 bg-primary/5"
            : "border-muted-foreground/25 hover:border-primary/50",
          disabled && "pointer-events-none opacity-50",
        )}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {hasFile ? (
          <div className="flex w-full items-center gap-3">
            <FileIcon className="h-6 w-6 shrink-0 text-primary" />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{fileName}</p>
              {value instanceof File && (
                <p className="text-xs text-muted-foreground">
                  {formatFileSize(value.size)}
                </p>
              )}
            </div>
            {!disabled && (
              <div className="flex gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => inputRef.current?.click()}
                >
                  Change
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleRemove}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            )}
          </div>
        ) : (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={disabled}
            className="flex flex-col items-center gap-1.5 text-muted-foreground transition-colors hover:text-foreground"
          >
            <FileUp className="h-6 w-6" />
            <span className="text-xs font-medium">Click or drag to upload</span>
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={acceptTypes}
        onChange={handleFileSelect}
        disabled={disabled}
        className="hidden"
        aria-label="Upload file"
      />
    </div>
  );
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
