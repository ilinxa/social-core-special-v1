"use client";

import { useState, useMemo, useCallback } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FieldRenderer } from "./FieldRenderer";
import { AddFieldPanel, EditFieldPanel } from "./FieldConfigPanel";
import { validateAllFields } from "@/features/forms/utils/field-validation";
import type { FormField, CreateFieldInput, UpdateFieldInput } from "@/types/forms";

// =============================================================================
// TYPES
// =============================================================================

export type FormBuilderMode = "design" | "preview" | "fill" | "view";

export type FormBuilderProps = {
  fields: FormField[];
  mode: FormBuilderMode;
  /** Current form data (for fill/view modes). */
  values?: Record<string, unknown>;
  /** Validation errors keyed by field_key. */
  errors?: Record<string, string>;
  /** Called on value change in fill mode. */
  onValuesChange?: (values: Record<string, unknown>) => void;
  /** Called on submit in fill mode. */
  onSubmit?: (values: Record<string, unknown>) => void;
  /** Design mode callbacks. */
  onAddField?: (data: CreateFieldInput) => void;
  onUpdateField?: (fieldId: string, data: UpdateFieldInput) => void;
  onDeleteField?: (fieldId: string) => void;
  onReorderFields?: (fields: { field_id: string; order: number }[]) => void;
  /** Loading state for design mode operations. */
  isFieldLoading?: boolean;
  /** Submit button label (fill mode). */
  submitLabel?: string;
  /** Whether submit is disabled. */
  submitDisabled?: boolean;
};

// =============================================================================
// STEP NAVIGATION
// =============================================================================

