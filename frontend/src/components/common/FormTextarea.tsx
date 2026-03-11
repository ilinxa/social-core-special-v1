"use client";

import { forwardRef } from "react";

import type { FieldError } from "react-hook-form";

import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface FormTextareaProps extends React.ComponentProps<typeof Textarea> {
  label: string;
  error?: FieldError;
  description?: string;
}

export const FormTextarea = forwardRef<HTMLTextAreaElement, FormTextareaProps>(
  ({ label, error, description, id, className, ...props }, ref) => {
    const fieldId = id ?? props.name;

    return (
      <div className={cn("space-y-2", className)}>
        <Label htmlFor={fieldId}>{label}</Label>
        <Textarea
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

FormTextarea.displayName = "FormTextarea";
