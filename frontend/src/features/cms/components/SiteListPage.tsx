/**
 * CMS Site List Page
 * ===================
 * Lists CMS sites for the current context (platform or business).
 * Supports create, click-to-detail, and quota display.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { QuotaBar } from "@/components/common/QuotaBar";
import { useSites } from "@/features/cms/hooks/use-cms-queries";
import { SiteCreateDialog } from "@/features/cms/components/SiteCreateDialog";
import type { CmsApiContext, CmsSite } from "@/features/cms/types";

type SiteListPageProps = {
  context: CmsApiContext;
  basePath: string;
  /** Max sites allowed (0 = unlimited). Business context only. */
  maxSites?: number;
};

export function SiteListPage({ context, basePath, maxSites = 0 }: SiteListPageProps) {
  const router = useRouter();
  const { data, isLoading } = useSites(context);
  const [createOpen, setCreateOpen] = useState(false);

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Sites</h1>
          <p className="text-sm text-muted-foreground">
            Manage your CMS websites and their pages.
          </p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="mr-1.5 h-4 w-4" />
          New Site
        </Button>
      </div>

      {/* Quota indicator (business context) */}
      {maxSites > 0 && data && (
        <QuotaBar
          current={data.results.length}
          max={maxSites}
          label="Sites"
        />
      )}

      {/* Site list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16">
          <p className="text-muted-foreground">No sites yet.</p>
          <Button variant="outline" onClick={() => setCreateOpen(true)}>
            Create your first site
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          {data.results.map((site: CmsSite) => (
            <button
              key={site.id}
              type="button"
              className="flex w-full items-center justify-between rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
              onClick={() =>
                router.push(`${basePath}/sites/${site.slug}`)
              }
            >
              <div className="space-y-1">
                <p className="font-medium">{site.name}</p>
                <p className="text-sm text-muted-foreground">
                  {site.slug}
                  {site.domain ? ` \u00b7 ${site.domain}` : ""}
                </p>
              </div>
              <Badge variant={site.is_active ? "default" : "secondary"}>
                {site.is_active ? "Active" : "Inactive"}
              </Badge>
            </button>
          ))}
        </div>
      )}

      {/* Create dialog */}
      <SiteCreateDialog
        context={context}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </div>
  );
}