function StepNavigation({
  steps,
  currentStep,
  onStepChange,
}: {
  steps: string[];
  currentStep: string;
  onStepChange: (step: string) => void;
}) {
  return (
    <Tabs value={currentStep} onValueChange={onStepChange}>
      <TabsList>
        {steps.map((step) => (
          <TabsTrigger key={step} value={step}>
            {step}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
}

// =============================================================================
// SECTION WRAPPER
// =============================================================================

function SectionWrapper({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">{title}</h3>
      <div className="space-y-4">{children}</div>
    </div>
  );
}

// =============================================================================
// FORM BUILDER
// =============================================================================

export function FormBuilder({
  fields,
  mode,
  values: externalValues,
  errors,
  onValuesChange,
  onSubmit,
  onAddField,
  onUpdateField,
  onDeleteField,
  onReorderFields,
  isFieldLoading,
  submitLabel = "Submit",
  submitDisabled,
}: FormBuilderProps) {
  const [internalValues, setInternalValues] = useState<Record<string, unknown>>(
    externalValues ?? {},
  );
  const [editingFieldId, setEditingFieldId] = useState<string | null>(null);
  const [deleteFieldId, setDeleteFieldId] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

  const values = externalValues ?? internalValues;

  // Sort fields by order
  const sortedFields = useMemo(
    () => [...fields].sort((a, b) => a.order - b.order),
    [fields],
  );

  // Extract unique steps
  const steps = useMemo(() => {
    const unique = new Set(
      sortedFields
        .map((f) => f.step_tag)
        .filter(Boolean),
    );
    return Array.from(unique);
  }, [sortedFields]);

  const [currentStep, setCurrentStep] = useState(steps[0] ?? "");

  // Check whether a field should be hidden based on step tab
  const isFieldHidden = useCallback(
    (field: FormField) => {
      if (steps.length === 0) return false;
      if (!currentStep) return false;
      return !!field.step_tag && field.step_tag !== currentStep;
    },
    [steps, currentStep],
  );

  // Group ALL fields by section (not filtered — hidden via CSS)
  const sections = useMemo(() => {
    const grouped = new Map<string, FormField[]>();
    for (const field of sortedFields) {
      const key = field.section_tag || "__default__";
      const arr = grouped.get(key) ?? [];
      arr.push(field);
      grouped.set(key, arr);
    }
    return grouped;
  }, [sortedFields]);

  const handleFieldChange = useCallback(
    (fieldKey: string, value: unknown) => {
      const next = { ...values, [fieldKey]: value };
      setInternalValues(next);
      onValuesChange?.(next);
      // Clear validation error for this field on change
      if (validationErrors[fieldKey]) {
        setValidationErrors((prev) => {
          const next = { ...prev };
          delete next[fieldKey];
          return next;
        });
      }
    },
    [values, onValuesChange, validationErrors],
  );

  const handleSubmit = useCallback(() => {
    // Validate all fields (across all tabs) before submitting
    const fieldErrors = validateAllFields(sortedFields, values);
    if (Object.keys(fieldErrors).length > 0) {
      setValidationErrors(fieldErrors);
      // Navigate to the first tab that has an error
      if (steps.length > 0) {
        const errorKeys = new Set(Object.keys(fieldErrors));
        const firstErrorField = sortedFields.find(
          (f) => errorKeys.has(f.field_key) && f.step_tag,
        );
        if (firstErrorField?.step_tag) {
          setCurrentStep(firstErrorField.step_tag);
        }
      }
      return;
    }
    setValidationErrors({});
    onSubmit?.(values);
  }, [onSubmit, values, sortedFields, steps]);

  const nextOrder = sortedFields.length > 0
    ? Math.max(...sortedFields.map((f) => f.order)) + 1
    : 0;

  const isReadonly = mode === "view" || mode === "preview";

  function handleMoveField(fieldId: string, direction: "up" | "down") {
    const idx = sortedFields.findIndex((f) => f.id === fieldId);
    if (idx < 0) return;
    const swapIdx = direction === "up" ? idx - 1 : idx + 1;
    if (swapIdx < 0 || swapIdx >= sortedFields.length) return;

    const reordered = sortedFields.map((f, i) => {
      if (i === idx) return { field_id: f.id, order: sortedFields[swapIdx].order };
      if (i === swapIdx) return { field_id: f.id, order: sortedFields[idx].order };
      return { field_id: f.id, order: f.order };
    });
    onReorderFields?.(reordered);
  }

  return (
    <div className="space-y-6">
      {/* Step navigation */}
      {steps.length > 1 && (
        <StepNavigation
          steps={steps}
          currentStep={currentStep}
          onStepChange={setCurrentStep}
        />
      )}

      {/* Fields */}
      {Array.from(sections.entries()).map(([sectionKey, sectionFields]) => {
        const content = (
          <div key={sectionKey} className="space-y-4">
            {sectionFields.map((field, fieldIdx) => (
              <div key={field.id} className={isFieldHidden(field) ? "hidden" : undefined}>
                {mode === "design" && editingFieldId === field.id ? (
                  <EditFieldPanel
                    field={field}
                    onUpdate={(data) => {
                      onUpdateField?.(field.id, data as UpdateFieldInput);
                      setEditingFieldId(null);
                    }}
                    onDelete={() => {
                      setDeleteFieldId(field.id);
                      setEditingFieldId(null);
                    }}
                    isLoading={isFieldLoading}
                  />
                ) : (
                  <div
                    className={
                      mode === "design"
                        ? "flex items-start gap-2"
                        : undefined
                    }
                  >
                    {mode === "design" && onReorderFields && (
                      <div className="flex shrink-0 flex-col gap-0.5 pt-3">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          disabled={fieldIdx === 0 || isFieldLoading}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleMoveField(field.id, "up");
                          }}
                          aria-label="Move field up"
                        >
                          <ChevronUp className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-6 w-6"
                          disabled={fieldIdx === sectionFields.length - 1 || isFieldLoading}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleMoveField(field.id, "down");
                          }}
                          aria-label="Move field down"
                        >
                          <ChevronDown className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                    <div
                      className={
                        mode === "design"
                          ? "min-w-0 flex-1 cursor-pointer rounded-lg border p-3 transition-colors hover:border-primary"
                          : undefined
                      }
                      onClick={
                        mode === "design"
                          ? () => setEditingFieldId(field.id)
                          : undefined
                      }
                    >
                      <FieldRenderer
                        field={field}
                        value={values[field.field_key]}
                        onChange={handleFieldChange}
                        disabled={isReadonly}
                        errors={{ ...validationErrors, ...errors }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        );

        if (sectionKey !== "__default__") {
          return (
            <SectionWrapper key={sectionKey} title={sectionKey}>
              {content}
            </SectionWrapper>
          );
        }
        return content;
      })}

      {/* Design mode: add field */}
      {mode === "design" && onAddField && (
        <AddFieldPanel
          onAdd={onAddField}
          nextOrder={nextOrder}
          isLoading={isFieldLoading}
        />
      )}

      {/* Fill mode: submit button */}
      {mode === "fill" && onSubmit && (
        <div className="flex justify-end pt-4">
          <Button onClick={handleSubmit} disabled={submitDisabled}>
            {submitLabel}
          </Button>
        </div>
      )}

      {/* Delete field confirmation dialog */}
      <Dialog
        open={deleteFieldId !== null}
        onOpenChange={(open) => { if (!open) setDeleteFieldId(null); }}
      >
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>Delete Field</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete this field? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteFieldId(null)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (deleteFieldId) {
                  onDeleteField?.(deleteFieldId);
                  setDeleteFieldId(null);
                }
              }}
              disabled={isFieldLoading}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
