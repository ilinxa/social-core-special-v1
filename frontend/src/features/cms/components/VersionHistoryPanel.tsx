/**
 * Version History Panel
 * ======================
 * Slide-out panel showing content versions for a block placement.
 * Supports rollback to any previous version.
 */

"use client";

import { useState } from "react";
import { Clock, RotateCcw } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { ConfirmActionDialog } from "@/components/common/ConfirmActionDialog";
import { VERSION_ACTION_CONFIG } from "@/features/cms/constants/cms-constants";
import { useBlockHistory } from "@/features/cms/hooks/use-cms-queries";
import { useRollbackContent } from "@/features/cms/hooks/use-cms-mutations";
import type {
  CmsApiContext,
  CmsContentVersion,
  ContentVersionAction,
} from "@/features/cms/types";

type VersionHistoryPanelProps = {
  context: CmsApiContext;
  blockPlacementId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

export function VersionHistoryPanel({
  context,
  blockPlacementId,
  open,
  onOpenChange,
}: VersionHistoryPanelProps) {
  const { data, isLoading } = useBlockHistory(context, blockPlacementId);
  const rollbackMutation = useRollbackContent(context, blockPlacementId);
  const [rollbackVersion, setRollbackVersion] = useState<number | null>(null);

  function handleRollback() {
    if (rollbackVersion === null) return;
    rollbackMutation.mutate(rollbackVersion, {
      onSuccess: () => {
        toast.success(`Rolled back to version ${rollbackVersion}`);
        setRollbackVersion(null);
      },
      onError: () => toast.error("Rollback failed"),
    });
  }

  return (
    <>
      <Sheet open={open} onOpenChange={onOpenChange}>
        <SheetContent className="w-96 overflow-y-auto sm:max-w-md">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Version History
            </SheetTitle>
            <SheetDescription>
              Content snapshots for this block. Click Restore to roll back.
            </SheetDescription>
          </SheetHeader>

          <div className="mt-6 space-y-3">
            {isLoading ? (
              Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-lg" />
              ))
            ) : !data?.results.length ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No versions recorded yet.
              </p>
            ) : (
              data.results.map((version: CmsContentVersion) => (
                <div
                  key={version.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">
                        v{version.version_number}
                      </span>
                      <Badge variant="outline" className="text-xs">
                        {VERSION_ACTION_CONFIG[
                          version.action as ContentVersionAction
                        ] ?? version.action}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {version.created_by_username} &middot;{" "}
                      {new Date(version.created_at).toLocaleString()}
                    </p>
                    {version.notes && (
                      <p className="text-xs text-muted-foreground italic">
                        {version.notes}
                      </p>
                    )}
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setRollbackVersion(version.version_number)}
                  >
                    <RotateCcw className="mr-1 h-3 w-3" />
                    Restore
                  </Button>
                </div>
              ))
            )}
          </div>
        </SheetContent>
      </Sheet>

      <ConfirmActionDialog
        open={rollbackVersion !== null}
        onOpenChange={(v) => !v && setRollbackVersion(null)}
        title="Restore Version"
        description={`This will restore draft content to version ${rollbackVersion}. A new version will be created with the rollback action. Published content is not affected.`}
        confirmLabel="Restore"
        onConfirm={handleRollback}
        isLoading={rollbackMutation.isPending}
      />
    </>
  );
}
