"use client";

import { useMemo } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FormField } from "@/types/forms";
import type { TransactionFormResponse } from "@/types/transactions";

interface TransactionFormPanelProps {
  formResponse: TransactionFormResponse;
  fields: FormField[];
  infoRequestedFields?: string[] | null;
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "\u2014";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function TransactionFormPanel({
  formResponse,
  fields: rawFields,
  infoRequestedFields,
}: TransactionFormPanelProps) {
  const fields = useMemo(
    () =>
      [...rawFields]
        .filter((f) => !f.is_hidden)
        .sort((a, b) => a.order - b.order),
    [rawFields],
  );

  const requestedFieldSet = useMemo(
    () => new Set(infoRequestedFields ?? []),
    [infoRequestedFields],
  );

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">
            {formResponse.form_name ?? "Form Response"}
          </CardTitle>
          <span className="text-xs text-muted-foreground">
            Revision {formResponse.revision}
          </span>
        </div>
      </CardHeader>
      <CardContent>
        {fields.length === 0 ? (
          <p className="text-sm text-muted-foreground">No fields to display.</p>
        ) : (
          <div className="rounded-lg border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground w-1/3">
                    Field
                  </th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">
                    Value
                  </th>
                </tr>
              </thead>
              <tbody>
                {fields.map((field, idx) => {
                  const isRequested = requestedFieldSet.has(field.field_key);
                  return (
                    <tr
                      key={field.id}
                      className={`${idx < fields.length - 1 ? "border-b" : ""} ${isRequested ? "bg-amber-50 dark:bg-amber-950/30" : ""}`}
                    >
                      <td className="px-4 py-2 font-medium text-muted-foreground">
                        <span className="flex items-center gap-2">
                          {field.label}
                          {isRequested && (
                            <Badge
                              variant="outline"
                              className="text-xs border-amber-400 text-amber-700"
                            >
                              Needs update
                            </Badge>
                          )}
                        </span>
                      </td>
                      <td className="px-4 py-2">
                        {formatValue(formResponse.data[field.field_key])}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
