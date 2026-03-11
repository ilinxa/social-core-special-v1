"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FIELD_TYPE_CONFIG,
  FIELD_CATEGORIES,
} from "@/features/forms/constants/field-types";
import type { FormField, FieldType, CreateFieldInput } from "@/types/forms";

// =============================================================================
// ADD FIELD PANEL
// =============================================================================

type AddFieldPanelProps = {
  onAdd: (data: CreateFieldInput) => void;
  nextOrder: number;
  isLoading?: boolean;
};

export function AddFieldPanel({ onAdd, nextOrder, isLoading }: AddFieldPanelProps) {
  const [fieldKey, setFieldKey] = useState("");
  const [fieldType, setFieldType] = useState<FieldType>("text");
  const [label, setLabel] = useState("");
  const [description, setDescription] = useState("");
  const [isRequired, setIsRequired] = useState(false);

  const isValid = fieldKey.trim().length > 0 && label.trim().length > 0;

  function handleSubmit() {
    if (!isValid) return;
    onAdd({
      field_key: fieldKey.trim(),
      field_type: fieldType,
      label: label.trim(),
      description: description.trim() || undefined,
      order: nextOrder,
      is_required: isRequired,
    });
    setFieldKey("");
    setLabel("");
    setDescription("");
    setIsRequired(false);
    setFieldType("text");
  }

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <h4 className="font-medium">Add Field</h4>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="add-field-key">Field Key</Label>
          <Input
            id="add-field-key"
            value={fieldKey}
            onChange={(e) => setFieldKey(e.target.value)}
            placeholder="e.g. full_name"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="add-field-type">Field Type</Label>
          <Select value={fieldType} onValueChange={(v) => setFieldType(v as FieldType)}>
            <SelectTrigger id="add-field-type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {FIELD_CATEGORIES.map((cat) => (
                <div key={cat.value}>
                  <p className="px-2 py-1 text-xs font-semibold text-muted-foreground">
                    {cat.label}
                  </p>
                  {Object.entries(FIELD_TYPE_CONFIG)
                    .filter(([, config]) => config.category === cat.value)
                    .map(([type, config]) => (
                      <SelectItem key={type} value={type}>
                        {config.label}
                      </SelectItem>
                    ))}
                </div>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="add-field-label">Label</Label>
        <Input
          id="add-field-label"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g. Full Name"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="add-field-desc">Description</Label>
        <Textarea
          id="add-field-desc"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Help text for the field"
          rows={2}
        />
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id="add-field-required"
          checked={isRequired}
          onCheckedChange={setIsRequired}
        />
        <Label htmlFor="add-field-required">Required</Label>
      </div>

      <Button onClick={handleSubmit} disabled={!isValid || isLoading} size="sm">
        Add Field
      </Button>
    </div>
  );
}

// =============================================================================
// EDIT FIELD PANEL
// =============================================================================

type EditFieldPanelProps = {
  field: FormField;
  onUpdate: (data: Record<string, unknown>) => void;
  onDelete: () => void;
  isLoading?: boolean;
};

export function EditFieldPanel({
  field,
  onUpdate,
  onDelete,
  isLoading,
}: EditFieldPanelProps) {
  const [label, setLabel] = useState(field.label);
  const [description, setDescription] = useState(field.description);
  const [placeholder, setPlaceholder] = useState(field.placeholder);
  const [isRequired, setIsRequired] = useState(field.is_required);

  const hasChanges =
    label !== field.label ||
    description !== field.description ||
    placeholder !== field.placeholder ||
    isRequired !== field.is_required;

  function handleSave() {
    onUpdate({
      label: label.trim(),
      help_text: description.trim(),
      placeholder: placeholder.trim(),
      is_required: isRequired,
    });
  }

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium">
          Edit: {field.field_key}
          <span className="ml-2 text-sm text-muted-foreground">
            ({FIELD_TYPE_CONFIG[field.field_type]?.label ?? field.field_type})
          </span>
        </h4>
        <Button
          variant="destructive"
          size="sm"
          onClick={onDelete}
          disabled={isLoading}
        >
          Delete
        </Button>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`edit-${field.id}-label`}>Label</Label>
        <Input
          id={`edit-${field.id}-label`}
          value={label}
          onChange={(e) => setLabel(e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`edit-${field.id}-desc`}>Description</Label>
        <Textarea
          id={`edit-${field.id}-desc`}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={2}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`edit-${field.id}-placeholder`}>Placeholder</Label>
        <Input
          id={`edit-${field.id}-placeholder`}
          value={placeholder}
          onChange={(e) => setPlaceholder(e.target.value)}
        />
      </div>

      <div className="flex items-center gap-2">
        <Switch
          id={`edit-${field.id}-required`}
          checked={isRequired}
          onCheckedChange={setIsRequired}
        />
        <Label htmlFor={`edit-${field.id}-required`}>Required</Label>
      </div>

      <Button
        onClick={handleSave}
        disabled={!hasChanges || isLoading}
        size="sm"
      >
        Save Changes
      </Button>
    </div>
  );
}
