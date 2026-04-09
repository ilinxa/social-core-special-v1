/**
 * Page Editor
 * =============
 * Main CMS page editing experience.
 * Layout: Content Tree (left) + Block Content Editor (right).
 * Fetches page with ?depth=full for the full section/block tree.
 *
 * Includes: publish/unpublish, version history, export/import.
 */

"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Clock, Download, Menu, Upload } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/common/StatusBadge";
import { Can } from "@/components/common/Can";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { ApiError } from "@/lib/api-client";
import { usePage } from "@/features/cms/hooks/use-cms-queries";
import {
  useExportPage,
  useImportPage,
  usePublishPage,
  useUnpublishPage,
} from "@/features/cms/hooks/use-cms-mutations";
import { PAGE_STATUS_CONFIG } from "@/features/cms/constants/cms-constants";
import { ContentTree } from "@/features/cms/components/ContentTree";
import { BlockContentEditor } from "@/features/cms/components/BlockContentEditor";
import { VersionHistoryPanel } from "@/features/cms/components/VersionHistoryPanel";
import type {
  CmsApiContext,
  CmsBlockPlacement,
  CmsPageDetail,
  CmsPermissions,
  CmsPublishError,
  PageStatus,
} from "@/features/cms/types";

type PageEditorProps = {
  context: CmsApiContext;
  siteSlug: string;
  pageSlug: string;
  basePath: string;
};

