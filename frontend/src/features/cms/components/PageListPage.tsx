/**
 * CMS Page List
 * ==============
 * Lists pages for a site with status filter tabs.
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Can } from "@/components/common/Can";
import { PAGE_STATUS_CONFIG } from "@/features/cms/constants/cms-constants";
import { usePages } from "@/features/cms/hooks/use-cms-queries";
import { PageCreateDialog } from "@/features/cms/components/PageCreateDialog";
import type {
  CmsApiContext,
  CmsPage,
  CmsPermissions,
} from "@/features/cms/types";

const STATUS_TABS = ["all", "draft", "published", "archived"] as const;

type PageListPageProps = {
  context: CmsApiContext;
  siteSlug: string;
  basePath: string;
  permissions?: CmsPermissions | null;
};

export function PageListPage({
  context,
  siteSlug,
  basePath,
  permissions,
}: PageListPageProps) {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading } = usePages(context, {
    site: siteSlug,
    status: statusFilter === "all" ? undefined : statusFilter,
  });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Pages</h2>
        <Can allowed={permissions?.can_create_page ?? true}>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <Plus className="mr-1.5 h-4 w-4" />
            New Page
          </Button>
        </Can>
      </div>

      {/* Status tabs */}
      <div className="flex gap-2">
        {STATUS_TABS.map((tab) => (
          <Button
            key={tab}
            variant={statusFilter === tab ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter(tab)}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </Button>
        ))}
      </div>

      {/* Page list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <p className="py-8 text-center text-muted-foreground">
          No pages found.
        </p>
      ) : (
        <div className="space-y-2">
          {data.results.map((page: CmsPage) => (
            <button
              key={page.id}
              type="button"
              className="flex w-full items-center justify-between rounded-lg border p-4 text-left transition-colors hover:bg-muted/50"
              onClick={() =>
                router.push(`${basePath}/pages/${page.slug}`)
              }
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <p className="font-medium">{page.title}</p>
                  {page.is_required && (
                    <span className="text-xs text-muted-foreground">
                      (required)
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">
                  {page.path} &middot; Order: {page.order}
                </p>
              </div>
              <StatusBadge
                status={page.status}
                statusMap={PAGE_STATUS_CONFIG}
              />
            </button>
          ))}
        </div>
      )}

      <PageCreateDialog
        context={context}
        siteSlug={siteSlug}
        open={createOpen}
        onOpenChange={setCreateOpen}
      />
    </div>
  );
}
