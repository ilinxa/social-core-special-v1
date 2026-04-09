/**
 * Business CMS Management Page (Platform Admin)
 * ================================================
 * Toggle CMS enabled/disabled per business.
 * View activated templates for each business.
 */

"use client";

import { useState } from "react";
import { Building2 } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import {
  useBusinessActivations,
  useBusinessCmsStatus,
} from "@/features/cms/hooks/use-cms-queries";
import { useToggleBusinessCms } from "@/features/cms/hooks/use-cms-mutations";
import type { BusinessCmsStatus } from "@/features/cms/types";

export function BusinessCmsManagementPage() {
  const { data, isLoading } = useBusinessCmsStatus();
  const [detailId, setDetailId] = useState<string | null>(null);

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-2xl font-bold">Business CMS Management</h1>
        <p className="text-sm text-muted-foreground">
          Enable or disable CMS access for businesses. Enabling auto-provisions
          default templates.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-16 w-full rounded-lg" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <p className="py-8 text-center text-muted-foreground">
          No businesses found.
        </p>
      ) : (
        <div className="space-y-2">
          {data.results.map((biz: BusinessCmsStatus) => (
            <BusinessRow
              key={biz.id}
              business={biz}
              onViewActivations={() => setDetailId(biz.id)}
            />
          ))}
        </div>
      )}

      {/* Activations detail sheet */}
      {detailId && (
        <ActivationsSheet
          businessId={detailId}
          open={detailId !== null}
          onOpenChange={(v) => !v && setDetailId(null)}
        />
      )}
    </div>
  );
}

function BusinessRow({
  business,
  onViewActivations,
}: {
  business: BusinessCmsStatus;
  onViewActivations: () => void;
}) {
  const toggleMutation = useToggleBusinessCms(business.id);

  function handleToggle(enabled: boolean) {
    toggleMutation.mutate(
      { cms_enabled: enabled },
      {
        onSuccess: () => {
          toast.success(
            enabled
              ? `CMS enabled for ${business.legal_name}`
              : `CMS disabled for ${business.legal_name}`,
          );
        },
        onError: () => toast.error("Failed to toggle CMS"),
      },
    );
  }

  return (
    <div className="flex items-center justify-between rounded-lg border p-4">
      <button
        type="button"
        className="flex items-center gap-3 text-left"
        onClick={onViewActivations}
      >
        <Building2 className="h-5 w-5 text-muted-foreground" />
        <div>
          <p className="font-medium">{business.legal_name}</p>
          <p className="text-sm text-muted-foreground">{business.slug}</p>
        </div>
      </button>
      <div className="flex items-center gap-3">
        <Badge variant={business.cms_enabled ? "default" : "secondary"}>
          {business.cms_enabled ? "Enabled" : "Disabled"}
        </Badge>
        <Switch
          checked={business.cms_enabled}
          onCheckedChange={handleToggle}
          disabled={toggleMutation.isPending}
        />
      </div>
    </div>
  );
}

function ActivationsSheet({
  businessId,
  open,
  onOpenChange,
}: {
  businessId: string;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const { data, isLoading } = useBusinessActivations(businessId);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Activated Templates</SheetTitle>
        </SheetHeader>
        <div className="mt-6 space-y-6">
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : (
            <>
              <div>
                <h3 className="mb-2 text-sm font-medium">Section Templates</h3>
                {data?.section_templates.length ? (
                  <div className="space-y-1">
                    {data.section_templates.map((a) => (
                      <div
                        key={a.id}
                        className="rounded border px-3 py-2 text-sm"
                      >
                        {a.template.display_name}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">None</p>
                )}
              </div>
              <div>
                <h3 className="mb-2 text-sm font-medium">Block Templates</h3>
                {data?.block_templates.length ? (
                  <div className="space-y-1">
                    {data.block_templates.map((a) => (
                      <div
                        key={a.id}
                        className="rounded border px-3 py-2 text-sm"
                      >
                        {a.template.display_name}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">None</p>
                )}
              </div>
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