export function PageEditor({
  context,
  siteSlug,
  pageSlug,
  basePath,
}: PageEditorProps) {
  const router = useRouter();
  const { data: page, isLoading } = usePage(context, pageSlug, {
    site: siteSlug,
    depth: "full",
  });
  const publishMutation = usePublishPage(context);
  const unpublishMutation = useUnpublishPage(context);
  const importMutation = useImportPage(context);
  const exportMutation = useExportPage(context);

  const [publishErrors, setPublishErrors] = useState<CmsPublishError[]>([]);
  const [publishConfirmOpen, setPublishConfirmOpen] = useState(false);
  const [unpublishConfirmOpen, setUnpublishConfirmOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [mobileTreeOpen, setMobileTreeOpen] = useState(false);

  const permissions = (
    page && "_permissions" in page ? page._permissions : null
  ) as CmsPermissions | null;

  // Build sections from page detail
  const sections = useMemo(() => {
    if (!page || !("section_placements" in page)) return [];
    return (page as CmsPageDetail).section_placements ?? [];
  }, [page]);

  // Derive initial block ID from sections (first block of first section)
  const initialBlockId = useMemo(() => {
    return sections[0]?.block_placements?.[0]?.id ?? null;
  }, [sections]);

  const [selectedBlockId, setSelectedBlockId] = useState<string | null>(null);
  const activeBlockId = selectedBlockId ?? initialBlockId;

  // Find selected block across all sections
  const selectedBlock = useMemo<CmsBlockPlacement | null>(() => {
    if (!activeBlockId) return null;
    for (const section of sections) {
      const found = section.block_placements.find(
        (b) => b.id === activeBlockId,
      );
      if (found) return found;
    }
    return null;
  }, [sections, activeBlockId]);

  // Publish error map for tree highlighting
  const publishErrorMap = useMemo(() => {
    const map = new Map<string, { field_key: string; message: string }[]>();
    for (const err of publishErrors) {
      const existing = map.get(err.block_placement_id) ?? [];
      existing.push({ field_key: err.field_key, message: err.message });
      map.set(err.block_placement_id, existing);
    }
    return map;
  }, [publishErrors]);

  // Publish errors for selected block
  const selectedBlockErrors = activeBlockId
    ? publishErrors.filter((e) => e.block_placement_id === activeBlockId)
    : [];

  function handlePublish() {
    setPublishErrors([]);
    publishMutation.mutate(
      { pageSlug, siteSlug },
      {
        onSuccess: () => toast.success("Page published"),
        onError: (error) => {
          if (
            error instanceof ApiError &&
            error.code === "validation_error" &&
            error.details?.publish_errors
          ) {
            setPublishErrors(
              error.details.publish_errors as CmsPublishError[],
            );
            toast.error("Publish failed — fix validation errors");
          } else {
            toast.error("Failed to publish page");
          }
        },
      },
    );
  }

  function handleUnpublish() {
    unpublishMutation.mutate(
      { pageSlug, siteSlug },
      {
        onSuccess: () => toast.success("Page unpublished"),
        onError: () => toast.error("Failed to unpublish"),
      },
    );
  }

  function handleExport() {
    exportMutation.mutate(
      { pageSlug, siteSlug },
      {
        onSuccess: (data) => {
          const blob = new Blob([JSON.stringify(data, null, 2)], {
            type: "application/json",
          });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = `${pageSlug}-export.json`;
          a.click();
          URL.revokeObjectURL(url);
          toast.success("Page exported");
        },
        onError: () => toast.error("Export failed"),
      },
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <Skeleton className="h-8 w-48" />
        <div className="flex gap-6">
          <Skeleton className="h-96 w-72" />
          <Skeleton className="h-96 flex-1" />
        </div>
      </div>
    );
  }

  if (!page) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground">Page not found.</p>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Open content tree"
            className="md:hidden"
            onClick={() => setMobileTreeOpen(true)}
          >
            <Menu className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push(`${basePath}/pages`)}
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back
          </Button>
          <Separator orientation="vertical" className="h-6" />
          <h1 className="text-lg font-semibold">{page.title}</h1>
          <StatusBadge
            status={page.status as PageStatus}
            statusMap={PAGE_STATUS_CONFIG}
          />
        </div>
        <div className="flex items-center gap-2">
          {/* Version history */}
          {activeBlockId && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setHistoryOpen(true)}
            >
              <Clock className="mr-1 h-4 w-4" />
              History
            </Button>
          )}

          {/* Export */}
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={exportMutation.isPending}
          >
            <Download className="mr-1 h-4 w-4" />
            Export
          </Button>

          {/* Import (file picker) */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              const input = document.createElement("input");
              input.type = "file";
              input.accept = ".json";
              input.onchange = (e) => {
                const file = (e.target as HTMLInputElement).files?.[0];
                if (!file) return;
                const reader = new FileReader();
                reader.onload = () => {
                  try {
                    const data = JSON.parse(reader.result as string);
                    importMutation.mutate(
                      {
                        pageSlug,
                        siteSlug,
                        data: {
                          export_version: data.export_version ?? "3.1",
                          page: data.page ?? data,
                        },
                      },
                      {
                        onSuccess: () => toast.success("Page content imported"),
                        onError: () => toast.error("Import failed"),
                      },
                    );
                  } catch {
                    toast.error("Invalid JSON file");
                  }
                };
                reader.readAsText(file);
              };
              input.click();
            }}
          >
            <Upload className="mr-1 h-4 w-4" />
            Import
          </Button>

          {/* Publish / Unpublish with confirmation */}
          <Can allowed={permissions?.can_publish_content ?? true}>
            {page.status === "published" ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setUnpublishConfirmOpen(true)}
                disabled={unpublishMutation.isPending}
              >
                Unpublish
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => setPublishConfirmOpen(true)}
                disabled={publishMutation.isPending}
              >
                Publish
              </Button>
            )}
          </Can>
        </div>
      </div>

      {/* Publish errors banner */}
      {publishErrors.length > 0 && (
        <div className="border-b bg-destructive/10 px-6 py-2 text-sm text-destructive">
          {publishErrors.length} validation error(s) found. Fix them and try
          again.
        </div>
      )}

      {/* Main editor area */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Content Tree (hidden on mobile, visible on md+) */}
        <div className="hidden w-72 shrink-0 overflow-y-auto border-r p-4 md:block">
          <ContentTree
            sections={sections}
            selectedBlockId={activeBlockId}
            onSelectBlock={setSelectedBlockId}
            publishErrors={publishErrorMap}
          />
        </div>

        {/* Right: Block Editor */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          {selectedBlock ? (
            <BlockContentEditor
              key={selectedBlock.id}
              context={context}
              block={selectedBlock}
              publishErrors={selectedBlockErrors}
            />
          ) : (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              Select a block from the tree to edit its content.
            </div>
          )}
        </div>
      </div>

      {/* Mobile tree drawer */}
      <Sheet open={mobileTreeOpen} onOpenChange={setMobileTreeOpen}>
        <SheetContent side="left" className="w-72 overflow-y-auto p-4">
          <SheetHeader>
            <SheetTitle>Content Structure</SheetTitle>
          </SheetHeader>
          <div className="mt-4">
            <ContentTree
              sections={sections}
              selectedBlockId={activeBlockId}
              onSelectBlock={(id) => {
                setSelectedBlockId(id);
                setMobileTreeOpen(false);
              }}
              publishErrors={publishErrorMap}
            />
          </div>
        </SheetContent>
      </Sheet>

      {/* Publish confirmation dialog */}
      <ConfirmActionDialog
        open={publishConfirmOpen}
        onOpenChange={setPublishConfirmOpen}
        title="Publish Page"
        description="This will validate all blocks and make the page live. Are you sure?"
        confirmLabel="Publish"
        onConfirm={() => {
          setPublishConfirmOpen(false);
          handlePublish();
        }}
        isLoading={publishMutation.isPending}
      />

      {/* Unpublish confirmation dialog */}
      <ConfirmActionDialog
        open={unpublishConfirmOpen}
        onOpenChange={setUnpublishConfirmOpen}
        title="Unpublish Page"
        description="This will revert the page to draft. Published content will be preserved but not visible publicly."
        confirmLabel="Unpublish"
        onConfirm={() => {
          setUnpublishConfirmOpen(false);
          handleUnpublish();
        }}
        isLoading={unpublishMutation.isPending}
      />

      {/* Version history panel */}
      {activeBlockId && (
        <VersionHistoryPanel
          context={context}
          blockPlacementId={activeBlockId}
          open={historyOpen}
          onOpenChange={setHistoryOpen}
        />
      )}
    </div>
  );
}
