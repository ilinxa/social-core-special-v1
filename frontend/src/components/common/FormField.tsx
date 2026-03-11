"use client";

import { forwardRef } from "react";

import type { FieldError } from "react-hook-form";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

interface FormFieldProps extends React.ComponentProps<typeof Input> {
  label: string;
  error?: FieldError;
  description?: string;
}

export const FormField = forwardRef<HTMLInputElement, FormFieldProps>(
  ({ label, error, description, id, className, ...props }, ref) => {
    const fieldId = id ?? props.name;

    return (
      <div className={cn("space-y-2", className)}>
        <Label htmlFor={fieldId}>{label}</Label>
        <Input
          ref={ref}
          id={fieldId}
          aria-invalid={!!error}
          aria-describedby={error ? `${fieldId}-error` : undefined}
          {...props}
        />
        {error && (
          <p id={`${fieldId}-error`} className="text-destructive text-sm">
            {error.message}
          </p>
        )}
        {description && !error && <p className="text-muted-foreground text-sm">{description}</p>}
      </div>
    );
  },
);

FormField.displayName = "FormField";
