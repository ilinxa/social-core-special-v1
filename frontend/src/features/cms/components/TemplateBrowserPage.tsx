/**
 * Template Browser Page (Platform)
 * ==================================
 * Read-only view of ALL templates (superuser manages via Django Admin).
 * No activate/deactivate — platform uses templates directly.
 */

"use client";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TEMPLATE_ORG_TYPE_LABELS } from "@/features/cms/constants/cms-constants";
import {
  useAdminBlockTemplates,
  useAdminSectionTemplates,
} from "@/features/cms/hooks/use-cms-queries";
import type {
  CmsBlockTemplate,
  CmsSectionTemplate,
  TemplateOrgType,
} from "@/features/cms/types";

export function TemplateBrowserPage() {
  const { data: sections, isLoading: sectionsLoading } =
    useAdminSectionTemplates();
  const { data: blocks, isLoading: blocksLoading } =
    useAdminBlockTemplates();

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Templates</h1>
        <p className="text-sm text-muted-foreground">
          All CMS templates. Managed by superuser via Django Admin.
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
          {sectionsLoading ? (
            <LoadingSkeleton />
          ) : !sections?.results.length ? (
            <EmptyState text="No section templates." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {sections.results.map((tpl: CmsSectionTemplate) => (
                <div key={tpl.id} className="rounded-lg border p-4 space-y-2">
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
                  <div className="flex gap-1">
                    <Badge variant="outline" className="text-xs">
                      {tpl.section_type}
                    </Badge>
                    {tpl.org_type && (
                      <Badge variant="outline" className="text-xs">
                        {TEMPLATE_ORG_TYPE_LABELS[tpl.org_type as TemplateOrgType]}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="blocks" className="mt-4">
          {blocksLoading ? (
            <LoadingSkeleton />
          ) : !blocks?.results.length ? (
            <EmptyState text="No block templates." />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {blocks.results.map((tpl: CmsBlockTemplate) => (
                <div key={tpl.id} className="rounded-lg border p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="font-medium">{tpl.display_name}</h3>
                    <div className="flex items-center gap-1">
                      {tpl.is_default && (
                        <Badge variant="secondary" className="text-xs">
                          Default
                        </Badge>
                      )}
                      <Badge variant="secondary" className="text-xs">
                        v{tpl.schema_version}
                      </Badge>
                    </div>
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {tpl.description || "No description"}
                  </p>
                  <div className="flex flex-wrap gap-1">
                    <Badge variant="outline" className="text-xs">
                      {tpl.block_type}
                    </Badge>
                    {tpl.org_type && (
                      <Badge variant="outline" className="text-xs">
                        {TEMPLATE_ORG_TYPE_LABELS[tpl.org_type as TemplateOrgType]}
                      </Badge>
                    )}
                    {tpl.schema.fields.length > 0 && (
                      <Badge variant="outline" className="text-xs">
                        {tpl.schema.fields.length} fields
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }, (_, i) => (
        <Skeleton key={i} className="h-32 rounded-lg" />
      ))}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <p className="py-12 text-center text-muted-foreground">{text}</p>
  );
}
