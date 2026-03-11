"use client";

import { useParams } from "next/navigation";
import { useRouter } from "next/navigation";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Can } from "@/components/common/Can";
import { useHasPermission } from "@/hooks/use-has-permission";
import {
  useBusinessMemberships,
  usePlatformMembership,
} from "@/stores/membership-store";
import type { AccountType } from "@/types/rbac";

type TransactionsDashboardPageInnerProps = {
  accountType: AccountType;
  accountId: string;
  basePath: string;
};

function TransactionsDashboardPageInner({
  accountType,
  accountId,
  basePath,
}: TransactionsDashboardPageInnerProps) {
  const router = useRouter();
  const canConfigureTransactions = useHasPermission(
    "can_configure_transactions",
    accountType,
    accountId,
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Transactions</h1>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card
          className="cursor-pointer transition-colors hover:bg-muted/50"
          onClick={() => router.push(`${basePath}/requests`)}
        >
          <CardHeader>
            <CardTitle className="text-base">Requests</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              View and manage incoming membership requests.
            </p>
          </CardContent>
        </Card>

        <Card
          className="cursor-pointer transition-colors hover:bg-muted/50"
          onClick={() => router.push(`${basePath}/invitations`)}
        >
          <CardHeader>
            <CardTitle className="text-base">Invitations</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Send and track member invitations.
            </p>
          </CardContent>
        </Card>

        <Can allowed={canConfigureTransactions}>
          <Card
            className="cursor-pointer transition-colors hover:bg-muted/50"
            onClick={() => router.push(`${basePath}/settings`)}
          >
            <CardHeader>
              <CardTitle className="text-base">Settings</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Configure transaction forms and requirements.
              </p>
            </CardContent>
          </Card>
        </Can>
      </div>
    </div>
  );
}

// =============================================================================
// BUSINESS WRAPPER
// =============================================================================

export function BusinessTransactionsDashboardPage() {
  const { slug } = useParams<{ slug: string }>();
  const memberships = useBusinessMemberships();
  const myMembership = memberships.find((m) => m.account_slug === slug);
  const accountId = myMembership?.account_id ?? "";

  return (
    <TransactionsDashboardPageInner
      accountType="business"
      accountId={accountId}
      basePath={`/bconsole/${slug}/transactions`}
    />
  );
}

// =============================================================================
// PLATFORM WRAPPER
// =============================================================================

export function PlatformTransactionsDashboardPage() {
  const myMembership = usePlatformMembership();
  const accountId = myMembership?.account_id ?? "";

  return (
    <TransactionsDashboardPageInner
      accountType="platform"
      accountId={accountId}
      basePath="/pconsole/transactions"
    />
  );
}
