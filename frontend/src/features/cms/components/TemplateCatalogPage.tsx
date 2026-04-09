/**
 * Template Catalog Page
 * ======================
 * Browse available templates (not yet activated) for the business.
 * Tabs: Section Templates | Block Templates.
 * "Activate" button on each card.
 */

"use client";

import { toast } from "sonner";
import { Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TEMPLATE_ORG_TYPE_LABELS } from "@/features/cms/constants/cms-constants";
import {
  useCatalogBlocks,
  useCatalogSections,
} from "@/features/cms/hooks/use-cms-queries";
import {
  useActivateBlockTemplate,
  useActivateSectionTemplate,
} from "@/features/cms/hooks/use-cms-mutations";
import type {
  CmsTemplateCatalogBlock,
  CmsTemplateCatalogSection,
  TemplateOrgType,
} from "@/features/cms/types";

type TemplateCatalogPageProps = {
  businessSlug: string;
};

export function TemplateCatalogPage({ businessSlug }: TemplateCatalogPageProps) {
  const { data: sections, isLoading: sectionsLoading } =
    useCatalogSections(businessSlug);
  const { data: blocks, isLoading: blocksLoading } =
    useCatalogBlocks(businessSlug);
  const activateSection = useActivateSectionTemplate(businessSlug);
  const activateBlock = useActivateBlockTemplate(businessSlug);

  function handleActivateSection(templateId: string) {
    activateSection.mutate(templateId, {
      onSuccess: () => toast.success("Section template activated"),
      onError: () => toast.error("Failed to activate template"),
    });
  }

  function handleActivateBlock(templateId: string) {
    activateBlock.mutate(templateId, {
      onSuccess: () => toast.success("Block template activated"),
      onError: () => toast.error("Failed to activate template"),
    });
  }

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Template Catalog</h1>
        <p className="text-sm text-muted-foreground">
          Browse and activate templates for your content.
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
          <TemplateGrid
            items={sections?.results}
            isLoading={sectionsLoading}
            onActivate={handleActivateSection}
            activating={activateSection.isPending}
            emptyMessage="All available section templates are already in your library."
          />
        </TabsContent>

        <TabsContent value="blocks" className="mt-4">
          <TemplateGrid
            items={blocks?.results}
            isLoading={blocksLoading}
            onActivate={handleActivateBlock}
            activating={activateBlock.isPending}
            emptyMessage="All available block templates are already in your library."
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function TemplateGrid({
  items,
  isLoading,
  onActivate,
  activating,
  emptyMessage,
}: {
  items?: (CmsTemplateCatalogSection | CmsTemplateCatalogBlock)[];
  isLoading: boolean;
  onActivate: (id: string) => void;
  activating: boolean;
  emptyMessage: string;
}) {
  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-40 rounded-lg" />
        ))}
      </div>
    );
  }

  if (!items?.length) {
    return (
      <p className="py-12 text-center text-muted-foreground">{emptyMessage}</p>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items.map((tpl) => (
        <div
          key={tpl.id}
          className="flex flex-col justify-between rounded-lg border p-4"
        >
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">{tpl.display_name}</h3>
              {tpl.is_default && (
                <Badge variant="secondary" className="text-xs">
                  Default
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground line-clamp-2">
              {tpl.description || "No description"}
            </p>
            <div className="flex gap-2">
              <Badge variant="outline" className="text-xs">
                {"section_type" in tpl
                  ? (tpl as CmsTemplateCatalogSection).section_type
                  : (tpl as CmsTemplateCatalogBlock).block_type}
              </Badge>
              <Badge variant="outline" className="text-xs">
                {TEMPLATE_ORG_TYPE_LABELS[tpl.org_type as TemplateOrgType]}
              </Badge>
            </div>
          </div>
          <Button
            size="sm"
            className="mt-4"
            onClick={() => onActivate(tpl.id)}
            disabled={activating}
          >
            <Plus className="mr-1 h-3.5 w-3.5" />
            Activate
          </Button>
        </div>
      ))}
    </div>
  );
}
