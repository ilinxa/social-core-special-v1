"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { TemplateList } from "./TemplateList";
import { useTemplateList } from "@/features/forms/hooks/use-form-queries";
import { useHasPermission } from "@/hooks/use-has-permission";
import type { AccountType } from "@/types/rbac";

type TemplateListPageProps = {
  accountType: AccountType;
  slug: string;
  accountId: string;
  basePath: string;
};

export function TemplateListPage({
  accountType,
  slug,
  accountId,
  basePath,
}: TemplateListPageProps) {
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState("all");
  const [page, setPage] = useState(1);
  const canCreateForm = useHasPermission("can_create_form", accountType, accountId);

  const params: Record<string, unknown> = { page, page_size: 10 };
  if (statusFilter !== "all") params.status = statusFilter;

  const { data, isLoading } = useTemplateList(accountType, accountId, params);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => router.push(basePath)}>
          &larr; Back
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">Form Templates</h1>
      </div>

      <TemplateList
        data={data}
        isLoading={isLoading}
        statusFilter={statusFilter}
        onStatusChange={(s) => {
          setStatusFilter(s);
          setPage(1);
        }}
        onTemplateClick={(id) => router.push(`${basePath}/templates/${id}`)}
        onCreateClick={() => router.push(`${basePath}/templates/new`)}
        canCreate={canCreateForm}
        page={page}
        onPageChange={setPage}
      />
    </div>
  );
}
