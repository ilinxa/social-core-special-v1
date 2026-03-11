"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { FormField } from "@/types/forms";

interface RequestChangesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  fields: FormField[];
  onSubmit: (message: string, requestedFields: string[]) => void;
  isLoading?: boolean;
}

export function RequestChangesDialog({
  open,
  onOpenChange,
  fields,
  onSubmit,
  isLoading = false,
}: RequestChangesDialogProps) {
  const [message, setMessage] = useState("");
  const [selectedFields, setSelectedFields] = useState<string[]>([]);

  const visibleFields = fields
    .filter((f) => !f.is_hidden)
    .sort((a, b) => a.order - b.order);

  function handleToggleField(fieldKey: string) {
    setSelectedFields((prev) =>
      prev.includes(fieldKey)
        ? prev.filter((k) => k !== fieldKey)
        : [...prev, fieldKey],
    );
  }

  function handleSubmit() {
    onSubmit(message, selectedFields);
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      setMessage("");
      setSelectedFields([]);
    }
    onOpenChange(nextOpen);
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Request Changes</DialogTitle>
          <DialogDescription>
            Explain what needs to be corrected. The submitter will be able to
            edit their response and resubmit.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Message */}
          <div className="space-y-2">
            <Label htmlFor="request-message">Message *</Label>
            <Textarea
              id="request-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Please describe what needs to be changed..."
              maxLength={2000}
              rows={4}
              disabled={isLoading}
            />
          </div>

          {/* Field selection */}
          {visibleFields.length > 0 && (
            <div className="space-y-2">
              <Label>Fields that need updating (optional)</Label>
              <div className="max-h-48 space-y-2 overflow-y-auto rounded-md border p-3">
                {visibleFields.map((field) => (
                  <div key={field.id} className="flex items-center gap-2">
                    <Checkbox
                      id={`field-${field.field_key}`}
                      checked={selectedFields.includes(field.field_key)}
                      onCheckedChange={() => handleToggleField(field.field_key)}
                      disabled={isLoading}
                    />
                    <Label
                      htmlFor={`field-${field.field_key}`}
                      className="text-sm font-normal cursor-pointer"
                    >
                      {field.label}
                    </Label>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={isLoading}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={isLoading || !message.trim()}
          >
            {isLoading ? "Sending..." : "Request Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
