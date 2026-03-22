"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown } from "lucide-react";

import { StatusBadge } from "@/components/common/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  TRANSACTION_CATEGORY_CONFIG,
  TRANSACTION_STATUS_CONFIG,
} from "@/features/transactions/constants/transaction-statuses";
import { useTransactionList } from "@/features/transactions/hooks/use-transaction-queries";
import type {
  TransactionCategory,
  TransactionListItem,
  TransactionRole,
  TransactionStatus,
} from "@/types/transactions";

// =============================================================================
// ROLE TABS
// =============================================================================

const ROLE_TABS: { value: TransactionRole; label: string }[] = [
  { value: "all", label: "All" },
  { value: "initiator", label: "Sent" },
  { value: "target", label: "Received" },
];

// =============================================================================
// CATEGORY ORDER — easy to extend for future types
// =============================================================================

const CATEGORY_ORDER: TransactionCategory[] = [
  "membership",
  "ownership",
  "verification",
  "permission",
  "social",
];

// =============================================================================
// TRANSACTION TYPE DISPLAY NAMES
// =============================================================================

const TRANSACTION_TYPE_LABELS: Record<string, string> = {
  business_membership_invitation: "Membership Invitation",
  business_membership_request: "Membership Request",
  platform_membership_invitation: "Membership Invitation",
  platform_membership_request: "Membership Request",
  business_ownership_transfer: "Ownership Transfer",
  platform_ownership_transfer: "Ownership Transfer",
  business_creation_permission_request: "Business Creation Request",
  business_verification_request: "Verification Request",
  business_follow_request: "Follow Request",
  business_follow_approval_request: "Follow Approval Request",
  platform_follow_request: "Follow Request",
  business_connection_request: "Connection Request",
  business_platform_connection_request: "Connection Request",
  user_connection_request: "Connection Request",
};

function getTransactionTypeLabel(type: string): string {
  return (
    TRANSACTION_TYPE_LABELS[type] ??
    type
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

// =============================================================================
// CATEGORY CARD
// =============================================================================

interface CategoryCardProps {
  category: TransactionCategory;
  transactions: TransactionListItem[];
  defaultOpen?: boolean;
  onTransactionClick: (id: string) => void;
}

function CategoryCard({
  category,
  transactions,
  defaultOpen = true,
  onTransactionClick,
}: CategoryCardProps) {
  const config = TRANSACTION_CATEGORY_CONFIG[category];
  const pendingCount = transactions.filter(
    (t) => t.status === "pending" || t.status === "info_requested",
  ).length;

  return (
    <Collapsible defaultOpen={defaultOpen}>
      <div className="rounded-lg border">
        <CollapsibleTrigger className="flex w-full items-center justify-between p-4 text-left hover:bg-muted/50 transition-colors [&[data-state=open]>svg]:rotate-180">
          <div className="flex items-center gap-3">
            <h3 className="font-semibold">{config?.label ?? category}</h3>
            <Badge variant="secondary" className="text-xs">
              {transactions.length}
            </Badge>
            {pendingCount > 0 && (
              <Badge className="text-xs bg-blue-100 text-blue-800 border-transparent">
                {pendingCount} pending
              </Badge>
            )}
          </div>
          <ChevronDown className="h-4 w-4 text-muted-foreground transition-transform duration-200" />
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="border-t">
            {transactions.length === 0 ? (
              <p className="p-4 text-center text-sm text-muted-foreground">
                No transactions in this category.
              </p>
            ) : (
              <div className="divide-y">
                {transactions.map((t) => (
                  <button
                    key={t.id}
                    className="flex w-full items-center justify-between p-4 text-left transition-colors hover:bg-muted/50"
                    onClick={() => onTransactionClick(t.id)}
                  >
                    <div className="space-y-1 min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">
                          {t.initiator_name}
                        </span>
                        <span className="text-muted-foreground">&rarr;</span>
                        <span className="font-medium truncate">
                          {t.target_name}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {getTransactionTypeLabel(t.transaction_type)}
                        </span>
                        <span className="text-xs text-muted-foreground capitalize">
                          &middot; {t.mode}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0 ml-4">
                      <span className="text-sm text-muted-foreground">
                        {new Date(t.created_at).toLocaleDateString()}
                      </span>
                      <StatusBadge
                        status={t.status}
                        statusMap={TRANSACTION_STATUS_CONFIG}
                      />
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  );
}

// =============================================================================
// LOADING SKELETON
// =============================================================================

function CategorySkeleton() {
  return (
    <div className="rounded-lg border p-4 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton className="h-5 w-28" />
        <Skeleton className="h-5 w-8 rounded-full" />
      </div>
      {Array.from({ length: 2 }, (_, i) => (
        <div key={i} className="flex items-center justify-between py-2">
          <div className="space-y-1">
            <Skeleton className="h-4 w-48" />
            <Skeleton className="h-3 w-32" />
          </div>
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// STATUS FILTER
// =============================================================================

const STATUS_FILTER_OPTIONS: { value: string; label: string }[] = [
  { value: "all", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "accepted", label: "Accepted" },
  { value: "denied", label: "Denied" },
  { value: "cancelled", label: "Cancelled" },
  { value: "info_requested", label: "Info Requested" },
];

// =============================================================================
// MAIN PAGE COMPONENT
// =============================================================================

export function UserTransactionsPage() {
  const router = useRouter();
  const [roleFilter, setRoleFilter] = useState<TransactionRole>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const { data, isLoading } = useTransactionList({
    role: roleFilter,
    status: statusFilter === "all" ? undefined : (statusFilter as TransactionStatus),
    page_size: 100,
  });

  const transactions = data?.results ?? [];

  // Group transactions by category
  const groupedByCategory = useMemo(() => {
    const groups: Record<string, TransactionListItem[]> = {};
    for (const t of transactions) {
      const cat = t.category;
      if (!groups[cat]) groups[cat] = [];
      groups[cat].push(t);
    }
    return groups;
  }, [transactions]);

  // Ordered categories — only show those with transactions
  const activeCategories = useMemo(
    () => CATEGORY_ORDER.filter((cat) => (groupedByCategory[cat]?.length ?? 0) > 0),
    [groupedByCategory],
  );

  function handleTransactionClick(id: string) {
    router.push(`/activity/${id}`);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">Activity</h1>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <Tabs
          value={roleFilter}
          onValueChange={(v) => setRoleFilter(v as TransactionRole)}
        >
          <TabsList>
            {ROLE_TABS.map((tab) => (
              <TabsTrigger key={tab.value} value={tab.value}>
                {tab.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border bg-background px-3 py-1.5 text-sm"
        >
          {STATUS_FILTER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="space-y-4">
          <CategorySkeleton />
          <CategorySkeleton />
        </div>
      ) : activeCategories.length === 0 ? (
        <div className="rounded-lg border p-12 text-center">
          <p className="text-muted-foreground">
            No transactions found.
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Invitations and requests you send or receive will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {activeCategories.map((category) => (
            <CategoryCard
              key={category}
              category={category}
              transactions={groupedByCategory[category]}
              onTransactionClick={handleTransactionClick}
            />
          ))}
        </div>
      )}

      {/* Pagination info */}
      {data && data.count > transactions.length && (
        <div className="flex justify-center">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              // For now, show a simple "load more" indicator
              // Future: implement proper pagination
            }}
          >
            Showing {transactions.length} of {data.count}
          </Button>
        </div>
      )}
    </div>
  );
}
