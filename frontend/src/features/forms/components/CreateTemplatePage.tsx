"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useCreateTemplate } from "@/features/forms/hooks/use-form-mutations";
import type { AccountType } from "@/types/rbac";
import type { OwnerType, FormScope } from "@/types/forms";

type CreateTemplatePageProps = {
  accountType: AccountType;
  accountId: string;
  slug: string;
  basePath: string;
};

export function CreateTemplatePage({
  accountType,
  accountId,
  slug,
  basePath,
}: CreateTemplatePageProps) {
  const router = useRouter();
  const createTemplate = useCreateTemplate(accountType, accountId);

  const [name, setName] = useState("");
  const [slugValue, setSlugValue] = useState("");
  const [description, setDescription] = useState("");

  const isValid = name.trim().length > 0;

  function handleSubmit() {
    if (!isValid) return;
    createTemplate.mutate(
      {
        name: name.trim(),
        slug: slugValue.trim() || undefined,
        description: description.trim() || undefined,
        owner_type: accountType as OwnerType,
        owner_id: accountId,
        scope: accountType as FormScope,
      },
      {
        onSuccess: (data) => {
          toast.success("Form template created");
          router.push(`${basePath}/templates/${data.id}`);
        },
        onError: () => {
          toast.error("Failed to create template");
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push(`${basePath}/templates`)}
        >
          &larr; Back
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">Create New Form</h1>
      </div>

      <div className="max-w-xl space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="template-name">Form Name</Label>
          <Input
            id="template-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Membership Application"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="template-slug">
            Slug <span className="text-muted-foreground">(optional)</span>
          </Label>
          <Input
            id="template-slug"
            value={slugValue}
            onChange={(e) => setSlugValue(e.target.value)}
            placeholder="e.g. membership-application"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="template-desc">
            Description{" "}
            <span className="text-muted-foreground">(optional)</span>
          </Label>
          <Textarea
            id="template-desc"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe what this form is for"
            rows={3}
          />
        </div>

        <div className="flex gap-2 pt-2">
          <Button
            onClick={handleSubmit}
            disabled={!isValid || createTemplate.isPending}
          >
            Create Form
          </Button>
          <Button
            variant="outline"
            onClick={() => router.push(`${basePath}/templates`)}
          >
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
