/**
 * Template Library Page
 * ======================
 * Manage activated templates for the business.
 * Tabs: Section Templates | Block Templates.
 * "Remove" button with deactivation confirmation.
 */

"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { ApiError } from "@/lib/api-client";
import {
  useLibraryBlocks,
  useLibrarySections,
} from "@/features/cms/hooks/use-cms-queries";
import {
  useDeactivateBlockTemplate,
  useDeactivateSectionTemplate,
} from "@/features/cms/hooks/use-cms-mutations";
import type {
  CmsBlockActivation,
  CmsSectionActivation,
} from "@/features/cms/types";

type TemplateLibraryPageProps = {
  businessSlug: string;
};

export function TemplateLibraryPage({
  businessSlug,
}: TemplateLibraryPageProps) {
  const { data: sections, isLoading: sectionsLoading } =
    useLibrarySections(businessSlug);
  const { data: blocks, isLoading: blocksLoading } =
    useLibraryBlocks(businessSlug);
  const deactivateSection = useDeactivateSectionTemplate(businessSlug);
  const deactivateBlock = useDeactivateBlockTemplate(businessSlug);

  const [confirmId, setConfirmId] = useState<{
    id: string;
    type: "section" | "block";
    name: string;
  } | null>(null);

  function handleDeactivate() {
    if (!confirmId) return;
    const mutation =
      confirmId.type === "section" ? deactivateSection : deactivateBlock;
    mutation.mutate(confirmId.id, {
      onSuccess: () => {
        toast.success(`Template "${confirmId.name}" removed from library`);
        setConfirmId(null);
      },
      onError: (error) => {
        if (
          error instanceof ApiError &&
          error.details?.rule === "template_in_use"
        ) {
          toast.error(
            "Cannot remove — this template is used by active pages.",
          );
        } else {
          toast.error("Failed to remove template");
        }
        setConfirmId(null);
      },
    });
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">My Templates</h1>
        <p className="text-sm text-muted-foreground">
          Templates activated for your business content.
        </p>
      </div>

      <Tabs defaultValue="sections">
        <TabsList>
          <TabsTrigger value="sections">
            Section Templates ({sections?.results.length ?? 0})
          </TabsTrigger>
          <TabsTrigger value="blocks">
            Block Templates ({blocks?.results.length ?? 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="sections" className="mt-4">
          <LibraryGrid
            items={sections?.results}
            isLoading={sectionsLoading}
            type="section"
            onRemove={(id, name) =>
              setConfirmId({ id, type: "section", name })
            }
          />
        </TabsContent>

        <TabsContent value="blocks" className="mt-4">
          <LibraryGrid
            items={blocks?.results}
            isLoading={blocksLoading}
            type="block"
            onRemove={(id, name) => setConfirmId({ id, type: "block", name })}
          />
        </TabsContent>
      </Tabs>

      <ConfirmActionDialog
        open={confirmId !== null}
        onOpenChange={(v) => !v && setConfirmId(null)}
        title="Remove Template"
        description={`Remove "${confirmId?.name}" from your library? You can re-activate it later from the catalog.`}
        confirmLabel="Remove"
        variant="destructive"
        onConfirm={handleDeactivate}
        isLoading={
          deactivateSection.isPending || deactivateBlock.isPending
        }
      />
    </div>
  );
}

function LibraryGrid({
  items,
  isLoading,
  type,
  onRemove,
}: {
  items?: (CmsSectionActivation | CmsBlockActivation)[];
  isLoading: boolean;
  type: "section" | "block";
  onRemove: (activationId: string, templateName: string) => void;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-32 rounded-lg" />
        ))}
      </div>
    );
  }

  if (!items?.length) {
    return (
      <p className="py-12 text-center text-muted-foreground">
        No {type} templates activated. Visit the catalog to add some.
      </p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((activation) => (
        <div
          key={activation.id}
          className="flex flex-col justify-between rounded-lg border p-4"
        >
          <div className="space-y-2">
            <h3 className="font-medium">
              {activation.template.display_name}
            </h3>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {activation.template.description || "No description"}
            </p>
            <Badge variant="outline" className="text-xs">
              {"section_type" in activation.template
                ? activation.template.section_type
                : (activation.template as CmsBlockActivation["template"])
                    .block_type}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="mt-3 text-destructive hover:text-destructive"
            onClick={() =>
              onRemove(activation.id, activation.template.display_name)
            }
          >
            <Trash2 className="mr-1 h-3.5 w-3.5" />
            Remove
          </Button>
        </div>
      ))}
    </div>
  );
}
