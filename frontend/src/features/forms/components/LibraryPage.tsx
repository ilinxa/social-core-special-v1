"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useLibrary } from "@/features/forms/hooks/use-form-queries";
import { useForkTemplate } from "@/features/forms/hooks/use-form-mutations";
import type { AccountType } from "@/types/rbac";
import type { OwnerType } from "@/types/forms";

type LibraryPageProps = {
  accountType: AccountType;
  accountId: string;
  slug: string;
  basePath: string;
};

export function LibraryPage({
  accountType,
  accountId,
  slug,
  basePath,
}: LibraryPageProps) {
  const router = useRouter();
  const [page, setPage] = useState(1);
  const { data, isLoading } = useLibrary({ page, page_size: 10 });
  const forkTemplate = useForkTemplate();

  const totalPages = data ? Math.ceil(data.count / 10) : 0;

  function handleFork(formId: string) {
    forkTemplate.mutate(
      {
        formId,
        data: {
          new_owner_type: accountType as OwnerType,
          new_owner_id: accountId,
        },
      },
      {
        onSuccess: (result) => {
          toast.success("Template forked successfully");
          router.push(`${basePath}/templates/${result.id}`);
        },
        onError: () => {
          toast.error("Failed to fork template");
        },
      },
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => router.push(basePath)}>
          &larr; Back
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">Template Library</h1>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }, (_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : !data?.results.length ? (
        <p className="py-8 text-center text-muted-foreground">
          No public templates available.
        </p>
      ) : (
        <div className="space-y-3">
          {data.results.map((tpl) => (
            <div
              key={tpl.id}
              className="flex items-center justify-between rounded-lg border p-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{tpl.name}</span>
                  <Badge variant="secondary">{tpl.scope}</Badge>
                </div>
                {tpl.description && (
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {tpl.description}
                  </p>
                )}
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleFork(tpl.id)}
                disabled={forkTemplate.isPending}
              >
                Fork
              </Button>
            </div>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={page <= 1}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </Button>
          <span className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={page >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </div>
  );
}
