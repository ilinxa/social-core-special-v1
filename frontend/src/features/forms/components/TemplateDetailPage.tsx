"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { FormBuilder } from "./form-builder/FormBuilder";
import { FORM_STATUS_CONFIG } from "@/features/forms/constants/form-statuses";
import { useTemplateDetail } from "@/features/forms/hooks/use-form-queries";
import {
  useUpdateTemplate,
  usePublishTemplate,
  useArchiveTemplate,
  useUnarchiveTemplate,
  useCreateEditDraft,
  useDeleteTemplate,
  useAddField,
  useUpdateField,
  useDeleteField,
  useReorderFields,
} from "@/features/forms/hooks/use-form-mutations";
import type { AccountType } from "@/types/rbac";
import type { FormBuilderMode } from "./form-builder/FormBuilder";

type TemplateDetailPageProps = {
  accountType: AccountType;
  accountId: string;
  formId: string;
  slug: string;
  basePath: string;
};

export function TemplateDetailPage({
  accountType,
  accountId,
  formId,
  slug,
  basePath,
}: TemplateDetailPageProps) {
  const router = useRouter();
  const { data: template, isLoading } = useTemplateDetail(formId);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const updateTemplate = useUpdateTemplate(accountType, accountId, formId);
  const publishTemplate = usePublishTemplate(accountType, accountId, formId);
  const archiveTemplate = useArchiveTemplate(accountType, accountId, formId);
  const unarchiveTemplate = useUnarchiveTemplate(accountType, accountId, formId);
  const createEditDraft = useCreateEditDraft(accountType, accountId, formId);
  const deleteTemplate = useDeleteTemplate(accountType, accountId);
  const addField = useAddField(formId);
  const updateField = useUpdateField(formId);
  const deleteField = useDeleteField(formId);
  const reorderFields = useReorderFields(formId);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (!template) {
    return <p className="text-muted-foreground">Template not found.</p>;
  }

  const perms = template._permissions;
  const isDraft = template.status === "draft";
  const isActive = template.status === "active";
  const isArchived = template.status === "archived";
  const mode: FormBuilderMode = perms.can_edit && isDraft ? "design" : "preview";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push(`${basePath}/templates`)}
        >
          &larr; Back
        </Button>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">
              {template.name}
            </h1>
            <StatusBadge status={template.status} statusMap={FORM_STATUS_CONFIG} />
            <span className="text-sm text-muted-foreground">
              v{template.version}
            </span>
          </div>
          {template.description && (
            <p className="mt-1 text-muted-foreground">{template.description}</p>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <Can allowed={perms.can_publish && isDraft}>
          <Button
            size="sm"
            onClick={() =>
              publishTemplate.mutate(undefined, {
                onSuccess: () => toast.success("Template published"),
                onError: () => toast.error("Failed to publish template"),
              })
            }
            disabled={publishTemplate.isPending}
          >
            Publish
          </Button>
        </Can>

        <Can allowed={perms.can_edit && isActive}>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              createEditDraft.mutate(undefined, {
                onSuccess: (newDraft) => {
                  toast.success("Edit draft created — you can now modify fields");
                  router.push(`${basePath}/templates/${newDraft.id}`);
                },
                onError: () => toast.error("Failed to create edit draft"),
              })
            }
            disabled={createEditDraft.isPending}
          >
            Edit (Create v{template.version + 1})
          </Button>
        </Can>

        <Can allowed={perms.can_archive && isActive}>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              archiveTemplate.mutate(undefined, {
                onSuccess: () => toast.success("Template archived"),
                onError: () => toast.error("Failed to archive template"),
              })
            }
            disabled={archiveTemplate.isPending}
          >
            Archive
          </Button>
        </Can>

        <Can allowed={perms.can_edit && isArchived}>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              unarchiveTemplate.mutate(undefined, {
                onSuccess: () => toast.success("Template restored to draft"),
                onError: () => toast.error("Failed to restore template"),
              })
            }
            disabled={unarchiveTemplate.isPending}
          >
            Restore to Draft
          </Button>
        </Can>

        <Can allowed={perms.can_delete}>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setDeleteOpen(true)}
          >
            Delete
          </Button>
        </Can>
      </div>

      {/* Form Builder */}
      <FormBuilder
        fields={template.fields}
        mode={mode}
        onAddField={(data) =>
          addField.mutate(data, {
            onSuccess: () => toast.success("Field added"),
            onError: () => toast.error("Failed to add field"),
          })
        }
        onUpdateField={(fieldId, data) =>
          updateField.mutate(
            { fieldId, data },
            {
              onSuccess: () => toast.success("Field updated"),
              onError: () => toast.error("Failed to update field"),
            },
          )
        }
        onDeleteField={(fieldId) =>
          deleteField.mutate(fieldId, {
            onSuccess: () => toast.success("Field deleted"),
            onError: () => toast.error("Failed to delete field"),
          })
        }
        onReorderFields={(fields) =>
          reorderFields.mutate(fields, {
            onError: () => toast.error("Failed to reorder fields"),
          })
        }
        isFieldLoading={
          addField.isPending ||
          updateField.isPending ||
          deleteField.isPending ||
          reorderFields.isPending
        }
      />

      {/* Delete dialog */}
      <ConfirmActionDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        title="Delete Template"
        description={`Are you sure you want to delete "${template.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        isLoading={deleteTemplate.isPending}
        onConfirm={() =>
          deleteTemplate.mutate(formId, {
            onSuccess: () => {
              toast.success("Template deleted");
              router.push(`${basePath}/templates`);
            },
            onError: () => toast.error("Failed to delete template"),
          })
        }
      />
    </div>
  );
}
